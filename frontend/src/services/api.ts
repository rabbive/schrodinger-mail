import type {
  AppState, AuditEntry, BenchmarkResult, Contact, CryptoStep,
  Draft, Email, Folder, SessionInfo,
} from "@/types";

const BASE = "";

let accessToken: string | null = null;

function headers(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (accessToken) h["Authorization"] = `Bearer ${accessToken}`;
  return h;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: headers() });
  if (!res.ok) throw new Error((await res.json()).error ?? res.statusText);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) throw new Error((await res.json()).error ?? res.statusText);
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "DELETE",
    headers: headers(),
  });
  return res.json();
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export const api = {
  // Auth
  login: (username: string, password?: string) =>
    post<{ ok: boolean; user: unknown; access_token: string; refresh_token: string }>(
      "/api/auth/login",
      { username, password },
    ),
  logout: () => post<{ ok: boolean }>("/api/auth/logout"),
  register: (username: string, password?: string) =>
    post<{ ok: boolean; user: unknown; steps: CryptoStep[] }>(
      "/api/register",
      { username, password },
    ),
  authStatus: () =>
    get<{ auth_enabled: boolean; logged_in: boolean; username: string; csrf_token: string }>(
      "/api/auth/status",
    ),
  refreshToken: (refreshToken: string) =>
    post<{ access_token: string; refresh_token: string }>("/api/auth/refresh", {
      refresh_token: refreshToken,
    }),
  setPassword: (username: string, password: string) =>
    post<{ ok: boolean }>("/api/auth/set-password", { username, password }),

  // State
  getState: () => get<AppState>("/api/state"),

  // Folders & Emails
  getFolders: (username: string) =>
    get<{ folders: Folder[] }>(`/api/folders/${username}`),
  getEmails: (username: string, folder: string) =>
    get<{ emails: Email[] }>(`/api/emails/${username}/${folder}`),
  getInbox: (username: string) =>
    get<{ emails: Email[] }>(`/api/inbox/${username}`),
  moveEmail: (username: string, emailId: number, folder: string) =>
    post<{ ok: boolean }>(`/api/move/${username}/${emailId}`, { folder }),
  deleteEmail: (username: string, emailId: number) =>
    post<{ ok: boolean }>(`/api/delete/${username}/${emailId}`),
  deletePermanent: (username: string, emailId: number) =>
    del<{ ok: boolean }>(`/api/delete-permanent/${username}/${emailId}`),
  emptyTrash: (username: string) =>
    del<{ ok: boolean }>(`/api/empty-trash/${username}`),
  markRead: (username: string, emailId: number) =>
    post<{ ok: boolean }>(`/api/read/${username}/${emailId}`),
  search: (username: string, query: string) =>
    get<{ emails: Email[] }>(`/api/search/${username}?q=${encodeURIComponent(query)}`),

  // Thread
  getThread: (threadId: string) =>
    get<{ thread_id: string; emails: Email[] }>(`/api/thread/${threadId}`),

  // Send / Receive
  send: (data: {
    sender: string;
    recipient: string;
    recipients?: string[];
    subject: string;
    body: string;
    encrypt_subject?: boolean;
    security_level?: number;
    password?: string;
    thread_id?: string;
    in_reply_to?: string;
  }) => {
    const url = data.security_level === 1 ? "/api/send-password" : "/api/send";
    return post<{ ok: boolean; steps: CryptoStep[] }>(url, data);
  },
  sendForged: (data: { sender: string; recipient: string; subject: string; body: string }) =>
    post<{ ok: boolean; steps: CryptoStep[] }>("/api/send-forged", data),
  receive: (username: string) =>
    post<{ ok: boolean; steps: CryptoStep[]; results: Email[] }>(`/api/receive/${username}`),
  tamper: (username: string) =>
    post<{ ok: boolean }>(`/api/tamper/${username}`),
  replay: (username: string) =>
    post<{ ok: boolean }>(`/api/replay/${username}`),

  // Reply / Forward
  reply: (data: {
    original_sender: string;
    original_subject: string;
    original_body: string;
    thread_id?: string;
    message_id?: string;
  }) => post<{ recipient: string; subject: string; body: string; thread_id?: string }>(
    "/api/reply",
    data,
  ),
  forward: (data: {
    original_sender: string;
    original_subject: string;
    original_body: string;
  }) => post<{ subject: string; body: string }>("/api/forward", data),

  // Drafts
  getDrafts: (username: string) =>
    get<{ drafts: Draft[] }>(`/api/drafts/${username}`),
  saveDraft: (username: string, data: Partial<Draft>) =>
    post<{ ok: boolean; draft_id: number }>(`/api/draft/${username}`, data),
  deleteDraft: (username: string, draftId: number) =>
    del<{ ok: boolean }>(`/api/draft/${username}/${draftId}`),

  // Contacts
  getContacts: (username: string) =>
    get<{ contacts: Contact[] }>(`/api/contacts/${username}`),
  addContact: (username: string, data: Partial<Contact>) =>
    post<{ ok: boolean; contact_id: number }>(`/api/contacts/${username}`, data),
  deleteContact: (username: string, contactId: number) =>
    del<{ ok: boolean }>(`/api/contacts/${username}/${contactId}`),

  // Keys
  getKeys: (username: string) => get<Record<string, unknown>>(`/api/keys/${username}`),
  verifyKeys: (userA: string, userB: string) =>
    post<{ user_a: Record<string, string>; user_b: Record<string, string> }>(
      "/api/keys/verify",
      { user_a: userA, user_b: userB },
    ),

  // Settings
  getSettings: (username: string) =>
    get<{ settings: Record<string, unknown> }>(`/api/settings/${username}`),
  saveSettings: (username: string, data: Record<string, unknown>) =>
    post<{ ok: boolean }>(`/api/settings/${username}`, data),

  // Audit
  getAuditLog: (username: string, limit?: number) =>
    get<{ log: AuditEntry[] }>(`/api/audit/${username}?limit=${limit ?? 100}`),

  // Sessions
  getSessions: (username: string) =>
    get<{ sessions: SessionInfo[] }>(`/api/sessions/${username}`),
  revokeSession: (sessionId: string) =>
    del<{ ok: boolean }>(`/api/sessions/${sessionId}`),

  // Benchmarks
  getBenchmarks: () =>
    get<{ benchmarks: BenchmarkResult[] }>("/api/benchmarks"),

  // Metrics
  getMetrics: () => get<Record<string, number>>("/api/metrics"),
};
