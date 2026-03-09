import { useState } from "react";
import { cn } from "@/lib/utils";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  BookOpen,
  FlaskConical,
  PenSquare,
  ShieldCheck,
  RotateCcw,
  FileText,
  Lock,
  ShieldX,
  RefreshCcwDot,
  KeyRound,
  Check,
  ChevronDown,
  ChevronRight,
  Download,
} from "lucide-react";

interface DemoStep {
  id: string;
  phase: string;
  title: string;
  claim: string;
  action: string;
  expectedOutcome: string;
  securityProperty: string;
  timeEstimate: string;
  icon: React.ReactNode;
}

const DEMO_STEPS: DemoStep[] = [
  {
    id: "normal-send",
    phase: "Phase 1 — Confidentiality",
    title: "Secure Message Send/Receive (Level 2)",
    claim: "Only the intended recipient can decrypt the message.",
    action: "Send a message from Alice to Bob using Kyber768 KEM + Dilithium3 signature + AES-256-GCM.",
    expectedOutcome: "Bob receives the message with a 'verified' badge. Crypto log shows KEM encapsulation, AES-GCM encryption, and signature generation.",
    securityProperty: "Confidentiality + Authenticity + Integrity",
    timeEstimate: "2 min",
    icon: <Lock className="w-3.5 h-3.5" />,
  },
  {
    id: "tamper-attack",
    phase: "Phase 2 — Integrity",
    title: "Ciphertext Tampering Detection",
    claim: "Any modification to the ciphertext is detected via GCM authentication tag.",
    action: "Use Attack Lab -> 'Tamper Attack' to flip a byte in the ciphertext, then receive as Bob.",
    expectedOutcome: "GCM decryption fails. Email shows 'Tampered' badge with error. Verification panel confirms integrity violation.",
    securityProperty: "Integrity (AES-256-GCM authentication tag)",
    timeEstimate: "2 min",
    icon: <ShieldX className="w-3.5 h-3.5" />,
  },
  {
    id: "forge-attack",
    phase: "Phase 3 — Authenticity",
    title: "Forged Signature Detection",
    claim: "Messages signed with a wrong private key are rejected by Dilithium verification.",
    action: "Use Attack Lab -> 'Forge Signature' to sign with a different user's key, then receive as Bob.",
    expectedOutcome: "Signature verification fails. Email shows 'Forged' badge. Verification panel shows Dilithium signature mismatch.",
    securityProperty: "Authenticity (Dilithium3 digital signatures)",
    timeEstimate: "2 min",
    icon: <ShieldCheck className="w-3.5 h-3.5" />,
  },
  {
    id: "replay-attack",
    phase: "Phase 4 — Replay Protection",
    title: "Replay Attack Detection",
    claim: "Duplicate messages are rejected by the message-ID replay cache.",
    action: "Use Attack Lab -> 'Replay Attack' to duplicate a pending message, then receive as Bob.",
    expectedOutcome: "Second copy is flagged as 'Replay'. Verification panel shows duplicate Message-ID detected in seen-ID cache.",
    securityProperty: "Freshness (unique Message-ID tracking)",
    timeEstimate: "2 min",
    icon: <RefreshCcwDot className="w-3.5 h-3.5" />,
  },
  {
    id: "password-level",
    phase: "Phase 5 — Level 1 Symmetric",
    title: "Password-Protected Encryption (Level 1)",
    claim: "KDF-derived key protects messages without public-key infrastructure.",
    action: "Send a Level 1 message with a shared password. Receive on the other side.",
    expectedOutcome: "Message decrypts only with the correct password. Crypto log shows scrypt KDF derivation.",
    securityProperty: "Symmetric confidentiality (scrypt + AES-256-GCM)",
    timeEstimate: "2 min",
    icon: <KeyRound className="w-3.5 h-3.5" />,
  },
  {
    id: "key-rotation",
    phase: "Phase 6 — Trust Management",
    title: "Key Rotation & TOFU Warning",
    claim: "Fingerprint changes trigger a trust warning to prevent MITM key substitution.",
    action: "Rotate a user's keys via the TOFU panel and observe the fingerprint mismatch warning.",
    expectedOutcome: "A trust warning appears requiring explicit user acceptance. Old fingerprint vs new fingerprint displayed.",
    securityProperty: "Trust-On-First-Use (TOFU) key continuity",
    timeEstimate: "2 min",
    icon: <RotateCcw className="w-3.5 h-3.5" />,
  },
  {
    id: "export-report",
    phase: "Phase 7 — Evidence",
    title: "Export Security Report",
    claim: "All cryptographic operations and attack outcomes are auditable.",
    action: "Click 'Export Demo Report' to generate an HTML+JSON evidence bundle.",
    expectedOutcome: "Downloaded report contains algorithm details, key sizes, benchmarks, attack results, and full audit trail.",
    securityProperty: "Auditability + Non-repudiation",
    timeEstimate: "1 min",
    icon: <FileText className="w-3.5 h-3.5" />,
  },
];

export default function DemoStoryline() {
  const { setActiveTab, activeUser } = useStore();
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [activeStep, setActiveStep] = useState<string | null>(null);

  const toggleComplete = (id: string) => {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const progress = (completedSteps.size / DEMO_STEPS.length) * 100;

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center gap-2">
        <BookOpen className="w-4 h-4 text-primary" />
        <div>
          <h2 className="text-[14px] font-semibold text-foreground">
            Demo Storyline
          </h2>
          <p className="text-[11px] text-muted-foreground mt-1">
            A guided 10-15 minute walkthrough for your professor demo. Each step maps to a specific security claim with expected evidence.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-[11px] font-mono text-muted-foreground whitespace-nowrap">
          {completedSteps.size}/{DEMO_STEPS.length} steps
        </span>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <Button variant="destructive" size="sm" onClick={() => setActiveTab("attack-lab")}>
          <FlaskConical className="w-3.5 h-3.5" /> Open Attack Lab
        </Button>
        <Button variant="outline" size="sm" onClick={() => setActiveTab("compose")}>
          <PenSquare className="w-3.5 h-3.5" /> Compose Message
        </Button>
        <Button variant="outline" size="sm" onClick={() => setActiveTab("tofu")} className="text-quantum-orange border-quantum-orange/20 hover:bg-quantum-orange/10">
          <ShieldCheck className="w-3.5 h-3.5" /> Trust & TOFU
        </Button>
        <Button variant="outline" size="sm" className="text-quantum-green border-quantum-green/20 hover:bg-quantum-green/10" asChild>
          <a href={api.getDemoReportUrl(activeUser)}>
            <Download className="w-3.5 h-3.5" /> Export Report
          </a>
        </Button>
      </div>

      <div className="space-y-2">
        {DEMO_STEPS.map((step, i) => {
          const isActive = activeStep === step.id;
          const isComplete = completedSteps.has(step.id);

          return (
            <Card
              key={step.id}
              className={cn(
                "transition-all",
                isComplete
                  ? "bg-quantum-green/5 border-quantum-green/20"
                  : isActive
                    ? "border-primary/30"
                    : "",
              )}
            >
              <button
                onClick={() => setActiveStep(isActive ? null : step.id)}
                className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleComplete(step.id);
                  }}
                  className={cn(
                    "w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold flex-shrink-0 transition-all",
                    isComplete
                      ? "bg-quantum-green text-white"
                      : "bg-secondary text-muted-foreground border",
                  )}
                >
                  {isComplete ? <Check className="w-3 h-3" /> : i + 1}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-primary flex items-center gap-1">
                      {step.icon} {step.phase}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      ~{step.timeEstimate}
                    </span>
                  </div>
                  <div className="text-[12px] font-medium text-foreground mt-0.5">
                    {step.title}
                  </div>
                </div>

                {isActive ? (
                  <ChevronDown className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                )}
              </button>

              {isActive && (
                <div className="px-3 pb-3 pt-0 space-y-2.5 border-t mx-3">
                  <div className="pt-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                      Security Claim
                    </div>
                    <p className="text-[12px] text-foreground leading-relaxed">
                      {step.claim}
                    </p>
                  </div>

                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                      Action
                    </div>
                    <p className="text-[12px] text-muted-foreground leading-relaxed">
                      {step.action}
                    </p>
                  </div>

                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                      Expected Outcome
                    </div>
                    <p className="text-[12px] text-quantum-green leading-relaxed">
                      {step.expectedOutcome}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <Badge className="gap-1">
                      <ShieldCheck className="w-3 h-3" />
                      {step.securityProperty}
                    </Badge>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      <Card className="p-3 text-[11px] text-muted-foreground space-y-1.5">
        <div className="font-medium text-foreground/70 text-[12px]">
          Security Properties Demonstrated
        </div>
        <div className="flex flex-wrap gap-1.5">
          {["Confidentiality", "Integrity", "Authenticity", "Replay Protection", "Quantum Resistance", "Trust Management", "Auditability"].map((prop) => (
            <Badge key={prop} variant="outline">
              {prop}
            </Badge>
          ))}
        </div>
      </Card>
    </div>
  );
}
