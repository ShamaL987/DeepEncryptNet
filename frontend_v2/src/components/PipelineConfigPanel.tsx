import { useState } from "react";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";

export interface PipelineConfig {
  ready_dir: string;
  processing_dir: string;
  processed_dir: string;
  streams_dir: string;
  max_packets: number;
  max_duration_sec: number;
  idle_timeout_sec: number;
  poll_interval_sec: number;
  auto_start: boolean;
  enable_stats: boolean;
  mode: string;
  feature_pipeline: string;
}

const defaultConfig: PipelineConfig = {
  ready_dir: "/data/ready",
  processing_dir: "/data/processing",
  processed_dir: "/data/processed",
  streams_dir: "/data/streams",
  max_packets: 10000,
  max_duration_sec: 120,
  idle_timeout_sec: 30,
  poll_interval_sec: 5,
  auto_start: true,
  enable_stats: true,
  mode: "live",
  feature_pipeline: "default",
};

const modeOptions = ["live", "batch", "replay"];
const featurePipelineOptions = ["default", "extended", "minimal", "custom"];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PipelineConfigPanel({ open, onOpenChange }: Props) {
  const [config, setConfig] = useState<PipelineConfig>(defaultConfig);

  const update = <K extends keyof PipelineConfig>(key: K, value: PipelineConfig[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    toast.success("Configuration saved", { description: "Pipeline config updated. Restart to apply." });
    onOpenChange(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto bg-card border-border">
        <SheetHeader>
          <SheetTitle className="text-foreground">Pipeline Configuration</SheetTitle>
          <SheetDescription>Edit runtime settings. Save and restart to apply changes.</SheetDescription>
        </SheetHeader>

        <div className="space-y-6 py-6">
          {/* Directory paths */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Directory Paths</h3>
            {(["ready_dir", "processing_dir", "processed_dir", "streams_dir"] as const).map(key => (
              <div key={key} className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">{key}</Label>
                <Input
                  value={config[key]}
                  onChange={e => update(key, e.target.value)}
                  className="h-9 text-sm font-mono bg-secondary/50 border-border"
                />
              </div>
            ))}
          </div>

          <Separator className="bg-border" />

          {/* Numeric fields */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Numeric Settings</h3>
            {([
              ["max_packets", "Max Packets"],
              ["max_duration_sec", "Max Duration (sec)"],
              ["idle_timeout_sec", "Idle Timeout (sec)"],
              ["poll_interval_sec", "Poll Interval (sec)"],
            ] as const).map(([key, label]) => (
              <div key={key} className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">{label}</Label>
                <Input
                  type="number"
                  value={config[key]}
                  onChange={e => update(key, Number(e.target.value))}
                  className="h-9 text-sm font-mono bg-secondary/50 border-border"
                />
              </div>
            ))}
          </div>

          <Separator className="bg-border" />

          {/* Toggles */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Toggles</h3>
            {([
              ["auto_start", "Auto Start"],
              ["enable_stats", "Enable Stats"],
            ] as const).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between">
                <Label className="text-sm text-foreground">{label}</Label>
                <Switch
                  checked={config[key]}
                  onCheckedChange={v => update(key, v)}
                />
              </div>
            ))}
          </div>

          <Separator className="bg-border" />

          {/* Dropdowns */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Pipeline Options</h3>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Mode</Label>
              <Select value={config.mode} onValueChange={v => update("mode", v)}>
                <SelectTrigger className="h-9 bg-secondary/50 border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {modeOptions.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Feature Pipeline</Label>
              <Select value={config.feature_pipeline} onValueChange={v => update("feature_pipeline", v)}>
                <SelectTrigger className="h-9 bg-secondary/50 border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {featurePipelineOptions.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSave}>Save Configuration</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
