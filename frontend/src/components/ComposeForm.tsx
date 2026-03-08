import { useState } from "react";
import { useStore } from "@/hooks/useStore";

interface Props {
  showNotification: (message: string, type: "success" | "error" | "info") => void;
}

export default function ComposeForm({ showNotification }: Props) {
  const { appState, activeUser, sendEmail } = useStore();
  const [recipient, setRecipient] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [securityLevel, setSecurityLevel] = useState(1);
  const [encryptSubject, setEncryptSubject] = useState(false);
  const [password, setPassword] = useState("");
  const [sending, setSending] = useState(false);

  const otherUsers = appState
    ? Object.keys(appState.users).filter((u) => u !== activeUser)
    : [];

  const handleSend = async () => {
    if (!recipient || !subject || !body) {
      showNotification("Please fill in all fields.", "error");
      return;
    }
    setSending(true);
    try {
      await sendEmail({
        recipient,
        subject,
        body,
        securityLevel,
        encryptSubject,
        password: securityLevel === 1 ? password : undefined,
      });
      showNotification("Email sent and encrypted successfully!", "success");
      setSubject("");
      setBody("");
      setPassword("");
    } catch (err) {
      showNotification(err instanceof Error ? err.message : "Send failed.", "error");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-3">
      <div className="space-y-1">
        <label className="text-xs font-semibold text-[var(--text-dim)]">To</label>
        <select
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          className="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent"
        >
          <option value="">Select recipient...</option>
          {otherUsers.map((u) => (
            <option key={u} value={u}>
              {u.charAt(0).toUpperCase() + u.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1">
        <label className="text-xs font-semibold text-[var(--text-dim)]">Subject</label>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Enter subject..."
          className="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent"
        />
      </div>

      <div className="space-y-1">
        <label className="text-xs font-semibold text-[var(--text-dim)]">Body</label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Write your message..."
          rows={8}
          className="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent resize-y font-inherit"
        />
      </div>

      <div className="space-y-1">
        <label className="text-xs font-semibold text-[var(--text-dim)]">Security Level</label>
        <select
          value={securityLevel}
          onChange={(e) => setSecurityLevel(Number(e.target.value))}
          className="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent"
        >
          <option value={1}>Level 1 — Password-Protected (scrypt KDF)</option>
          <option value={2}>Level 2 — Post-Quantum (Kyber768 + Dilithium3)</option>
          <option value={3}>Level 3 — Hybrid Defense-in-Depth (RSA-2048 + Kyber768)</option>
        </select>
      </div>

      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={encryptSubject}
          onChange={(e) => setEncryptSubject(e.target.checked)}
          className="accent-accent"
        />
        Encrypt subject line
      </label>

      {securityLevel === 1 && (
        <div className="space-y-1">
          <label className="text-xs font-semibold text-[var(--text-dim)]">
            Password for recipient
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Shared password..."
            className="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent"
          />
        </div>
      )}

      <div className="flex items-center gap-2 pt-2">
        <button
          onClick={handleSend}
          disabled={sending}
          className="px-5 py-2 bg-accent hover:bg-accent-light text-white text-sm font-semibold rounded transition-colors disabled:opacity-50"
        >
          {sending ? "Encrypting..." : "Send Encrypted"}
        </button>
        <button className="px-3 py-2 bg-[var(--surface2)] text-[var(--text-dim)] text-xs font-medium rounded hover:bg-[var(--border)] transition-colors">
          Save Draft
        </button>
      </div>

      {appState?.features && (
        <div className="flex gap-2 mt-3">
          {appState.features.forward_secrecy && (
            <span className="px-2 py-0.5 bg-quantum-green/10 text-quantum-green text-[10px] font-bold rounded">
              Forward Secrecy
            </span>
          )}
          {appState.features.encrypted_attachments && (
            <span className="px-2 py-0.5 bg-quantum-blue/10 text-quantum-blue text-[10px] font-bold rounded">
              Encrypted Attachments
            </span>
          )}
          {appState.features.multi_recipient && (
            <span className="px-2 py-0.5 bg-accent/10 text-accent text-[10px] font-bold rounded">
              Multi-Recipient
            </span>
          )}
        </div>
      )}
    </div>
  );
}
