import { useState } from "react";
import { cn } from "@/lib/utils";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
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
  BookOpen,
  ArrowRight,
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
  explanation?: {
    attack_name: string;
    detected: boolean;
    security_property: string;
    defense_mechanism: string;
    how_it_works: string;
    real_world: string;
  };
  steps: Array<{ step: number; title: string; description: string; status: string }>;
};

export default function AttackLab() {
  const { appState, activeUser, addCryptoSteps, clearCryptoLog } = useStore();
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, ScenarioResult>>({});
  const [selectedRecipient, setSelectedRecipient] = useState("");

  const allUsers = appState ? Object.keys(appState.users) : [];
  const otherUsers = allUsers.filter((u) => u !== activeUser);

  // Auto-select first other user if none selected
  const recipient = selectedRecipient || otherUsers[0] || "";

  const runScenario = async (scenario: AttackScenario) => {
    if (running || !recipient) return;
    setRunning(scenario.id);
    clearCryptoLog();

    try {
      const res = await api.runAttack({
        attack_type: scenario.attackType,
        sender: activeUser,
        recipient,
      });

      addCryptoSteps(res.steps);

      const result: ScenarioResult = {
        status: res.detected ? "success" : "failure",
        observed: res.detected
          ? getSuccessMessage(scenario.attackType)
          : "Unexpected: attack was not detected.",
        explanation: res.explanation,
        steps: res.steps as ScenarioResult["steps"],
      };

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

  const runAllScenarios = async () => {
    if (running || !recipient) return;
    for (const scenario of SCENARIOS) {
      await runScenario(scenario);
    }
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

      {/* Attacker / Target selector */}
      <Card className="p-3 space-y-3">
        <div className="flex items-center gap-3">
          <Target className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          <div className="flex-1 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
            <div>
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Attacker (Sender)</Label>
              <div className="text-[12px] font-semibold text-foreground capitalize mt-0.5 px-2 py-1.5 rounded-md bg-secondary border">
                {activeUser}
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-destructive mt-4" />
            <div>
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">Target (Recipient)</Label>
              <Select
                value={recipient}
                onChange={(e) => setSelectedRecipient(e.target.value)}
                className="mt-0.5"
              >
                {otherUsers.length === 0 && <option value="">No other users</option>}
                {otherUsers.map((u) => (
                  <option key={u} value={u}>
                    {u.charAt(0).toUpperCase() + u.slice(1)}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="destructive"
            size="sm"
            onClick={runAllScenarios}
            disabled={!!running || !recipient}
          >
            <Play className="w-3.5 h-3.5" />
            Run All Attacks
          </Button>
          {running && (
            <div className="flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 text-destructive animate-spin" />
              <span className="text-[10px] font-mono text-destructive">Running...</span>
            </div>
          )}
        </div>
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
                <div className="mx-4 mb-3 space-y-2">
                  {/* Detection result */}
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

                  {/* Educational explanation */}
                  {result.explanation && (
                    <div className="p-3 rounded-md border bg-primary/5 border-primary/20">
                      <div className="flex items-center gap-1.5 mb-2">
                        <BookOpen className="w-3.5 h-3.5 text-primary" />
                        <span className="text-[11px] font-semibold text-primary">
                          How This Defense Works
                        </span>
                      </div>
                      <div className="space-y-2 text-[11px] leading-relaxed">
                        <div>
                          <span className="font-semibold text-foreground">Security Property: </span>
                          <span className="text-primary font-mono">{result.explanation.security_property}</span>
                        </div>
                        <div>
                          <span className="font-semibold text-foreground">Defense Mechanism: </span>
                          <span className="text-foreground">{result.explanation.defense_mechanism}</span>
                        </div>
                        <div>
                          <span className="font-semibold text-foreground">Technical Explanation: </span>
                          <span className="text-muted-foreground">{result.explanation.how_it_works}</span>
                        </div>
                        <div>
                          <span className="font-semibold text-foreground">Real-World Relevance: </span>
                          <span className="text-muted-foreground">{result.explanation.real_world}</span>
                        </div>
                      </div>
                    </div>
                  )}
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
                    {r ? (r.status === "success" ? "DETECTED" : "FAIL") : "—"}
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

function getSuccessMessage(attackType: string): string {
  switch (attackType) {
    case "tamper":
      return "GCM authentication tag verification failed — tampering detected. Message rejected.";
    case "forge":
      return "Dilithium3 signature verification failed — forged signature detected. Sender identity not confirmed.";
    case "replay":
      return "Duplicate Message-ID found in seen-ID cache — replay attack detected. Second copy rejected.";
    case "wrong-password":
      return "scrypt derived a different AES key from the wrong password — GCM decryption failed. Message unreadable without correct password.";
    default:
      return "Attack detected.";
  }
}
