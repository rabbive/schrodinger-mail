import { create } from "zustand";
import type { AppState, CryptoStep, Email, Folder } from "@/types";
import { api, setAccessToken } from "@/services/api";

interface Store {
  // State
  appState: AppState | null;
  activeUser: string;
  activeFolder: string;
  emails: Email[];
  folders: Folder[];
  selectedEmailId: number | null;
  activeTab: string;
  cryptoLog: CryptoStep[];
  loading: boolean;
  passwordRequired: boolean;
  theme: "dark" | "light";
  accessToken: string | null;
  refreshToken: string | null;

  // Actions
  init: () => Promise<void>;
  setActiveUser: (user: string) => void;
  setActiveFolder: (folder: string) => void;
  setSelectedEmailId: (id: number | null) => void;
  setActiveTab: (tab: string) => void;
  loadFolders: () => Promise<void>;
  loadEmails: (folder?: string) => Promise<void>;
  sendEmail: (data: {
    recipient: string;
    recipients?: string[];
    subject: string;
    body: string;
    securityLevel: number;
    encryptSubject: boolean;
    password?: string;
    threadId?: string;
    inReplyTo?: string;
  }) => Promise<CryptoStep[]>;
  receiveEmails: (password?: string) => Promise<void>;
  addCryptoSteps: (steps: CryptoStep[]) => void;
  clearCryptoLog: () => void;
  toggleTheme: () => void;
  login: (username: string, password?: string) => Promise<void>;
  logout: () => Promise<void>;
  setLoading: (v: boolean) => void;
}

export const useStore = create<Store>((set, get) => ({
  appState: null,
  activeUser: "alice",
  activeFolder: "inbox",
  emails: [],
  folders: [],
  selectedEmailId: null,
  activeTab: "demo-guide",
  cryptoLog: [],
  loading: false,
  passwordRequired: false,
  theme: (localStorage.getItem("qec-theme") as "dark" | "light") || "dark",
  accessToken: localStorage.getItem("qec-access-token"),
  refreshToken: localStorage.getItem("qec-refresh-token"),

  init: async () => {
    const token = get().accessToken;
    if (token) setAccessToken(token);
    const state = await api.getState();
    const activeUser =
      (state.local_username as string) ||
      Object.keys(state.users)[0] ||
      "";
    set({ appState: state, activeUser });
    await get().loadFolders();
    await get().loadEmails();
  },

  setSelectedEmailId: (id) => set({ selectedEmailId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),

  setActiveUser: (user) => {
    set({
      activeUser: user,
      activeFolder: "inbox",
      emails: [],
      selectedEmailId: null,
      passwordRequired: false,
    });
    get().receiveEmails();
  },

  setActiveFolder: async (folder) => {
    set({ activeFolder: folder });
    await get().loadEmails(folder);
  },

  loadFolders: async () => {
    const { activeUser } = get();
    const data = await api.getFolders(activeUser);
    set({ folders: data.folders });
  },

  loadEmails: async (folder?: string) => {
    const { activeUser, activeFolder } = get();
    const f = folder ?? activeFolder;
    const data = await api.getEmails(activeUser, f);
    set({ emails: data.emails, activeFolder: f });
  },

  sendEmail: async (data) => {
    const { activeUser } = get();
    set({ cryptoLog: [] });
    const result = await api.send({
      sender: activeUser,
      recipient: data.recipient,
      recipients: data.recipients,
      subject: data.subject,
      body: data.body,
      encrypt_subject: data.encryptSubject,
      security_level: data.securityLevel,
      password: data.password,
      thread_id: data.threadId,
      in_reply_to: data.inReplyTo,
    });
    get().addCryptoSteps(result.steps);
    await get().loadFolders();
    return result.steps;
  },

  receiveEmails: async (password) => {
    const { activeUser, loading } = get();
    if (loading) return;
    set({ loading: true });
    try {
      const result = await api.receive(activeUser, password);
      if (get().activeUser !== activeUser) return;
      set({ passwordRequired: result.password_required });
      if (result.steps && result.steps.length > 0) {
        set({ cryptoLog: [] });
        get().addCryptoSteps(result.steps);
      }
      await get().loadFolders();
      await get().loadEmails();
    } finally {
      set({ loading: false });
    }
  },

  addCryptoSteps: (steps) => set((s) => ({ cryptoLog: [...steps, ...s.cryptoLog] })),
  clearCryptoLog: () => set({ cryptoLog: [] }),

  toggleTheme: () => {
    const next = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("qec-theme", next);
    set({ theme: next });
  },

  login: async (username, password) => {
    const result = await api.login(username, password);
    setAccessToken(result.access_token);
    localStorage.setItem("qec-access-token", result.access_token);
    localStorage.setItem("qec-refresh-token", result.refresh_token);
    set({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
      activeUser: username,
    });
    await get().init();
  },

  logout: async () => {
    await api.logout();
    setAccessToken(null);
    localStorage.removeItem("qec-access-token");
    localStorage.removeItem("qec-refresh-token");
    set({ accessToken: null, refreshToken: null });
  },

  setLoading: (v) => set({ loading: v }),
}));
