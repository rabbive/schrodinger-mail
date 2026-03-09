import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import type { Contact } from "@/types";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Globe,
  UserPlus,
  Wifi,
  Monitor,
  RefreshCw,
  Trash2,
  ShieldCheck,
  Loader2,
  Network,
  Activity,
  Server,
  Radio,
} from "lucide-react";

interface TraceEvent {
  action: string;
  details: string;
  ip: string;
  timestamp: string;
  transport: string;
}

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

  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);
  const [localAddress, setLocalAddress] = useState("");
  const [activeSection, setActiveSection] = useState<"contacts" | "trace">("contacts");

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

  const loadTrace = async () => {
    setTraceLoading(true);
    try {
      const data = await api.getNetworkTrace(activeUser);
      setTraceEvents(data.events);
      setLocalAddress(data.local_address);
    } catch {
      setTraceEvents([]);
    } finally {
      setTraceLoading(false);
    }
  };

  useEffect(() => {
    loadContacts();
    loadTrace();
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

  const actionLabel = (action: string) => {
    const labels: Record<string, string> = {
      send_email: "Send",
      send_multi: "Multi-Send",
      send_forged: "Forge (attack)",
      send_password_protected: "Send (L1)",
      receive_email: "Receive",
      p2p_received: "P2P Receive",
      p2p_sent: "P2P Send",
      tamper_demo: "Tamper (attack)",
      replay_demo: "Replay (attack)",
    };
    return labels[action] || action;
  };

  const actionColor = (action: string) => {
    if (action.includes("tamper") || action.includes("forge") || action.includes("replay"))
      return "text-destructive";
    if (action.includes("receive") || action.includes("p2p_received"))
      return "text-quantum-green";
    return "text-primary";
  };

  return (
    <div className="max-w-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-primary" />
          <div>
            <h2 className="text-[13px] font-semibold text-foreground">Network & Contacts</h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Manage contacts, peer addresses, and view network delivery trace.
            </p>
          </div>
        </div>
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          <UserPlus className="w-3.5 h-3.5" />
          {showForm ? "Cancel" : "Add Contact"}
        </Button>
      </div>

      <Card className="flex items-center gap-3 p-3">
        <span
          className={cn(
            "w-2 h-2 rounded-full flex-shrink-0",
            isP2P ? "bg-quantum-green animate-pulse-gentle" : "bg-muted-foreground",
          )}
        />
        <div className="flex-1 min-w-0">
          <span className="text-[12px] font-medium text-foreground flex items-center gap-1.5">
            {isP2P ? <Wifi className="w-3 h-3 text-quantum-green" /> : <Monitor className="w-3 h-3" />}
            {isP2P ? "P2P LAN Mode Active" : "Demo / Server Mode"}
          </span>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {isP2P
              ? "Contacts with a peer address receive mail directly over LAN."
              : "Running in demo mode. Set QEC_P2P_ENABLED=1 for peer-to-peer delivery."}
          </p>
        </div>
        <Badge variant={isP2P ? "success" : "outline"}>
          {isP2P ? "P2P" : "DEMO"}
        </Badge>
      </Card>

      <div className="flex gap-1 p-0.5 bg-secondary rounded-md">
        <button
          onClick={() => setActiveSection("contacts")}
          className={cn(
            "flex-1 py-1.5 text-[11px] font-medium rounded-md transition-colors flex items-center justify-center gap-1.5",
            activeSection === "contacts"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground/60",
          )}
        >
          <Network className="w-3 h-3" /> Contacts ({contacts.length})
        </button>
        <button
          onClick={() => {
            setActiveSection("trace");
            loadTrace();
          }}
          className={cn(
            "flex-1 py-1.5 text-[11px] font-medium rounded-md transition-colors flex items-center justify-center gap-1.5",
            activeSection === "trace"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground/60",
          )}
        >
          <Activity className="w-3 h-3" /> Network Trace ({traceEvents.length})
        </button>
      </div>

      {showForm && (
        <Card className="p-4 space-y-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <UserPlus className="w-3 h-3" /> New Contact
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>
                Display Name <span className="text-destructive">*</span>
              </Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Alice"
              />
            </div>
            <div className="space-y-1">
              <Label>
                Username <span className="text-destructive">*</span>
              </Label>
              <Input
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                placeholder="alice"
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label>
              Peer Address
              <span className="font-normal text-muted-foreground"> (optional — P2P LAN delivery)</span>
            </Label>
            <Input
              value={form.peer_address}
              onChange={(e) => setForm((f) => ({ ...f, peer_address: e.target.value }))}
              placeholder="192.168.1.10:6001"
              className="font-mono"
            />
          </div>
          <div className="space-y-1">
            <Label>Notes</Label>
            <Input
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Optional notes..."
            />
          </div>
          <div className="flex gap-2 pt-1">
            <Button
              onClick={handleAdd}
              disabled={submitting || !form.name.trim() || !form.username.trim()}
              size="sm"
            >
              <UserPlus className="w-3.5 h-3.5" />
              {submitting ? "Adding..." : "Add Contact"}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {error && (
        <div className="px-3 py-2 rounded-md bg-destructive/8 border border-destructive/20 text-[12px] text-destructive">
          {error}
        </div>
      )}

      {activeSection === "contacts" && (
        <div className="space-y-2">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
            </div>
          ) : contacts.length === 0 ? (
            <div className="py-8 text-center text-[11px] text-muted-foreground">
              No contacts yet. Add one above.
            </div>
          ) : (
            <Card className="overflow-hidden">
              {sorted.map((contact, i) => (
                <div
                  key={contact.id}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5",
                    i < sorted.length - 1 && "border-b",
                    "hover:bg-secondary transition-colors",
                  )}
                >
                  <div className="w-7 h-7 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <span className="text-[11px] font-bold text-primary">
                      {contact.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] font-medium text-foreground truncate">
                        {contact.name}
                      </span>
                      <span className="text-[11px] font-mono text-muted-foreground">
                        @{contact.username}
                      </span>
                      {contact.verified && (
                        <Badge variant="success" className="gap-0.5">
                          <ShieldCheck className="w-2.5 h-2.5" /> verified
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      {contact.peer_address ? (
                        <span className="flex items-center gap-1 text-[10px] font-mono text-primary">
                          <Radio className="w-2.5 h-2.5" /> {contact.peer_address}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                          <Server className="w-2.5 h-2.5" /> server relay
                        </span>
                      )}
                      {contact.kyber_fingerprint && (
                        <span className="text-[9px] font-mono text-muted-foreground truncate max-w-[100px]">
                          KEM:{contact.kyber_fingerprint.slice(0, 10)}
                        </span>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(contact.id)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="w-3 h-3" /> Remove
                  </Button>
                </div>
              ))}
            </Card>
          )}
        </div>
      )}

      {activeSection === "trace" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Delivery Events
            </span>
            <div className="flex items-center gap-2">
              {localAddress && (
                <span className="text-[10px] font-mono text-muted-foreground">
                  Local: {localAddress}
                </span>
              )}
              <Button variant="ghost" size="sm" onClick={loadTrace} className="h-5 px-1.5 text-[10px]">
                <RefreshCw className="w-3 h-3" /> Refresh
              </Button>
            </div>
          </div>

          {traceLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
            </div>
          ) : traceEvents.length === 0 ? (
            <div className="py-8 text-center text-[11px] text-muted-foreground">
              No network events recorded yet. Send or receive messages to see the trace.
            </div>
          ) : (
            <Card className="overflow-hidden">
              {traceEvents.map((evt, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex items-start gap-3 px-3 py-2",
                    i < traceEvents.length - 1 && "border-b",
                  )}
                >
                  <div className="flex flex-col items-center flex-shrink-0 pt-1">
                    <span
                      className={cn(
                        "w-2 h-2 rounded-full flex-shrink-0",
                        evt.action.includes("tamper") || evt.action.includes("forge") || evt.action.includes("replay")
                          ? "bg-destructive"
                          : evt.action.includes("receive")
                            ? "bg-quantum-green"
                            : "bg-primary",
                      )}
                    />
                    {i < traceEvents.length - 1 && (
                      <div className="w-px h-full bg-border mt-1" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn("text-[11px] font-semibold", actionColor(evt.action))}>
                        {actionLabel(evt.action)}
                      </span>
                      <Badge variant={evt.transport === "p2p" ? "success" : "outline"} className="text-[9px]">
                        {evt.transport === "p2p" ? "P2P" : "SERVER"}
                      </Badge>
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-0.5 truncate">
                      {evt.details}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-[9px] font-mono text-muted-foreground">
                        {evt.timestamp}
                      </span>
                      {evt.ip && (
                        <span className="text-[9px] font-mono text-muted-foreground">
                          IP: {evt.ip}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </Card>
          )}
        </div>
      )}

      <Card className="p-3 text-[11px] text-muted-foreground space-y-1.5">
        <div className="font-medium text-foreground/70 text-[12px] flex items-center gap-1.5">
          <Globe className="w-3 h-3" /> How P2P LAN delivery works
        </div>
        <p>
          When a contact has a peer address, encrypted mail is sent directly to their node over the local
          network via <span className="font-mono text-primary">POST /p2p/incoming</span>. The cryptographic
          payload is identical to server relay — only the transport changes.
        </p>
        <p>
          Both nodes must run Schrödinger Mail with <span className="font-mono text-primary">QEC_P2P_ENABLED=1</span> and
          be reachable on the same LAN.
        </p>
      </Card>
    </div>
  );
}
