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

  return (
    <div className="max-w-2xl space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h2 className="text-sm font-bold text-[var(--text)]">Network & Contacts</h2>
          <p className="text-xs text-[var(--text-dim)]">
            Manage contacts and P2P LAN peer addresses for direct encrypted delivery.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="px-3 py-1.5 bg-accent text-white text-xs font-semibold rounded hover:bg-accent-light transition-colors"
        >
          {showForm ? "Cancel" : "+ Add Contact"}
        </button>
      </div>

      {/* Mode badge */}
      <div className="flex items-center gap-2 p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
        <span
          className={clsx(
            "w-2 h-2 rounded-full flex-shrink-0",
            isP2P ? "bg-quantum-green animate-pulse" : "bg-[var(--text-dim)]",
          )}
        />
        <div className="flex-1 min-w-0">
          <span className="text-xs font-semibold text-[var(--text)]">
            {isP2P ? "P2P LAN Mode Active" : "Demo / Server Mode"}
          </span>
          <p className="text-[11px] text-[var(--text-dim)] mt-0.5">
            {isP2P
              ? "Emails sent to contacts with a peer address are delivered directly over the local network — no server relay."
              : "Running in demo mode. Set QEC_P2P_ENABLED=1 to activate peer-to-peer LAN delivery."}
          </p>
        </div>
        <span
          className={clsx(
            "px-2 py-0.5 text-[10px] font-bold rounded flex-shrink-0",
            isP2P
              ? "bg-quantum-green/15 text-quantum-green"
              : "bg-[var(--surface2)] text-[var(--text-dim)]",
          )}
        >
          {isP2P ? "P2P" : "DEMO"}
        </span>
      </div>

      {/* Add contact form */}
      {showForm && (
        <div className="p-4 rounded-lg bg-[var(--surface)] border border-[var(--border)] space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-dim)]">
            New Contact
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-[var(--text-dim)]">
                Display Name <span className="text-quantum-red">*</span>
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Alice"
                className="w-full px-3 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-[var(--text-dim)]">
                Username <span className="text-quantum-red">*</span>
              </label>
              <input
                type="text"
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                placeholder="alice"
                className="w-full px-3 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent"
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[var(--text-dim)]">
              Peer Address{" "}
              <span className="text-[var(--text-dim)] font-normal">(optional — for P2P LAN delivery)</span>
            </label>
            <input
              type="text"
              value={form.peer_address}
              onChange={(e) => setForm((f) => ({ ...f, peer_address: e.target.value }))}
              placeholder="192.168.1.10:6001"
              className="w-full px-3 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded text-sm font-mono text-[var(--text)] focus:outline-none focus:border-accent"
            />
            <p className="text-[10px] text-[var(--text-dim)]">
              Format: IP:port — mail to this contact bypasses the server and goes directly over LAN.
            </p>
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-[var(--text-dim)]">Notes</label>
            <input
              type="text"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Optional notes..."
              className="w-full px-3 py-1.5 bg-[var(--bg)] border border-[var(--border)] rounded text-sm text-[var(--text)] focus:outline-none focus:border-accent"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleAdd}
              disabled={submitting || !form.name.trim() || !form.username.trim()}
              className="px-4 py-1.5 bg-accent text-white text-xs font-semibold rounded hover:bg-accent-light transition-colors disabled:opacity-50"
            >
              {submitting ? "Adding..." : "Add Contact"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 bg-[var(--surface2)] text-[var(--text-dim)] text-xs rounded hover:bg-[var(--border)] transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-3 py-2 rounded bg-quantum-red/10 border border-quantum-red/30 text-xs text-quantum-red">
          {error}
        </div>
      )}

      {/* Contacts list */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
            Contacts ({contacts.length})
          </span>
          <button
            onClick={loadContacts}
            className="text-[10px] text-accent hover:text-accent-light transition-colors"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : contacts.length === 0 ? (
          <div className="py-8 text-center text-xs text-[var(--text-dim)]">
            No contacts yet. Add one above.
          </div>
        ) : (
          <div className="rounded-lg border border-[var(--border)] overflow-hidden">
            {contacts.map((contact, i) => (
              <div
                key={contact.id}
                className={clsx(
                  "flex items-center gap-3 px-4 py-3",
                  i < contacts.length - 1 && "border-b border-[var(--border)]",
                  "bg-[var(--surface)] hover:bg-[var(--surface2)] transition-colors",
                )}
              >
                {/* Avatar */}
                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-accent">
                    {contact.name.charAt(0).toUpperCase()}
                  </span>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-[var(--text)] truncate">
                      {contact.name}
                    </span>
                    <span className="text-[11px] text-[var(--text-dim)]">@{contact.username}</span>
                    {contact.verified && (
                      <span className="px-1.5 py-0.5 bg-quantum-green/15 text-quantum-green text-[9px] font-bold rounded">
                        Verified
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    {contact.peer_address ? (
                      <span className="flex items-center gap-1 text-[11px] font-mono text-accent">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                        {contact.peer_address}
                      </span>
                    ) : (
                      <span className="text-[11px] text-[var(--text-dim)]">No P2P address</span>
                    )}
                    {contact.kyber_fingerprint && (
                      <span className="text-[10px] font-mono text-[var(--text-dim)] truncate max-w-[120px]">
                        KEM: {contact.kyber_fingerprint.slice(0, 12)}…
                      </span>
                    )}
                  </div>
                  {contact.notes && (
                    <div className="text-[11px] text-[var(--text-dim)] mt-0.5 truncate">
                      {contact.notes}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <button
                  onClick={() => handleDelete(contact.id)}
                  className="text-[11px] text-quantum-red/60 hover:text-quantum-red transition-colors flex-shrink-0"
                  title="Remove contact"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* P2P info box */}
      <div className="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[11px] text-[var(--text-dim)] space-y-1">
        <div className="font-semibold text-[var(--text)] text-xs mb-1">How P2P LAN delivery works</div>
        <p>
          When a contact has a peer address set, encrypted mail is sent directly to their node over your
          local network via <span className="font-mono text-accent">POST /p2p/incoming</span>. The
          cryptographic payload (KEM + signature + ciphertext) is identical — only the transport changes.
        </p>
        <p>
          Both nodes must run Schrödinger Mail with <span className="font-mono text-accent">QEC_P2P_ENABLED=1</span> and
          be reachable on the same LAN segment.
        </p>
      </div>
    </div>
  );
}
