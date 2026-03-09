import { useStore } from "@/hooks/useStore";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Sun, Moon, Shield } from "lucide-react";

export default function Header() {
  const { appState, activeUser, setActiveUser, toggleTheme, theme } = useStore();
  const users = appState ? Object.keys(appState.users) : [];

  return (
    <header className="col-span-full flex items-center gap-3 px-4 h-[48px] border-b bg-card">
      <div className="flex items-center gap-2.5">
        <span className="w-6 h-6 rounded-md bg-primary flex items-center justify-center text-primary-foreground">
          <Shield className="w-3.5 h-3.5" />
        </span>
        <span className="font-semibold text-sm text-foreground tracking-tight">
          Schrödinger Mail
        </span>
      </div>

      <Separator orientation="vertical" className="h-4 mx-1" />

      <div className="flex items-center gap-1.5">
        {appState && (
          <>
            <Badge variant="outline">{appState.kem_algorithm}</Badge>
            <Badge variant="outline">{appState.sig_algorithm}</Badge>
            <Badge variant="outline">AES-256-GCM</Badge>
          </>
        )}
      </div>

      <div className="flex-1" />

      <Button
        variant="outline"
        size="icon"
        onClick={toggleTheme}
        className="w-7 h-7"
      >
        {theme === "dark" ? (
          <Sun className="h-3.5 w-3.5" />
        ) : (
          <Moon className="h-3.5 w-3.5" />
        )}
        <span className="sr-only">Toggle theme</span>
      </Button>

      <Separator orientation="vertical" className="h-4 mx-0.5" />

      <div className="flex items-center gap-1">
        {users.map((name) => (
          <Button
            key={name}
            variant={name === activeUser ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveUser(name)}
            className={cn(
              name === activeUser && "bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25",
            )}
          >
            {name.charAt(0).toUpperCase() + name.slice(1)}
          </Button>
        ))}
      </div>
    </header>
  );
}
