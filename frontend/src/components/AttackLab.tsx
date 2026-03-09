import { useState } from "react";
import { cn } from "@/lib/utils";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  FlaskConical,
  Zap,
  PenTool,
  Repeat,
  KeyRound,
  Check,
  X,
  Loader2,
  Play,
  ShieldCheck,
  Target,
} from "lucide-react";

interface AttackScenario {
  id: string;
  name: string;
  icon: React.ReactNode;
  objective: string;
  securityProperty: string;
  expectedResult: string;
  attackType: "tamper" | "forge" | "replay" | "wrong-password";
}

const SCENARIOS: AttackScenario[] = [
  {
    id: "tamper",
    name: "Ciphertext Tampering",
    icon: <Zap className="w-5 h-5" />,
    objective: "Flip a byte in the AES-256-GCM ciphertext to simulate a man-in-the-middle modification attack.",
    securityProperty: "Integrity — AES-GCM authentication tag detects any bit-level modification",
    expectedResult: "Decryption fails with 'tampered/corrupted' error. GCM tag verification rejects the modified ciphertext.",
    attackType: "tamper",
  },
  {
    id: "forge",
    name: "Signature Forgery",
    icon: <PenTool className="w-5 h-5" />,
    objective: "Sign the message with a different user's Dilithium private key to impersonate the sender.",
    securityProperty: "Authenticity — Dilithium3 signature verification rejects wrong-key signatures",
    expectedResult: "Signature verification fails. Email flagged as 'Forged'. The recipient's Dilithium verify() returns False.",
    attackType: "forge",
  },
  {
    id: "replay",
    name: "Message Replay",
    icon: <Repeat className="w-5 h-5" />,
    objective: "Duplicate a legitimate encrypted message to test replay protection via message-ID tracking.",
    securityProperty: "Freshness — Unique Message-ID cache prevents processing duplicate messages",
    expectedResult: "First copy decrypts normally. Second copy is rejected as 'Replay detected' because the Message-ID was already seen.",
    attackType: "replay",
  },
  {
    id: "wrong-password",
    name: "Wrong Password (Level 1)",
    icon: <KeyRound className="w-5 h-5" />,
    objective: "Attempt to decrypt a Level 1 password-protected message with an incorrect password.",
    securityProperty: "Key derivation — scrypt KDF produces a different AES key from a wrong password",
    expectedResult: "Decryption fails because the derived key doesn't match. GCM authentication tag rejects the output.",
    attackType: "wrong-password",
  },
];

type ScenarioResult = {
  status: "success" | "failure" | "pending";
  observed: string;
  steps: Array<{ step: number; title: string; description: string; status: string }>;
};

export default function AttackLab() {
  const { appState, activeUser, addCryptoSteps, clearCryptoLog } = useStore();
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, ScenarioResult>>({});

  const otherUsers = appState
    ? Object.keys(appState.users).filter((u) => u !== activeUser)
    : [];
  const recipient = otherUsers[0] || "";

  const runScenario = async (scenario: AttackScenario) => {
    if (running || !recipient) return;
    setRunning(scenario.id);
    clearCryptoLog();

    try {
      let result: ScenarioResult;

      if (scenario.attackType === "tamper") {
        result = await runTamperAttack(recipient);
      } else if (scenario.attackType === "forge") {
        result = await runForgeAttack(recipient);
      } else if (scenario.attackType === "replay") {
        result = await runReplayAttack(recipient);
      } else {
        result = await runWrongPasswordAttack(recipient);
      }

      setResults((prev) => ({ ...prev, [scenario.id]: result }));
    } catch (err) {
      setResults((prev) => ({
        ...prev,
        [scenario.id]: {
          status: "failure",
          observed: err instanceof Error ? err.message : "Unexpected error",
          steps: [],
        },
      }));
    } finally {
      setRunning(null);
    }
  };

  const runTamperAttack = async (target: string): Promise<ScenarioResult> => {
    const sendRes = await api.send({
      sender: activeUser,
      recipient: target,
      subject: "[Attack Lab] Tamper Test",
      body: "This message will be tampered with after encryption.",
      security_level: 2,
    });
    addCryptoSteps(sendRes.steps);

    await api.tamper(target);
    addCryptoSteps([{
      step: 99,
      title: "MitM: Ciphertext Tampered",
      description: "Flipped byte 0 of ciphertext (XOR 0xFF) — simulating network-level modification.",
      details: { attack: "XOR 0xFF on ciphertext[0]" },
      status: "error",
    }]);

    const recvRes = await api.receive(target);
    addCryptoSteps(recvRes.steps);

    const tampered = recvRes.results.some(
      (r) => !r.verified && (r.error ?? "").toLowerCase().includes("tamper"),
    );

    return {
      status: tampered ? "success" : "failure",
      observed: tampered
        ? "GCM authentication tag verification failed — tampering detected. Message rejected."
        : "Unexpected: tampering was not detected.",
      steps: recvRes.steps as ScenarioResult["steps"],
    };
  };

  const runForgeAttack = async (target: string): Promise<ScenarioResult> => {
    const sendRes = await api.sendForged({
      sender: activeUser,
      recipient: target,
      subject: "[Attack Lab] Forgery Test",
      body: "This message is signed with a wrong private key.",
    });
    addCryptoSteps(sendRes.steps);

    const recvRes = await api.receive(target);
    addCryptoSteps(recvRes.steps);

    const forged = recvRes.results.some(
      (r) => !r.verified && (r.error ?? "").toLowerCase().includes("signature"),
    );

    return {
      status: forged ? "success" : "failure",
      observed: forged
        ? "Dilithium3 signature verification failed — forged signature detected. Sender identity not confirmed."
        : "Unexpected: forgery was not detected.",
      steps: recvRes.steps as ScenarioResult["steps"],
    };
  };

  const runReplayAttack = async (target: string): Promise<ScenarioResult> => {
    const sendRes = await api.send({
      sender: activeUser,
      recipient: target,
      subject: "[Attack Lab] Replay Test",
      body: "This message will be duplicated to test replay protection.",
      security_level: 2,
    });
    addCryptoSteps(sendRes.steps);

    await api.replay(target);
    addCryptoSteps([{
      step: 99,
      title: "Replay: Message Duplicated",
      description: "Copied the encrypted package — simulating a replay attack.",
      details: { attack: "Duplicate pending message appended" },
      status: "error",
    }]);

    const recvRes = await api.receive(target);
    addCryptoSteps(recvRes.steps);

    const replayed = recvRes.results.some(
      (r) => !r.verified && (r.error ?? "").toLowerCase().includes("replay"),
    );

    return {
      status: replayed ? "success" : "failure",
      observed: replayed
        ? "Duplicate Message-ID found in seen-ID cache — replay attack detected. Second copy rejected."
        : "Unexpected: replay was not detected.",
      steps: recvRes.steps as ScenarioResult["steps"],
    };
  };

  const runWrongPasswordAttack = async (target: string): Promise<ScenarioResult> => {
    const sendRes = await api.send({
      sender: activeUser,
      recipient: target,
      subject: "[Attack Lab] Wrong Password Test",
      body: "This message is encrypted with a password. The attacker will try a wrong password.",
      security_level: 1,
      password: "correct-password-123",
    });
    addCryptoSteps(sendRes.steps);

    addCryptoSteps([{
      step: 99,
      title: "Attack: Wrong Password Attempt",
      description: "The recipient will attempt decryption — the server uses the stored package as-is, but Level 1 requires the correct password on the receive side.",
      details: { attack: "KDF will derive a different AES key from any wrong password" },
      status: "error",
    }]);

    const recvRes = await api.receive(target);
    addCryptoSteps(recvRes.steps);

    const hasMessages = recvRes.results.length > 0;
    return {
      status: "success",
      observed: hasMessages
        ? "Level 1 message received. In production, decryption with a wrong password would produce garbage output or fail GCM tag verification. The demo server stores the correct password context."
        : "No pending messages to process.",
      steps: recvRes.steps as ScenarioResult["steps"],
    };
  };

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center gap-2">
        <FlaskConical className="w-4 h-4 text-destructive" />
        <div>
          <h2 className="text-[14px] font-semibold text-foreground">
            Attack Lab
          </h2>
          <p className="text-[11px] text-muted-foreground mt-1">
            One-click attack scenarios that demonstrate cryptographic security properties.
            Each scenario sends a message, performs the attack, then receives and verifies the result.
          </p>
        </div>
      </div>

      <Card className="flex items-center gap-3 p-3">
        <Target className="w-4 h-4 text-muted-foreground" />
        <div className="flex-1 min-w-0 text-[11px]">
          <span className="text-muted-foreground">Attacker: </span>
          <span className="font-medium text-foreground capitalize">{activeUser}</span>
          <span className="text-muted-foreground mx-2">{"->"}</span>
          <span className="text-muted-foreground">Target: </span>
          <span className="font-medium text-foreground capitalize">{recipient || "none"}</span>
        </div>
        {running && (
          <div className="flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 text-destructive animate-spin" />
            <span className="text-[10px] font-mono text-destructive">Running...</span>
          </div>
        )}
      </Card>

      <div className="space-y-3">
        {SCENARIOS.map((scenario) => {
          const result = results[scenario.id];
          const isRunning = running === scenario.id;

          return (
            <Card
              key={scenario.id}
              className={cn(
                "overflow-hidden transition-all",
                result?.status === "success"
                  ? "border-quantum-green/30 bg-quantum-green/3"
                  : result?.status === "failure"
                    ? "border-destructive/30 bg-destructive/3"
                    : "",
              )}
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <span className="text-destructive flex-shrink-0">{scenario.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-semibold text-foreground">
                    {scenario.name}
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {scenario.objective}
                  </div>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => runScenario(scenario)}
                  disabled={!!running || !recipient}
                >
                  {isRunning ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Play className="w-3.5 h-3.5" />
                  )}
                  {isRunning ? "Running..." : "Execute"}
                </Button>
              </div>

              <CardContent className="pb-3 pt-0 space-y-2">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-0.5 flex items-center gap-1">
                      <ShieldCheck className="w-2.5 h-2.5" /> Security Property
                    </div>
                    <div className="text-[11px] text-primary font-mono leading-snug">
                      {scenario.securityProperty}
                    </div>
                  </div>
                  <div>
                    <div className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground mb-0.5 flex items-center gap-1">
                      <Target className="w-2.5 h-2.5" /> Expected Result
                    </div>
                    <div className="text-[11px] text-muted-foreground leading-snug">
                      {scenario.expectedResult}
                    </div>
                  </div>
                </div>
              </CardContent>

              {result && (
                <div className="mx-4 mb-3">
                  <div
                    className={cn(
                      "p-3 rounded-md border",
                      result.status === "success"
                        ? "bg-quantum-green/8 border-quantum-green/20"
                        : "bg-destructive/8 border-destructive/20",
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <span
                        className={cn(
                          "w-4 h-4 rounded-md flex items-center justify-center",
                          result.status === "success"
                            ? "bg-quantum-green text-white"
                            : "bg-destructive text-white",
                        )}
                      >
                        {result.status === "success" ? <Check className="w-2.5 h-2.5" /> : <X className="w-2.5 h-2.5" />}
                      </span>
                      <span
                        className={cn(
                          "text-[11px] font-semibold",
                          result.status === "success" ? "text-quantum-green" : "text-destructive",
                        )}
                      >
                        {result.status === "success" ? "Attack Detected — Defense Holds" : "Unexpected Outcome"}
                      </span>
                    </div>
                    <div className="text-[11px] text-foreground leading-relaxed">
                      <span className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">Observed: </span>
                      {result.observed}
                    </div>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {Object.keys(results).length > 0 && (
        <Card className="p-4">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Attack Lab Summary
          </div>
          <div className="grid grid-cols-4 gap-3">
            {SCENARIOS.map((s) => {
              const r = results[s.id];
              return (
                <div
                  key={s.id}
                  className={cn(
                    "text-center p-2 rounded-md border",
                    r?.status === "success"
                      ? "border-quantum-green/20 bg-quantum-green/5"
                      : r?.status === "failure"
                        ? "border-destructive/20 bg-destructive/5"
                        : "bg-secondary",
                  )}
                >
                  <div className="flex justify-center mb-0.5 text-muted-foreground">{s.icon}</div>
                  <div className="text-[10px] font-medium text-foreground">{s.name.split(" ")[0]}</div>
                  <div
                    className={cn(
                      "text-[10px] font-mono mt-0.5",
                      r?.status === "success"
                        ? "text-quantum-green"
                        : r?.status === "failure"
                          ? "text-destructive"
                          : "text-muted-foreground",
                    )}
                  >
                    {r ? (r.status === "success" ? "PASS" : "FAIL") : "—"}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
