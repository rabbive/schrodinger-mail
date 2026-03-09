import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import {
  Layers,
  ArrowDownToLine,
  FileSignature,
  Package,
  Lock,
  Unlock,
  ShieldCheck,
  RefreshCcwDot,
  Inbox,
  Send,
} from "lucide-react";

const SENDER_ICONS = [ArrowDownToLine, FileSignature, Package, Lock, Lock, Send];
const RECEIVER_ICONS = [Unlock, Unlock, Package, ShieldCheck, RefreshCcwDot, Inbox];

export default function ArchitecturePanel() {
  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-2">
        <Layers className="w-4 h-4 text-primary" />
        <div>
          <h2 className="text-base font-bold">Signed KEM-DEM Architecture</h2>
          <p className="text-xs text-muted-foreground">
            Interactive visualization of the quantum-secure email pipeline.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-5">
        <div>
          <h3 className="text-sm font-semibold text-quantum-green mb-3 flex items-center gap-1.5">
            <Send className="w-3.5 h-3.5" /> Sender Workflow
          </h3>
          <div className="space-y-2">
            {SENDER_STEPS.map((step, i) => (
              <StepBlock key={i} step={i + 1} title={step.title} desc={step.desc} color="green" icon={SENDER_ICONS[i]} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-quantum-blue mb-3 flex items-center gap-1.5">
            <Inbox className="w-3.5 h-3.5" /> Receiver Workflow
          </h3>
          <div className="space-y-2">
            {RECEIVER_STEPS.map((step, i) => (
              <StepBlock key={i} step={i + 1} title={step.title} desc={step.desc} color="blue" icon={RECEIVER_ICONS[i]} />
            ))}
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-base font-bold mb-3">Classical vs Post-Quantum Cryptography</h2>
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-secondary">
                  <th className="text-left px-3 py-2">Property</th>
                  <th className="text-left px-3 py-2">Classical (RSA/ECDSA)</th>
                  <th className="text-left px-3 py-2">Post-Quantum (Kyber/Dilithium)</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map((row) => (
                  <tr key={row[0]} className="border-t">
                    <td className="px-3 py-1.5 font-medium">{row[0]}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{row[1]}</td>
                    <td className="px-3 py-1.5 text-quantum-green">{row[2]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StepBlock({
  step,
  title,
  desc,
  color,
  icon: Icon,
}: {
  step: number;
  title: string;
  desc: string;
  color: "green" | "blue";
  icon: React.ComponentType<{ className?: string }>;
}) {
  const bg = color === "green" ? "bg-quantum-green/10" : "bg-quantum-blue/10";
  const text = color === "green" ? "text-quantum-green" : "text-quantum-blue";

  return (
    <div className={cn(bg, "rounded-md p-2.5 border")}>
      <div className="flex items-center gap-2">
        <Icon className={cn("w-3.5 h-3.5", text)} />
        <span className={cn(text, "text-xs font-bold")}>{step}.</span>
        <span className="text-xs font-semibold">{title}</span>
      </div>
      <div className="text-[10px] text-muted-foreground mt-0.5 ml-5">{desc}</div>
    </div>
  );
}

const SENDER_STEPS = [
  { title: "Fetch Recipient's Public Keys", desc: "Retrieve Kyber768 PK and Dilithium3 PK from the server." },
  { title: "Sign Plaintext (Dilithium3)", desc: "Sign the plaintext with sender's Dilithium3 secret key." },
  { title: "Build Payload", desc: "Concatenate signature + plaintext into a single payload." },
  { title: "KEM Encapsulate (Kyber768)", desc: "Generate a shared secret and encapsulated key using recipient's Kyber PK." },
  { title: "AES-256-GCM Encrypt", desc: "Encrypt the payload using the shared secret as the AES key." },
  { title: "Send Package", desc: "Deliver (encapsulated_key, ciphertext, nonce, tag) to the server." },
];

const RECEIVER_STEPS = [
  { title: "KEM Decapsulate (Kyber768)", desc: "Recover the shared secret using receiver's Kyber SK." },
  { title: "AES-256-GCM Decrypt", desc: "Decrypt the ciphertext using the recovered shared secret." },
  { title: "Split Payload", desc: "Separate the signature from the plaintext." },
  { title: "Verify Signature (Dilithium3)", desc: "Verify the signature using sender's Dilithium3 public key." },
  { title: "Replay Detection", desc: "Check Message-ID against previously seen IDs." },
  { title: "Deliver to Inbox", desc: "Store the verified plaintext in the recipient's inbox." },
];

const COMPARISON = [
  ["KEM Algorithm", "RSA-2048 / ECDH", "CRYSTALS-Kyber768"],
  ["Signature Algorithm", "RSA / ECDSA", "CRYSTALS-Dilithium3"],
  ["Security Level", "128-bit classical", "NIST Level 3 (192-bit)"],
  ["Quantum Resistant", "NO — Broken by Shor's", "YES — Lattice-based hardness"],
  ["NIST Standardized", "Yes (legacy)", "Yes (FIPS 203/204, 2024)"],
  ["Harvest Now, Decrypt Later", "Vulnerable", "Protected"],
];
