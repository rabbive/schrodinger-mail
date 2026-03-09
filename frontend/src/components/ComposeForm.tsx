import { useState } from "react";
import { useStore } from "@/hooks/useStore";
import clsx from "clsx";

interface Props {
  showNotification: (message: string, type: "success" | "error" | "info") => void;
}

const SECURITY_LEVELS = [
  {
    value: 1,
    label: "Level 1",
    name: "Password-Protected",
    detail: "scrypt KDF — shared password derives the encryption key",
  },
  {
    value: 2,
    label: "Level 2",
    name: "Post-Quantum",
    detail: "Kyber768 KEM + Dilithium3 signatures — quantum-resistant",
  },
  {
    value: 3,
    label: "Level 3",
    name: "Hybrid Defense-in-Depth",
    detail: "RSA-2048 + Kyber768 combined — maximum security",
  },
];

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

  const isP2P = appState?.mode === "p2p";

  const handleSend = async () => {
    if (!recipient || !subject || !body) {
      showNotification("Please fill in all fields.", "error");
      return;
    }
    if (securityLevel === 1 && !password) {
      showNotification("Password is required for Level 1.", "error");
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

  const inputClass =
    "w-full px-3 py-2 bg-[var(--bg)] border border-[var(--border)] rounded text-[13px] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:border-accent transition-colors";

  return (
    <div className="max-w-2xl space-y-4">
      {/* Transport mode chip */}
      <div className="flex items-center gap-2">
        <span className={clsx(
          "px-2 py-0.5 text-[10px] font-mono font-medium rounded border",
          isP2P
            ? "bg-quantum-green/10 text-quantum-green border-quantum-green/20"
            : "bg-[var(--surface2)] text-[var(--text-muted)] border-[var(--border)]",
        )}>
          {isP2P ? "P2P LAN" : "Demo Mode"}
        </span>
        <span className="text-[11px] text-[var(--text-muted)]">
          Sending as <span className="text-[var(--text)] font-medium capitalize">{activeUser}</span>
        </span>
      </div>

      {/* To */}
      <div className="space-y-1.5">
        <label className="text-[12px] font-medium text-[var(--text-dim)]">To</label>
        <select
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          className={inputClass}
        >
          <option value="">Select recipient...</option>
          {otherUsers.map((u) => (
            <option key={u} value={u}>
              {u.charAt(0).toUpperCase() + u.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Subject */}
      <div className="space-y-1.5">
        <label className="text-[12px] font-medium text-[var(--text-dim)]">Subject</label>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Enter subject..."
          className={inputClass}
        />
      </div>

      {/* Body */}
      <div className="space-y-1.5">
        <label className="text-[12px] font-medium text-[var(--text-dim)]">Body</label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Write your message..."
          rows={8}
          className={clsx(inputClass, "resize-y")}
        />
      </div>

      {/* Security Level — card selector */}
      <div className="space-y-2">
        <label className="text-[12px] font-medium text-[var(--text-dim)]">Security Level</label>
        <div className="space-y-1.5">
          {SECURITY_LEVELS.map((lvl) => (
            <button
              key={lvl.value}
              type="button"
              onClick={() => setSecurityLevel(lvl.value)}
              className={clsx(
                "w-full text-left px-3 py-2.5 rounded border transition-all",
                securityLevel === lvl.value
                  ? "bg-accent/8 border-accent/40 ring-1 ring-accent/20"
                  : "bg-[var(--surface)] border-[var(--border)] hover:border-[var(--border-light)] hover:bg-[var(--surface2)]",
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={clsx(
                    "w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold flex-shrink-0",
                    securityLevel === lvl.value
                      ? "bg-accent text-white"
                      : "bg-[var(--surface2)] text-[var(--text-muted)] border border-[var(--border)]",
                  )}
                >
                  {lvl.value}
                </span>
                <span
                  className={clsx(
                    "text-[12px] font-semibold",
                    securityLevel === lvl.value ? "text-accent" : "text-[var(--text)]",
                  )}
                >
                  {lvl.label} — {lvl.name}
                </span>
              </div>
              <div className="text-[11px] text-[var(--text-dim)] mt-1 ml-7">
                {lvl.detail}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Encrypt subject */}
      <label className="flex items-center gap-2 text-[12px] text-[var(--text-dim)] cursor-pointer">
        <input
          type="checkbox"
          checked={encryptSubject}
          onChange={(e) => setEncryptSubject(e.target.checked)}
          className="accent-accent w-3.5 h-3.5"
        />
        Encrypt subject line
      </label>

      {/* Password field for Level 1 */}
      {securityLevel === 1 && (
        <div className="space-y-1.5">
          <label className="text-[12px] font-medium text-[var(--text-dim)]">
            Shared Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Both parties must know this password..."
            className={inputClass}
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleSend}
          disabled={sending}
          className="px-4 py-2 bg-accent hover:bg-accent-light text-white text-[12px] font-semibold rounded transition-colors disabled:opacity-50"
        >
          {sending ? "Encrypting..." : "Send Encrypted"}
        </button>
        <button className="px-3 py-2 bg-[var(--surface2)] text-[var(--text-dim)] text-[12px] font-medium rounded border border-[var(--border)] hover:bg-[var(--surface3)] transition-colors">
          Save Draft
        </button>
      </div>

      {/* Feature badges */}
      {appState?.features && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {appState.features.forward_secrecy && (
            <span className="px-2 py-0.5 bg-quantum-green/8 text-quantum-green text-[10px] font-mono font-medium rounded border border-quantum-green/15">
              Forward Secrecy
            </span>
          )}
          {appState.features.encrypted_attachments && (
            <span className="px-2 py-0.5 bg-quantum-blue/8 text-quantum-blue text-[10px] font-mono font-medium rounded border border-quantum-blue/15">
              Encrypted Attachments
            </span>
          )}
          {appState.features.multi_recipient && (
            <span className="px-2 py-0.5 bg-accent/8 text-accent text-[10px] font-mono font-medium rounded border border-accent/15">
              Multi-Recipient
            </span>
          )}
        </div>
      )}
    </div>
  );
}
