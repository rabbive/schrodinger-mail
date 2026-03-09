import { useState } from "react";
import clsx from "clsx";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";

interface DemoStep {
  id: string;
  phase: string;
  title: string;
  claim: string;
  action: string;
  expectedOutcome: string;
  securityProperty: string;
  timeEstimate: string;
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
  },
  {
    id: "tamper-attack",
    phase: "Phase 2 — Integrity",
    title: "Ciphertext Tampering Detection",
    claim: "Any modification to the ciphertext is detected via GCM authentication tag.",
    action: "Use Attack Lab → 'Tamper Attack' to flip a byte in the ciphertext, then receive as Bob.",
    expectedOutcome: "GCM decryption fails. Email shows 'Tampered' badge with error. Verification panel confirms integrity violation.",
    securityProperty: "Integrity (AES-256-GCM authentication tag)",
    timeEstimate: "2 min",
  },
  {
    id: "forge-attack",
    phase: "Phase 3 — Authenticity",
    title: "Forged Signature Detection",
    claim: "Messages signed with a wrong private key are rejected by Dilithium verification.",
    action: "Use Attack Lab → 'Forge Signature' to sign with a different user's key, then receive as Bob.",
    expectedOutcome: "Signature verification fails. Email shows 'Forged' badge. Verification panel shows Dilithium signature mismatch.",
    securityProperty: "Authenticity (Dilithium3 digital signatures)",
    timeEstimate: "2 min",
  },
  {
    id: "replay-attack",
    phase: "Phase 4 — Replay Protection",
    title: "Replay Attack Detection",
    claim: "Duplicate messages are rejected by the message-ID replay cache.",
    action: "Use Attack Lab → 'Replay Attack' to duplicate a pending message, then receive as Bob.",
    expectedOutcome: "Second copy is flagged as 'Replay'. Verification panel shows duplicate Message-ID detected in seen-ID cache.",
    securityProperty: "Freshness (unique Message-ID tracking)",
    timeEstimate: "2 min",
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
      {/* Header */}
      <div>
        <h2 className="text-[14px] font-semibold text-[var(--text)]">
          Demo Storyline
        </h2>
        <p className="text-[11px] text-[var(--text-muted)] mt-1">
          A guided 10–15 minute walkthrough for your professor demo. Each step maps to a specific security claim with expected evidence.
        </p>
      </div>

      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-[var(--surface2)] rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-[11px] font-mono text-[var(--text-dim)] whitespace-nowrap">
          {completedSteps.size}/{DEMO_STEPS.length} steps
        </span>
      </div>

      {/* Quick nav */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setActiveTab("attack-lab")}
          className="px-3 py-1.5 bg-quantum-red/10 text-quantum-red text-[11px] font-medium rounded border border-quantum-red/20 hover:bg-quantum-red/15 transition-colors"
        >
          Open Attack Lab
        </button>
        <button
          onClick={() => setActiveTab("compose")}
          className="px-3 py-1.5 bg-accent/10 text-accent text-[11px] font-medium rounded border border-accent/20 hover:bg-accent/15 transition-colors"
        >
          Compose Message
        </button>
        <button
          onClick={() => setActiveTab("tofu")}
          className="px-3 py-1.5 bg-quantum-orange/10 text-quantum-orange text-[11px] font-medium rounded border border-quantum-orange/20 hover:bg-quantum-orange/15 transition-colors"
        >
          Trust & TOFU
        </button>
        <a
          href={api.getDemoReportUrl(activeUser)}
          className="px-3 py-1.5 bg-quantum-green/10 text-quantum-green text-[11px] font-medium rounded border border-quantum-green/20 hover:bg-quantum-green/15 transition-colors"
        >
          Export Report
        </a>
      </div>

      {/* Steps */}
      <div className="space-y-2">
        {DEMO_STEPS.map((step, i) => {
          const isActive = activeStep === step.id;
          const isComplete = completedSteps.has(step.id);

          return (
            <div
              key={step.id}
              className={clsx(
                "rounded border transition-all",
                isComplete
                  ? "bg-quantum-green/5 border-quantum-green/20"
                  : isActive
                    ? "bg-[var(--surface)] border-accent/30"
                    : "bg-[var(--surface)] border-[var(--border)]",
              )}
            >
              {/* Step header */}
              <button
                onClick={() => setActiveStep(isActive ? null : step.id)}
                className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleComplete(step.id);
                  }}
                  className={clsx(
                    "w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold flex-shrink-0 transition-all",
                    isComplete
                      ? "bg-quantum-green text-white"
                      : "bg-[var(--surface2)] text-[var(--text-muted)] border border-[var(--border)]",
                  )}
                >
                  {isComplete ? "✓" : i + 1}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-accent">
                      {step.phase}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)]">
                      ~{step.timeEstimate}
                    </span>
                  </div>
                  <div className="text-[12px] font-medium text-[var(--text)] mt-0.5">
                    {step.title}
                  </div>
                </div>

                <span className="text-[10px] text-[var(--text-muted)] flex-shrink-0">
                  {isActive ? "▼" : "▶"}
                </span>
              </button>

              {/* Expanded detail */}
              {isActive && (
                <div className="px-3 pb-3 pt-0 space-y-2.5 border-t border-[var(--border)] mx-3">
                  <div className="pt-2.5">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">
                      Security Claim
                    </div>
                    <p className="text-[12px] text-[var(--text)] leading-relaxed">
                      {step.claim}
                    </p>
                  </div>

                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">
                      Action
                    </div>
                    <p className="text-[12px] text-[var(--text-dim)] leading-relaxed">
                      {step.action}
                    </p>
                  </div>

                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">
                      Expected Outcome
                    </div>
                    <p className="text-[12px] text-quantum-green leading-relaxed">
                      {step.expectedOutcome}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <span className="px-2 py-0.5 bg-accent/10 text-accent text-[10px] font-mono font-medium rounded border border-accent/15">
                      {step.securityProperty}
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary callout */}
      <div className="p-3 rounded border border-[var(--border)] bg-[var(--surface)] text-[11px] text-[var(--text-muted)] space-y-1.5">
        <div className="font-medium text-[var(--text-dim)] text-[12px]">
          Security Properties Demonstrated
        </div>
        <div className="flex flex-wrap gap-1.5">
          {["Confidentiality", "Integrity", "Authenticity", "Replay Protection", "Quantum Resistance", "Trust Management", "Auditability"].map((prop) => (
            <span
              key={prop}
              className="px-2 py-0.5 bg-[var(--surface2)] text-[var(--text-dim)] text-[10px] font-mono rounded border border-[var(--border)]"
            >
              {prop}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
