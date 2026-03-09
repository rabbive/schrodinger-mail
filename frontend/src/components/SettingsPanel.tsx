import { useEffect, useState } from "react";
import { useStore } from "@/hooks/useStore";
import { api } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Settings,
  User,
  Save,
  PenLine,
  FileText,
  Download,
  FlaskConical,
  CheckCircle2,
} from "lucide-react";

export default function SettingsPanel() {
  const { activeUser } = useStore();
  const [password, setPassword] = useState("");
  const [signature, setSignature] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings(activeUser).then((d) => {
      const s = d.settings as Record<string, unknown>;
      setSignature(String(s.signature ?? ""));
    }).catch(console.error);
  }, [activeUser]);

  const savePassword = async () => {
    if (password.length < 4) return;
    await api.setPassword(activeUser, password);
    setPassword("");
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const saveSignature = async () => {
    await api.saveSettings(activeUser, { signature });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-lg space-y-6">
      <div className="flex items-center gap-2">
        <Settings className="w-4 h-4 text-primary" />
        <h2 className="text-base font-bold">Settings</h2>
      </div>

      {saved && (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="w-3 h-3" /> Saved successfully.
        </Badge>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5">
            <User className="w-3.5 h-3.5" /> Account
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Username</span>
            <span className="font-semibold capitalize">{activeUser}</span>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New password"
            />
            <Button size="sm" onClick={savePassword}>
              <Save className="w-3.5 h-3.5" /> Save
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5">
            <PenLine className="w-3.5 h-3.5" /> Email Signature
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Textarea
            value={signature}
            onChange={(e) => setSignature(e.target.value)}
            placeholder="Your email signature..."
            rows={3}
            className="resize-y"
          />
          <Button size="sm" onClick={saveSignature}>
            <Save className="w-3.5 h-3.5" /> Save Signature
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" /> Security Report
          </CardTitle>
          <CardDescription>
            Download a comprehensive HTML report of your security configuration.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button size="sm" asChild>
            <a href={`/api/report/${activeUser}`}>
              <Download className="w-3.5 h-3.5" /> Download Report
            </a>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5">
            <FlaskConical className="w-3.5 h-3.5" /> Demo Evidence Report
          </CardTitle>
          <CardDescription>
            Export a comprehensive evidence bundle with algorithm details, attack outcomes, benchmarks,
            key fingerprints, and a full audit trail. Includes machine-readable JSON.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button size="sm" className="bg-quantum-green text-white hover:bg-quantum-green/90" asChild>
            <a href={api.getDemoReportUrl(activeUser)}>
              <Download className="w-3.5 h-3.5" /> Export Demo Evidence
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
