import { useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadges";
import { systemHealth, confidenceTrend, routedPctTrend, pipelineStatus } from "@/data/mockData";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from "recharts";
import { Activity, Cpu, Clock, AlertTriangle, Server, Database, Play, Square, RotateCcw, Settings } from "lucide-react";
import { useSimulatedLoading } from "@/hooks/use-simulated-loading";
import { PipelineSkeleton, MetricSkeleton, ChartSkeleton } from "@/components/Skeletons";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { PipelineConfigPanel } from "@/components/PipelineConfigPanel";
import { toast } from "sonner";

function MetricCard({ label, value, unit, icon: Icon }: { label: string; value: string | number; unit?: string; icon: React.ElementType }) {
  return (
    <div className="bg-secondary/50 rounded-md p-4 border border-border">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
      </div>
      <p className="text-xl font-bold font-mono text-foreground">
        {value}{unit && <span className="text-sm text-muted-foreground ml-1">{unit}</span>}
      </p>
    </div>
  );
}

export default function SystemHealth() {
  const isLoading = useSimulatedLoading(1000);
  const [configOpen, setConfigOpen] = useState(false);
  const [pipelineRunning, setPipelineRunning] = useState(true);
  const [startFrom, setStartFrom] = useState("raw-packets");

  const handleStart = () => {
    setPipelineRunning(true);
    toast.success("Pipeline started", { description: `Starting from: ${startFrom.replace(/-/g, " ")}` });
  };
  const handleStop = () => {
    setPipelineRunning(false);
    toast.info("Pipeline stopped");
  };
  const handleRestart = () => {
    setPipelineRunning(true);
    toast.success("Pipeline restarted", { description: "Configuration reloaded" });
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold text-foreground">System & Model Health</h1>
          <p className="text-xs text-muted-foreground">Pipeline performance and model deployment readiness</p>
        </div>

        {isLoading ? (
          <div className="space-y-6">
            <PipelineSkeleton />
            <Skeleton className="h-10 w-full rounded-md" />
            <Card className="bg-card border-border">
              <CardHeader className="pb-2 pt-4 px-4"><Skeleton className="h-4 w-28" /></CardHeader>
              <CardContent className="px-4 pb-4 space-y-3">
                <MetricSkeleton count={6} />
                <MetricSkeleton count={2} />
              </CardContent>
            </Card>
            <Card className="bg-card border-border">
              <CardHeader className="pb-2 pt-4 px-4"><Skeleton className="h-4 w-36" /></CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="space-y-1">
                      <Skeleton className="h-2.5 w-16" />
                      <Skeleton className="h-5 w-20" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ChartSkeleton height={220} />
              <ChartSkeleton height={220} />
            </div>
          </div>
        ) : (
          <>
            {/* Pipeline Status */}
            <div className="flex items-center gap-2 flex-wrap">
              {pipelineStatus.map((s, i) => (
                <div key={s.stage} className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 bg-secondary px-3 py-1.5 rounded-md">
                    <span className="text-xs text-foreground">{s.stage}</span>
                    <StatusBadge status={s.status} />
                  </div>
                  {i < pipelineStatus.length - 1 && <span className="text-muted-foreground text-xs">→</span>}
                </div>
              ))}
            </div>

            {/* Pipeline Actions & Start-From */}
            <Card className="bg-card border border-primary/30 shadow-[0_0_15px_-3px_hsl(210,100%,56%,0.15)]">
              <CardContent className="p-5">
                <div className="flex flex-col md:flex-row md:items-end gap-5">
                  {/* Action Buttons */}
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full animate-pulse" style={{ backgroundColor: pipelineRunning ? 'hsl(142,70%,49%)' : 'hsl(0,72%,51%)' }} />
                      <p className="text-xs font-semibold text-foreground uppercase tracking-wider">Pipeline Controls</p>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-mono" style={{ backgroundColor: pipelineRunning ? 'hsla(142,70%,49%,0.15)' : 'hsla(0,72%,51%,0.15)', color: pipelineRunning ? 'hsl(142,70%,49%)' : 'hsl(0,72%,51%)' }}>
                        {pipelineRunning ? "RUNNING" : "STOPPED"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <Button
                        onClick={handleStart}
                        disabled={pipelineRunning}
                        className="gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white shadow-md"
                      >
                        <Play className="h-4 w-4" /> Start
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={handleStop}
                        disabled={!pipelineRunning}
                        className="gap-1.5 shadow-md"
                      >
                        <Square className="h-4 w-4" /> Stop
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={handleRestart}
                        className="gap-1.5 shadow-md"
                      >
                        <RotateCcw className="h-4 w-4" /> Restart
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setConfigOpen(true)}
                        className="gap-1.5 border-primary/40 text-primary hover:bg-primary/10"
                      >
                        <Settings className="h-4 w-4" /> Change Configuration
                      </Button>
                    </div>
                  </div>

                  {/* Start From */}
                  <div className="space-y-1.5 md:ml-auto">
                    <Label className="text-[10px] text-muted-foreground uppercase tracking-wider">Pipeline Start From</Label>
                    <Select value={startFrom} onValueChange={setStartFrom}>
                      <SelectTrigger className="w-[220px] h-9 bg-secondary/50 border-border">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="raw-packets">Raw Packets</SelectItem>
                        <SelectItem value="pre-calculated-statistics">Pre-calculated Statistics</SelectItem>
                        <SelectItem value="predictions">Predictions</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Pipeline Health Metrics */}
            <Card className="bg-card border-border">
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Activity className="h-4 w-4 text-chart-blue" /> Pipeline Health
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  <MetricCard label="Packets/sec" value={systemHealth.captureRate.toLocaleString()} icon={Server} />
                  <MetricCard label="Flows/sec" value={systemHealth.flowCreationRate} icon={Database} />
                  <MetricCard label="Feature Latency (avg)" value={systemHealth.featureExtractorLatency.avg} unit="ms" icon={Clock} />
                  <MetricCard label="Feature Latency (p95)" value={systemHealth.featureExtractorLatency.p95} unit="ms" icon={Clock} />
                  <MetricCard label="Inference Latency (avg)" value={systemHealth.inferenceLatency.avg} unit="ms" icon={Cpu} />
                  <MetricCard label="Inference Latency (p95)" value={systemHealth.inferenceLatency.p95} unit="ms" icon={Cpu} />
                </div>
                <div className="grid grid-cols-2 gap-3 mt-3">
                  <MetricCard label="Errors (1h)" value={systemHealth.errors1h} icon={AlertTriangle} />
                  <MetricCard label="Errors (24h)" value={systemHealth.errors24h} icon={AlertTriangle} />
                </div>
              </CardContent>
            </Card>

            {/* Model Configuration */}
            <Card className="bg-card border-border">
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-chart-green" /> Model Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    ["Model Version", systemHealth.modelVersion],
                    ["Dataset", systemHealth.dataset],
                    ["T_low", systemHealth.tLow.toString()],
                    ["T_high", systemHealth.tHigh.toString()],
                  ].map(([k, v]) => (
                    <div key={k as string}>
                      <p className="text-[10px] text-muted-foreground uppercase">{k}</p>
                      <p className="text-sm font-mono font-semibold text-foreground mt-1">{v}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-3">
                  <p className="text-[10px] text-muted-foreground uppercase">Calibration</p>
                  <p className="text-sm font-mono text-foreground mt-1">{systemHealth.calibration}</p>
                </div>
              </CardContent>
            </Card>

            {/* Stability Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="bg-card border-border">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-sm font-medium">Confidence Median Trend</CardTitle>
                </CardHeader>
                <CardContent className="px-2 pb-4">
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={confidenceTrend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                      <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                      <YAxis domain={[0.4, 1]} tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                      <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
                      <ReferenceLine y={systemHealth.tHigh} stroke="hsl(142,70%,49%)" strokeDasharray="5 5" label={{ value: "T_high", position: "left", fill: "hsl(142,70%,49%)", fontSize: 10 }} />
                      <ReferenceLine y={systemHealth.tLow} stroke="hsl(25,95%,53%)" strokeDasharray="5 5" label={{ value: "T_low", position: "left", fill: "hsl(25,95%,53%)", fontSize: 10 }} />
                      <Line type="monotone" dataKey="median" stroke="hsl(210,100%,56%)" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="bg-card border-border">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-sm font-medium">Routed % Trend</CardTitle>
                </CardHeader>
                <CardContent className="px-2 pb-4">
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={routedPctTrend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                      <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                      <YAxis domain={[0, 50]} tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                      <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
                      <ReferenceLine y={35} stroke="hsl(0,72%,51%)" strokeDasharray="5 5" label={{ value: "Alert threshold", position: "left", fill: "hsl(0,72%,51%)", fontSize: 10 }} />
                      <Line type="monotone" dataKey="pct" stroke="hsl(270,70%,60%)" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>

      <PipelineConfigPanel open={configOpen} onOpenChange={setConfigOpen} />
    </DashboardLayout>
  );
}
