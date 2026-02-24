export default function ArchitecturePanel() {
  return (
    <div className="max-w-3xl">
      <h2 className="text-base font-bold mb-1">Signed KEM-DEM Architecture</h2>
      <p className="text-xs text-[var(--text-dim)] mb-4">
        Interactive visualization of the quantum-secure email pipeline.
      </p>

      <div className="grid grid-cols-2 gap-5">
        {/* Sender Workflow */}
        <div>
          <h3 className="text-sm font-semibold text-quantum-green mb-3">Sender Workflow</h3>
          <div className="space-y-2">
            {SENDER_STEPS.map((step, i) => (
              <StepBlock key={i} step={i + 1} title={step.title} desc={step.desc} color="green" />
            ))}
          </div>
        </div>

        {/* Receiver Workflow */}
        <div>
          <h3 className="text-sm font-semibold text-quantum-blue mb-3">Receiver Workflow</h3>
          <div className="space-y-2">
            {RECEIVER_STEPS.map((step, i) => (
              <StepBlock key={i} step={i + 1} title={step.title} desc={step.desc} color="blue" />
            ))}
          </div>
        </div>
      </div>

      {/* PQC vs Classical */}
      <div className="mt-8">
        <h2 className="text-base font-bold mb-3">Classical vs Post-Quantum Cryptography</h2>
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[var(--surface2)]">
                <th className="text-left px-3 py-2">Property</th>
                <th className="text-left px-3 py-2">Classical (RSA/ECDSA)</th>
                <th className="text-left px-3 py-2">Post-Quantum (Kyber/Dilithium)</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row) => (
                <tr key={row[0]} className="border-t border-[var(--border)]">
                  <td className="px-3 py-1.5 font-medium">{row[0]}</td>
                  <td className="px-3 py-1.5 text-[var(--text-dim)]">{row[1]}</td>
                  <td className="px-3 py-1.5 text-quantum-green">{row[2]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StepBlock({
  step,
  title,
  desc,
  color,
}: {
  step: number;
  title: string;
  desc: string;
  color: "green" | "blue";
}) {
  const bg = color === "green" ? "bg-quantum-green/10" : "bg-quantum-blue/10";
  const text = color === "green" ? "text-quantum-green" : "text-quantum-blue";

  return (
    <div className={`${bg} rounded p-2.5 border border-[var(--border)]`}>
      <div className="flex items-center gap-2">
        <span className={`${text} text-xs font-bold`}>{step}.</span>
        <span className="text-xs font-semibold">{title}</span>
      </div>
      <div className="text-[10px] text-[var(--text-dim)] mt-0.5 ml-5">{desc}</div>
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
