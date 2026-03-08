export interface UserInfo {
  username: string;
  kyber_pk_bytes: number;
  kyber_sk_bytes: number;
  dilithium_pk_bytes: number;
  dilithium_sk_bytes: number;
  rsa_pk_bytes: number;
  kyber_fingerprint: string;
  dilithium_fingerprint: string;
  kyber_fingerprint_short: string;
  dilithium_fingerprint_short: string;
  pending_messages: number;
  inbox_count: number;
  unread_count: number;
  has_password: boolean;
  has_rsa_keys: boolean;
}

export interface AppState {
  kem_algorithm: string;
  sig_algorithm: string;
  dem_algorithm: string;
  mode: "demo" | "p2p";
  users: Record<string, UserInfo>;
  features: {
    zero_knowledge: boolean;
    forward_secrecy: boolean;
    websockets: boolean;
    multi_recipient: boolean;
    encrypted_attachments: boolean;
    email_threading: boolean;
  };
}

export interface Email {
  id: number;
  sender: string;
  subject: string;
  plaintext: string | null;
  verified: boolean;
  error: string | null;
  read: boolean;
  folder: string;
  enc_subject: boolean;
  thread_id: string | null;
  in_reply_to: string | null;
  timestamp: string;
}

export interface Folder {
  name: string;
  total: number;
  unread: number;
}

export interface Draft {
  id: number;
  recipient: string;
  subject: string;
  body: string;
  updated_at: string;
}

export interface Contact {
  id: number;
  name: string;
  username: string;
  kyber_fingerprint: string;
  dilithium_fingerprint: string;
  verified: boolean;
  notes: string;
  peer_address?: string;
}

export interface CryptoStep {
  step: number;
  title: string;
  description: string;
  details: Record<string, unknown>;
  status: "success" | "error" | "info";
}

export interface AuditEntry {
  id: number;
  action: string;
  details: string;
  ip_address: string;
  timestamp: string;
}

export interface BenchmarkResult {
  operation: string;
  avg_ms: number;
  size_bytes: number;
}

export interface SessionInfo {
  session_id: string;
  username: string;
  created_at: string;
  last_active: string;
  ip_address: string;
  user_agent: string;
}
