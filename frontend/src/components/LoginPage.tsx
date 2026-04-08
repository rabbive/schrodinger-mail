import { useState } from "react";
import { Shield } from "lucide-react";
import { useStore } from "@/hooks/useStore";
import { api, setAccessToken } from "@/services/api";

export default function LoginPage({ onSuccess }: { onSuccess: () => void }) {
  const { init } = useStore();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!username.trim()) {
      setError("Please enter a username.");
      return;
    }

    if (mode === "register" && password !== password2) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const data = mode === "register"
        ? await api.register(username.trim().toLowerCase(), password)
        : await api.login(username.trim().toLowerCase(), password);

      if (!data.ok) throw new Error("Authentication failed");

      if (data.access_token) {
        setAccessToken(data.access_token);
        localStorage.setItem("qec-access-token", data.access_token);
        useStore.setState({ accessToken: data.access_token });
      }
      if (data.refresh_token) {
        localStorage.setItem("qec-refresh-token", data.refresh_token);
        useStore.setState({ refreshToken: data.refresh_token });
      }

      await init();
      onSuccess();
    } catch (err: unknown) {
      setError((err as Error).message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <span className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground">
            <Shield className="w-4 h-4" />
          </span>
          <span className="font-semibold text-lg tracking-tight">Schrödinger Mail</span>
        </div>

        {/* Card */}
        <div className="border rounded-xl bg-card shadow-sm p-6">
          {/* Tab toggle */}
          <div className="flex gap-1 bg-muted rounded-lg p-1 mb-5">
            <button
              type="button"
              onClick={() => { setMode("login"); setError(""); }}
              className={`flex-1 py-1.5 px-3 rounded-md text-sm font-medium transition-colors ${
                mode === "login"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => { setMode("register"); setError(""); }}
              className={`flex-1 py-1.5 px-3 rounded-md text-sm font-medium transition-colors ${
                mode === "register"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="your username"
                autoComplete="username"
                required
                className="w-full px-3 py-2 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••"
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                className="w-full px-3 py-2 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
              />
            </div>

            {mode === "register" && (
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Confirm password
                </label>
                <input
                  type="password"
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                  placeholder="••••••"
                  autoComplete="new-password"
                  className="w-full px-3 py-2 text-sm rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                />
              </div>
            )}

            {error && (
              <p className="text-xs text-destructive">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:opacity-50 transition-colors mt-1"
            >
              {loading
                ? mode === "register" ? "Creating account…" : "Signing in…"
                : mode === "register" ? "Create Account" : "Sign In"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-4">
          Kyber768 · Dilithium3 · AES-256-GCM
        </p>
      </div>
    </div>
  );
}
