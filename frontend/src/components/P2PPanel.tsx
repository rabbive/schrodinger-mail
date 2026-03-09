import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import type { Contact } from "@/types";
import clsx from "clsx";

export default function P2PPanel() {
  const { activeUser, appState } = useStore();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    username: "",
    peer_address: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const isP2P = appState?.mode === "p2p";

  const loadContacts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getContacts(activeUser);
      setContacts(data.contacts);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load contacts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContacts();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeUser]);

  const handleAdd = async () => {
    if (!form.name.trim() || !form.username.trim()) return;
    setSubmitting(true);
    try {
      await api.addContact(activeUser, {
        name: form.name.trim(),
        username: form.username.trim().toLowerCase(),
        peer_address: form.peer_address.trim() || undefined,
        notes: form.notes.trim(),
      });
      setForm({ name: "", username: "", peer_address: "", notes: "" });
      setShowForm(false);
      await loadContacts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add contact");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (contactId: number) => {
    try {
      await api.deleteContact(activeUser, contactId);
      await loadContacts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete contact");
    }
  };

  const verified = contacts.filter((c) => c.verified);
  const unverified = contacts.filter((c) => !c.verified);
  const sorted = [...verified, ...unverified];

  const inputClass =
    "w-full px-3 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded text-[13px] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-none focus:border-accent transition-colors";

  return (
    <div className="max-w-2xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[13px] font-semibold text-[var(--text)]">Network & Contacts</h2>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Manage contacts and peer addresses for direct encrypted delivery.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="px-3 py-1.5 bg-accent text-white text-[12px] font-medium rounded hover:bg-accent-light transition-colors"
        >
          {showForm ? "Cancel" : "Add Contact"}
        </button>
      </div>

      {/* Mode badge */}
      <div className="flex items-center gap-3 p-3 rounded border border-[var(--border)] bg-[var(--surface)]">
        <span
          className={clsx(
            "w-2 h-2 rounded-full flex-shrink-0",
            isP2P ? "bg-quantum-green animate-pulse-gentle" : "bg-[var(--text-muted)]",
          )}
        />
        <div className="flex-1 min-w-0">
          <span className="text-[12px] font-medium text-[var(--text)]">
            {isP2P ? "P2P LAN Mode Active" : "Demo / Server Mode"}
          </span>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            {isP2P
              ? "Contacts with a peer address receive mail directly over LAN."
              : "Running in demo mode. Set QEC_P2P_ENABLED=1 for peer-to-peer delivery."}
          </p>
        </div>
        <span
          className={clsx(
            "px-2 py-0.5 text-[10px] font-mono font-medium rounded border flex-shrink-0",
            isP2P
              ? "bg-quantum-green/10 text-quantum-green border-quantum-green/20"
              : "bg-[var(--surface2)] text-[var(--text-muted)] border-[var(--border)]",
          )}
        >
          {isP2P ? "P2P" : "DEMO"}
        </span>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="p-4 rounded border border-[var(--border)] bg-[var(--surface)] space-y-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            New Contact
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-[var(--text-dim)]">
                Display Name <span className="text-quantum-red">*</span>
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Alice"
                className={inputClass}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-[var(--text-dim)]">
                Username <span className="text-quantum-red">*</span>
              </label>
              <input
                type="text"
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                placeholder="alice"
                className={inputClass}
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-[var(--text-dim)]">
              Peer Address
              <span className="font-normal text-[var(--text-muted)]"> (optional — P2P LAN delivery)</span>
            </label>
            <input
              type="text"
              value={form.peer_address}
              onChange={(e) => setForm((f) => ({ ...f, peer_address: e.target.value }))}
              placeholder="192.168.1.10:6001"
              className={clsx(inputClass, "font-mono")}
            />
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-[var(--text-dim)]">Notes</label>
            <input
              type="text"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Optional notes..."
              className={inputClass}
            />
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleAdd}
              disabled={submitting || !form.name.trim() || !form.username.trim()}
              className="px-4 py-1.5 bg-accent text-white text-[12px] font-medium rounded hover:bg-accent-light transition-colors disabled:opacity-50"
            >
              {submitting ? "Adding..." : "Add Contact"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 bg-[var(--surface2)] text-[var(--text-dim)] text-[12px] rounded border border-[var(--border)] hover:bg-[var(--surface3)] transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-3 py-2 rounded bg-quantum-red/8 border border-quantum-red/20 text-[12px] text-quantum-red">
          {error}
        </div>
      )}

      {/* Contact list */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Contacts ({contacts.length})
          </span>
          <button
            onClick={loadContacts}
            className="text-[10px] text-[var(--text-muted)] hover:text-accent transition-colors"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : contacts.length === 0 ? (
          <div className="py-8 text-center text-[11px] text-[var(--text-muted)]">
            No contacts yet. Add one above.
          </div>
        ) : (
          <div className="rounded border border-[var(--border)] overflow-hidden">
            {sorted.map((contact, i) => (
              <div
                key={contact.id}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5",
                  i < sorted.length - 1 && "border-b border-[var(--border)]",
                  "bg-[var(--surface)] hover:bg-[var(--surface2)] transition-colors",
                )}
              >
                <div className="w-7 h-7 rounded bg-accent/10 flex items-center justify-center flex-shrink-0">
                  <span className="text-[11px] font-bold text-accent">
                    {contact.name.charAt(0).toUpperCase()}
                  </span>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-medium text-[var(--text)] truncate">
                      {contact.name}
                    </span>
                    <span className="text-[11px] font-mono text-[var(--text-muted)]">@{contact.username}</span>
                    {contact.verified && (
                      <span className="px-1 py-0.5 bg-quantum-green/10 text-quantum-green text-[9px] font-mono font-medium rounded">
                        verified
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    {contact.peer_address ? (
                      <span className="flex items-center gap-1 text-[10px] font-mono text-accent">
                        <span className="w-1 h-1 rounded-full bg-accent" />
                        {contact.peer_address}
                      </span>
                    ) : (
                      <span className="text-[10px] text-[var(--text-muted)]">server relay</span>
                    )}
                    {contact.kyber_fingerprint && (
                      <span className="text-[9px] font-mono text-[var(--text-muted)] truncate max-w-[100px]">
                        KEM:{contact.kyber_fingerprint.slice(0, 10)}
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(contact.id)}
                  className="text-[10px] text-[var(--text-muted)] hover:text-quantum-red transition-colors flex-shrink-0"
                  title="Remove contact"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 rounded border border-[var(--border)] bg-[var(--surface)] text-[11px] text-[var(--text-muted)] space-y-1.5">
        <div className="font-medium text-[var(--text-dim)] text-[12px]">How P2P LAN delivery works</div>
        <p>
          When a contact has a peer address, encrypted mail is sent directly to their node over the local
          network via <span className="font-mono text-accent">POST /p2p/incoming</span>. The cryptographic
          payload is identical to server relay — only the transport changes.
        </p>
        <p>
          Both nodes must run Schrödinger Mail with <span className="font-mono text-accent">QEC_P2P_ENABLED=1</span> and
          be reachable on the same LAN.
        </p>
      </div>
    </div>
  );
}
