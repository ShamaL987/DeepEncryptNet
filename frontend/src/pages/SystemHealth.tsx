import { useCallback, useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadges";
import {
  Activity,
  Cpu,
  Clock,
  AlertTriangle,
  Server,
  Database,
  Play,
  Square,
  RotateCcw,
  Settings,
  Loader2,
  ShieldOff,
  KeyRound,
  Check,
  Copy,
} from "lucide-react";
import { useSimulatedLoading } from "@/hooks/use-simulated-loading";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PipelineConfigPanel } from "@/components/PipelineConfigPanel";
import { toast } from "sonner";
import {
  fetchOverview,
  restartPipeline,
  startPipeline,
  stopPipeline,
} from "@/api/healthApi.ts";
import { usePolling } from "@/hooks/usePolling.ts";
import { mapOverviewToViewModel } from "@/mappers/systemHealthMapper.ts";
import { generateApiToken, revokeApiToken } from "@/api/login.ts";
import { Textarea } from "@/components/ui/textarea.tsx";

function MetricCard({
                      label,
                      value,
                      unit,
                      icon: Icon,
                    }: {
  label: string;
  value: string | number;
  unit?: string;
  icon: React.ElementType;
}) {
  return (
      <div className="bg-secondary/50 rounded-md p-4 border border-border">
        <div className="flex items-center gap-2 mb-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
            {label}
          </p>
        </div>
        <p className="text-xl font-bold font-mono text-foreground">
          {value}
          {unit && <span className="text-sm text-muted-foreground ml-1">{unit}</span>}
        </p>
      </div>
  );
}

export default function SystemHealth() {
  const isLoading = useSimulatedLoading(1000);
  const [configOpen, setConfigOpen] = useState(false);
  const [startFrom] = useState("raw-packets");
  const [startingUp, setStartingUp] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [pipelineRunningOverride, setPipelineRunningOverride] = useState<boolean | null>(null);

  const [tokenOverride, setTokenOverride] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [generatingToken, setGeneratingToken] = useState(false);
  const [revokingToken, setRevokingToken] = useState(false);

  const fetchOverviewStable = useCallback(() => fetchOverview(), []);
  const { data, refetch } = usePolling(fetchOverviewStable, 5000);

  const viewModel = useMemo(() => {
    return data ? mapOverviewToViewModel(data) : null;
  }, [data]);

  const polledPipelineRunning = viewModel?.pipelineRunning ?? false;
  const pipelineRunning =
      pipelineRunningOverride !== null ? pipelineRunningOverride : polledPipelineRunning;
  const config = viewModel?.config;

  const polledToken = viewModel?.api_token ?? "";
  const displayedToken = tokenOverride !== null ? tokenOverride : polledToken;

  useEffect(() => {
    if (
        pipelineRunningOverride !== null &&
        pipelineRunningOverride === polledPipelineRunning
    ) {
      setPipelineRunningOverride(null);
    }
  }, [pipelineRunningOverride, polledPipelineRunning]);

  useEffect(() => {
    if (tokenOverride !== null && tokenOverride === polledToken) {
      setTokenOverride(null);
    }
  }, [tokenOverride, polledToken]);

  const pipelineStatus: { stage: string; status: "yes" | "no" }[] = [
    {
      stage: "Feature Extraction",
      status: viewModel?.config?.enable_stats ? "yes" : "no",
    },
    {
      stage: "Temperature Scaling",
      status: viewModel?.pipelineConfig?.useTemperatureForRouting ? "yes" : "no",
    },
    {
      stage: "Predictions",
      status: "yes",
    },
  ];

  const handleStart = async () => {
    if (startingUp || stopping || restarting) return;

    setStartingUp(true);
    try {
      await startPipeline();
      setPipelineRunningOverride(true);
      toast.success("Pipeline started", {
        description: `Starting from: ${startFrom.replace(/-/g, " ")}`,
      });
    } catch {
      toast.error("Failed to start pipeline");
    } finally {
      setStartingUp(false);
    }
  };

  const handleStop = async () => {
    if (startingUp || stopping || restarting) return;

    setStopping(true);
    try {
      await stopPipeline();
      setPipelineRunningOverride(false);
      await refetch();
      toast.success("Pipeline stopped");
    } catch {
      toast.error("Failed to stop pipeline");
    } finally {
      setStopping(false);
    }
  };

  const handleRestart = async () => {
    if (startingUp || stopping || restarting) return;

    setRestarting(true);
    try {
      await restartPipeline();
      setPipelineRunningOverride(true);
      toast.success("Pipeline restarted", { description: "Configuration reloaded" });
    } catch {
      toast.error("Failed to restart pipeline");
    } finally {
      setRestarting(false);
    }
  };

  const handleGenerateToken = async () => {
    if (generatingToken || revokingToken) return;

    setGeneratingToken(true);
    try {
      const result = await generateApiToken();
      setTokenOverride(result.token);
      setCopied(false);
      await refetch();

      toast.success("Token generated", {
        description: result.replaced_existing
            ? "Existing API token was replaced"
            : "New API token is ready",
      });
    } catch (error) {
      const message =
          error instanceof Error ? error.message : "Failed to generate token";
      toast.error(message);
    } finally {
      setGeneratingToken(false);
    }
  };

  const handleRevokeToken = async () => {
    if (!displayedToken || generatingToken || revokingToken) return;

    setRevokingToken(true);
    try {
      const result = await revokeApiToken();

      if (result.revoked) {
        setTokenOverride("");
        setCopied(false);
        await refetch();
        toast.success("Token revoked");
      } else {
        toast.info(result.message || "No API token exists for this user");
      }
    } catch (error) {
      const message =
          error instanceof Error ? error.message : "Failed to revoke token";
      toast.error(message);
    } finally {
      setRevokingToken(false);
    }
  };

  const handleCopyToken = async () => {
    if (!displayedToken) return;

    try {
      await navigator.clipboard.writeText(displayedToken);
      setCopied(true);
      toast.success("Token copied to clipboard");
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy token");
    }
  };

  const anyActionLoading = startingUp || stopping || restarting;

  return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-xl font-bold text-foreground">System & Model Health</h1>
            <p className="text-xs text-muted-foreground">
              Pipeline performance and model deployment readiness
            </p>
          </div>

          {isLoading ? (
              <div className="space-y-6">
                <div className="flex items-center gap-2 flex-wrap">
                  {Array.from({ length: 3 }).map((_, index) => (
                      <div
                          key={index}
                          className="flex items-center gap-2 bg-secondary px-3 py-1.5 rounded-md"
                      >
                        <Skeleton className="h-3 w-24" />
                        <Skeleton className="h-5 w-10 rounded-full" />
                      </div>
                  ))}
                </div>

                <Card className="bg-card border border-primary/30 shadow-[0_0_15px_-3px_hsl(210,100%,56%,0.15)]">
                  <CardContent className="p-5">
                    <div className="flex flex-col items-center justify-center gap-4">
                      <div className="flex items-center gap-2">
                        <Skeleton className="h-2 w-2 rounded-full" />
                        <Skeleton className="h-3 w-28" />
                        <Skeleton className="h-5 w-16 rounded-md" />
                      </div>

                      <div className="flex flex-wrap items-center justify-center gap-2.5 w-full">
                        <Skeleton className="h-10 w-[90px] rounded-md" />
                        <Skeleton className="h-10 w-[82px] rounded-md" />
                        <Skeleton className="h-10 w-[100px] rounded-md" />
                        <Skeleton className="h-10 w-[170px] rounded-md" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card border-border">
                  <CardHeader className="pb-2 pt-4 px-4">
                    <Skeleton className="h-4 w-32" />
                  </CardHeader>
                  <CardContent className="px-4 pb-4 space-y-3">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                      {Array.from({ length: 6 }).map((_, index) => (
                          <div
                              key={index}
                              className="bg-secondary/50 rounded-md p-4 border border-border space-y-3"
                          >
                            <div className="flex items-center gap-2">
                              <Skeleton className="h-4 w-4 rounded-sm" />
                              <Skeleton className="h-3 w-16" />
                            </div>
                            <Skeleton className="h-6 w-20" />
                          </div>
                      ))}
                    </div>

                    <div className="grid grid-cols-2 gap-3 mt-3">
                      {Array.from({ length: 2 }).map((_, index) => (
                          <div
                              key={index}
                              className="bg-secondary/50 rounded-md p-4 border border-border space-y-3"
                          >
                            <div className="flex items-center gap-2">
                              <Skeleton className="h-4 w-4 rounded-sm" />
                              <Skeleton className="h-3 w-16" />
                            </div>
                            <Skeleton className="h-6 w-20" />
                          </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card border-border">
                  <CardHeader className="pb-2 pt-4 px-4">
                    <Skeleton className="h-4 w-36" />
                  </CardHeader>
                  <CardContent className="px-4 pb-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Array.from({ length: 4 }).map((_, index) => (
                          <div key={index} className="space-y-2">
                            <Skeleton className="h-3 w-20" />
                            <Skeleton className="h-5 w-24" />
                          </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
          ) : (
              <>
                <div className="flex items-center gap-2 flex-wrap">
                  {pipelineStatus.map((s, i) => (
                      <div key={s.stage} className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5 bg-secondary px-3 py-1.5 rounded-md">
                          <span className="text-xs text-foreground">{s.stage}</span>
                          <StatusBadge status={s.status} />
                        </div>
                        {i < pipelineStatus.length - 1 && (
                            <span className="text-muted-foreground text-xs">→</span>
                        )}
                      </div>
                  ))}
                </div>

                <Card className="bg-card border border-primary/30 shadow-[0_0_15px_-3px_hsl(210,100%,56%,0.15)]">
                  <CardContent className="p-5">
                    <div className="flex flex-col items-center justify-center gap-4 text-center">
                      <div className="flex flex-wrap items-center justify-center gap-2">
                        <div
                            className="h-2 w-2 rounded-full animate-pulse"
                            style={{
                              backgroundColor: pipelineRunning
                                  ? "hsl(142,70%,49%)"
                                  : "hsl(0,72%,51%)",
                            }}
                        />
                        <p className="text-xs font-semibold text-foreground uppercase tracking-wider">
                          Pipeline Controls
                        </p>
                        <span
                            className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                            style={{
                              backgroundColor: pipelineRunning
                                  ? "hsla(142,70%,49%,0.15)"
                                  : "hsla(0,72%,51%,0.15)",
                              color: pipelineRunning
                                  ? "hsl(142,70%,49%)"
                                  : "hsl(0,72%,51%)",
                            }}
                        >
                      {pipelineRunning ? "RUNNING" : "STOPPED"}
                    </span>
                      </div>

                      <div className="flex flex-wrap items-center justify-center gap-2.5">
                        <Button
                            onClick={handleStart}
                            disabled={pipelineRunning || anyActionLoading}
                            className="gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white shadow-md min-w-[90px]"
                        >
                          {startingUp ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                              <Play className="h-4 w-4" />
                          )}
                          Start
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleStop}
                            disabled={!pipelineRunning || anyActionLoading}
                            className="gap-1.5 shadow-md min-w-[82px]"
                        >
                          {stopping ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                              <Square className="h-4 w-4" />
                          )}
                          Stop
                        </Button>
                        <Button
                            variant="secondary"
                            onClick={handleRestart}
                            disabled={anyActionLoading}
                            className="gap-1.5 shadow-md min-w-[100px]"
                        >
                          {restarting ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                              <RotateCcw className="h-4 w-4" />
                          )}
                          Restart
                        </Button>
                        <Button
                            variant="outline"
                            onClick={() => setConfigOpen(true)}
                            disabled={anyActionLoading}
                            className="gap-1.5 border-primary/40 text-primary hover:bg-primary/10"
                        >
                          <Settings className="h-4 w-4" /> Change Configuration
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <div className="flex justify-center">
                  <Card className="bg-card border-border w-full max-w-4xl">
                    <CardHeader className="pb-2 pt-4 px-4">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <KeyRound className="h-4 w-4 text-chart-blue" />
                        API Token Management
                      </CardTitle>
                    </CardHeader>

                    <CardContent className="px-4 pb-4">
                      <div className="flex items-start gap-2 flex-col xl:flex-row">
                        <div className="flex-1 relative w-full min-w-0">
                          <Textarea
                              readOnly
                              value={displayedToken}
                              placeholder="No token generated"
                              className="font-mono text-[11px] leading-tight resize-none h-10 min-h-10 w-full bg-secondary/50 border-border pr-12 whitespace-nowrap overflow-x-auto"
                          />

                          {displayedToken && (
                              <Button
                                  variant="ghost"
                                  size="icon"
                                  className="absolute right-1 top-1 h-8 w-8 text-muted-foreground hover:text-foreground"
                                  onClick={handleCopyToken}
                              >
                                {copied ? (
                                    <Check className="h-3.5 w-3.5" />
                                ) : (
                                    <Copy className="h-3.5 w-3.5" />
                                )}
                              </Button>
                          )}
                        </div>

                        <Button
                            onClick={handleGenerateToken}
                            disabled={generatingToken || revokingToken}
                            className="h-10 px-3 gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white shadow-md min-w-[105px]"
                        >
                          {generatingToken ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                              <KeyRound className="h-4 w-4" />
                          )}
                          Generate
                        </Button>

                        <Button
                            variant="destructive"
                            onClick={handleRevokeToken}
                            disabled={!displayedToken || generatingToken || revokingToken}
                            className="h-10 px-3 gap-1.5 shadow-md min-w-[100px]"
                        >
                          {revokingToken ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                              <ShieldOff className="h-4 w-4" />
                          )}
                          Revoke
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card className="bg-card border-border">
                  <CardHeader className="pb-2 pt-4 px-4">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Activity className="h-4 w-4 text-chart-blue" /> Pipeline Health
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-4 pb-4">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                      <MetricCard
                          label="Uptime"
                          value={viewModel?.healthCards.prediction_uptime_sec ?? 0}
                          unit="ms"
                          icon={Cpu}
                      />
                      <MetricCard
                          label="Flows/sec"
                          value={viewModel?.healthCards.flowsPerSec ?? 0}
                          icon={Database}
                      />
                      <MetricCard
                          label="Predictions/sec"
                          value={viewModel?.healthCards.predictionsPerSec ?? 0}
                          icon={Server}
                      />
                      <MetricCard
                          label="Inference Latency (avg)"
                          value={viewModel?.healthCards.inferenceLatencyAvg ?? 0}
                          unit="ms"
                          icon={Clock}
                      />
                      <MetricCard
                          label="Inference Latency (p95)"
                          value={viewModel?.healthCards.inferenceLatencyP95 ?? 0}
                          unit="/ms"
                          icon={Clock}
                      />
                      <MetricCard
                          label="Routed (%)"
                          value={viewModel?.healthCards.routed_percent ?? 0}
                          unit="/s"
                          icon={Cpu}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3 mt-3">
                      <MetricCard label="Errors (1h)" value={0} icon={AlertTriangle} />
                      <MetricCard label="Errors (24h)" value={0} icon={AlertTriangle} />
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card border-border">
                  <CardHeader className="pb-2 pt-4 px-4">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-chart-green" /> Model Configuration
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-4 pb-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        ["Model Version", viewModel?.pipelineConfig?.pipelineName],
                        ["Model Name", viewModel?.pipelineConfig?.pipelineVersion],
                        [
                          "Pipeline Accuracy (Overall)",
                          viewModel?.pipelineConfig?.acceptedAccuracy,
                        ],
                        ["Coverage", viewModel?.pipelineConfig?.coverage],
                      ].map(([k, v]) => (
                          <div key={k as string}>
                            <p className="text-[10px] text-muted-foreground uppercase">{k}</p>
                            <p className="text-sm font-mono font-semibold text-foreground mt-1">
                              {v}
                            </p>
                          </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
          )}
        </div>

        {config && (
            <PipelineConfigPanel
                config={config}
                open={configOpen}
                onOpenChange={setConfigOpen}
            />
        )}
      </DashboardLayout>
  );
}