import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { PipelineConfig } from "@/mappers/systemHealthMapper";
import { savePipeline } from "@/api/healthApi";

const modeOptions = ["live", "batch", "replay"];
const featurePipelineOptions = ["HTTPS", "ISCX_V2"];

interface Props {
  config: PipelineConfig;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PipelineConfigPanel({ config, open, onOpenChange }: Props) {
  const [localConfig, setLocalConfig] = useState<PipelineConfig>(config);
  const previousOpenRef = useRef(false);
  const [saving, setSaving] = useState(false);


  useEffect(() => {
    const justOpened = open && !previousOpenRef.current;

    if (justOpened) {
      setLocalConfig(config);
    }

    previousOpenRef.current = open;
  }, [open, config]);

  const update = <K extends keyof PipelineConfig>(
      key: K,
      value: PipelineConfig[K]
  ) => {
    setLocalConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await savePipeline(localConfig);
      toast.success("Configuration saved", {
        description: "Pipeline config updated. Restart to apply.",
      });
      onOpenChange(false);
    } catch {
      toast.error("Failed to save configurations");
    } finally {
      setSaving(false);
    }
  };

  // const handleCancel = () => {
  //   setLocalConfig(config);
  //   onOpenChange(false);
  // };

  return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto bg-card border-border">
          <SheetHeader>
            <SheetTitle className="text-foreground">Pipeline Configuration</SheetTitle>
            <SheetDescription>
              Edit runtime settings. Save and restart to apply changes.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-6 py-6">
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Directory Paths
              </h3>
              {(["ready_dir", "processing_dir", "processed_dir", "streams_dir"] as const).map((key) => (
                  <div key={key} className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{key}</Label>
                    <Input
                        value={localConfig[key]}
                        onChange={(e) => update(key, e.target.value)}
                        className="h-9 text-sm font-mono bg-secondary/50 border-border"
                    />
                  </div>
              ))}
            </div>

            <Separator className="bg-border" />

            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Numeric Settings
              </h3>
              {([
                ["max_packets", "Max Packets"],
                ["max_duration_sec", "Max Duration (sec)"],
                ["idle_timeout_sec", "Idle Timeout (sec)"],
                ["poll_interval_sec", "Poll Interval (sec)"],
                ["system_delay", "System Delay (sec)"],
              ] as const).map(([key, label]) => (
                  <div key={key} className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">{label}</Label>
                    <Input
                        type="number"
                        value={localConfig[key]}
                        onChange={(e) => update(key, Number(e.target.value))}
                        className="h-9 text-sm font-mono bg-secondary/50 border-border"
                    />
                  </div>
              ))}
            </div>

            <Separator className="bg-border" />

            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Toggles
              </h3>
              {([
                ["save_processed_batch_file", "Save Batch Files"],
                ["save_stream_files", "Save Stream Files"],
                ["auto_start", "Auto Start"],
                ["enable_stats", "Enable Stats"],
              ] as const).map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between">
                    <Label className="text-sm text-foreground">{label}</Label>
                    <Switch
                        checked={localConfig[key]}
                        onCheckedChange={(v) => update(key, v)}
                    />
                  </div>
              ))}
            </div>

            <Separator className="bg-border" />

            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Pipeline Options
              </h3>

              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Mode</Label>
                <Select
                    value={localConfig.mode}
                    onValueChange={(v) => update("mode", v)}
                >
                  <SelectTrigger className="h-9 bg-secondary/50 border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {modeOptions.map((o) => (
                        <SelectItem key={o} value={o}>
                          {o}
                        </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Feature Pipeline</Label>
                <Select
                    value={localConfig.feature_pipeline}
                    onValueChange={(v) => update("feature_pipeline", v)}
                >
                  <SelectTrigger className="h-9 bg-secondary/50 border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {featurePipelineOptions.map((o) => (
                        <SelectItem key={o} value={o}>
                          {o}
                        </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <SheetFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving} className="min-w-[160px]">
            <span className="inline-flex w-4 items-center justify-center" aria-hidden="true">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <span className="h-4 w-4" />}
            </span>
              <span>Save Configuration</span>
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
  );
}