import { useState } from "react";
import { useStore } from "@/hooks/useStore";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Send,
  Save,
  Lock,
  ShieldCheck,
  Shield,
  Layers,
  Wifi,
  Monitor,
  ArrowRightLeft,
  Paperclip,
  Users,
} from "lucide-react";

interface Props {
  showNotification: (message: string, type: "success" | "error" | "info") => void;
}

const SECURITY_LEVELS = [
  {
    value: 1,
    label: "Level 1",
    name: "Password-Protected",
    detail: "scrypt KDF — shared password derives the encryption key",
    icon: Lock,
  },
  {
    value: 2,
    label: "Level 2",
    name: "Post-Quantum",
    detail: "Kyber768 KEM + Dilithium3 signatures — quantum-resistant",
    icon: ShieldCheck,
  },
  {
    value: 3,
    label: "Level 3",
    name: "Hybrid Defense-in-Depth",
    detail: "RSA-2048 + Kyber768 combined — maximum security",
    icon: Layers,
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

  return (
    <div className="max-w-2xl space-y-4">
      <div className="flex items-center gap-2">
        <Badge variant={isP2P ? "success" : "outline"} className="gap-1">
          {isP2P ? <Wifi className="w-3 h-3" /> : <Monitor className="w-3 h-3" />}
          {isP2P ? "P2P LAN" : "Demo Mode"}
        </Badge>
        <span className="text-[11px] text-muted-foreground">
          Sending as <span className="text-foreground font-medium capitalize">{activeUser}</span>
        </span>
      </div>

      <div className="space-y-1.5">
        <Label>To</Label>
        <Select value={recipient} onChange={(e) => setRecipient(e.target.value)}>
          <option value="">Select recipient...</option>
          {otherUsers.map((u) => (
            <option key={u} value={u}>
              {u.charAt(0).toUpperCase() + u.slice(1)}
            </option>
          ))}
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Subject</Label>
        <Input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Enter subject..."
        />
      </div>

      <div className="space-y-1.5">
        <Label>Body</Label>
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Write your message..."
          rows={8}
          className="resize-y"
        />
      </div>

      <div className="space-y-2">
        <Label>Security Level</Label>
        <div className="space-y-1.5">
          {SECURITY_LEVELS.map((lvl) => {
            const Icon = lvl.icon;
            return (
              <button
                key={lvl.value}
                type="button"
                onClick={() => setSecurityLevel(lvl.value)}
                className={cn(
                  "w-full text-left px-3 py-2.5 rounded-md border transition-all",
                  securityLevel === lvl.value
                    ? "bg-primary/8 border-primary/40 ring-1 ring-primary/20"
                    : "bg-card border-border hover:border-border/80 hover:bg-secondary",
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0",
                      securityLevel === lvl.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-muted-foreground border border-border",
                    )}
                  >
                    <Icon className="w-3 h-3" />
                  </span>
                  <span
                    className={cn(
                      "text-[12px] font-semibold",
                      securityLevel === lvl.value ? "text-primary" : "text-foreground",
                    )}
                  >
                    {lvl.label} — {lvl.name}
                  </span>
                </div>
                <div className="text-[11px] text-muted-foreground mt-1 ml-7">
                  {lvl.detail}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <label className="flex items-center gap-2 text-[12px] text-muted-foreground cursor-pointer">
        <input
          type="checkbox"
          checked={encryptSubject}
          onChange={(e) => setEncryptSubject(e.target.checked)}
          className="accent-primary w-3.5 h-3.5 rounded"
        />
        <Shield className="w-3 h-3" />
        Encrypt subject line
      </label>

      {securityLevel === 1 && (
        <div className="space-y-1.5">
          <Label className="flex items-center gap-1.5">
            <Lock className="w-3 h-3" />
            Shared Password
          </Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Both parties must know this password..."
          />
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        <Button onClick={handleSend} disabled={sending}>
          <Send className="w-3.5 h-3.5" />
          {sending ? "Encrypting..." : "Send Encrypted"}
        </Button>
        <Button variant="secondary">
          <Save className="w-3.5 h-3.5" />
          Save Draft
        </Button>
      </div>

      {appState?.features && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {appState.features.forward_secrecy && (
            <Badge variant="success" className="gap-1">
              <ArrowRightLeft className="w-3 h-3" />
              Forward Secrecy
            </Badge>
          )}
          {appState.features.encrypted_attachments && (
            <Badge variant="info" className="gap-1">
              <Paperclip className="w-3 h-3" />
              Encrypted Attachments
            </Badge>
          )}
          {appState.features.multi_recipient && (
            <Badge className="gap-1">
              <Users className="w-3 h-3" />
              Multi-Recipient
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
