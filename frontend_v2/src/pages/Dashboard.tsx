import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadges";
import {
  kpiData, pipelineStatus, flowsOverTime, classifiedVsRouted,
  trafficMix, confidenceDistribution, alerts
} from "@/data/mockData";
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { useNavigate } from "react-router-dom";
import {
  Clock, Waves, Zap, CheckCircle2, ArrowRightLeft,
  Inbox, AlertTriangle, RefreshCw
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { useState } from "react";
import { useSimulatedLoading } from "@/hooks/use-simulated-loading";
import { KpiSkeleton, ChartSkeleton, PipelineSkeleton } from "@/components/Skeletons";
import { Skeleton } from "@/components/ui/skeleton";

const CHART_COLORS = [
  "hsl(210,100%,56%)", "hsl(142,70%,49%)", "hsl(25,95%,53%)",
  "hsl(270,70%,60%)", "hsl(187,85%,53%)", "hsl(0,72%,51%)", "hsl(45,93%,58%)"
];

const timeWindows = ["5m", "15m", "1h", "24h"];

function KpiCard({ title, value, sub, icon: Icon }: { title: string; value: string | number; sub?: string; icon: React.ElementType }) {
  return (
    <Card className="bg-card border-border">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">{title}</p>
            <p className="text-2xl font-bold text-foreground mt-1">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
          </div>
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [selectedWindow, setSelectedWindow] = useState("1h");
  const isLoading = useSimulatedLoading(1200);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-foreground">Overview Dashboard</h1>
            <p className="text-xs text-muted-foreground">Encrypted traffic monitoring • Real-time pipeline status</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex bg-secondary rounded-md">
              {timeWindows.map(w => (
                <button
                  key={w}
                  onClick={() => setSelectedWindow(w)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    selectedWindow === w
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {w}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Auto-refresh</span>
              <Switch />
            </div>
          </div>
        </div>

        {isLoading ? (
          <>
            <PipelineSkeleton />
            <KpiSkeleton count={7} />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <ChartSkeleton />
                  <ChartSkeleton />
                  <ChartSkeleton />
                  <ChartSkeleton />
                </div>
              </div>
              <div>
                <Card className="bg-card border-border">
                  <CardHeader className="pb-2 pt-4 px-4">
                    <Skeleton className="h-4 w-24" />
                  </CardHeader>
                  <CardContent className="px-4 pb-4 space-y-3">
                    {[1, 2, 3].map(i => (
                      <Skeleton key={i} className="h-20 w-full rounded-md" />
                    ))}
                  </CardContent>
                </Card>
              </div>
            </div>
          </>
        ) : (
          <>
            {/* Pipeline Status */}
            <div className="flex items-center gap-2">
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

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
              <KpiCard title="Uptime" value={kpiData.uptime} icon={Clock} />
              <KpiCard title="Unique Flows" value={kpiData.uniqueFlows} icon={Waves} />
              <KpiCard title="Processed/min" value={kpiData.processedPerMin} icon={Zap} />
              <KpiCard title="Classified" value={kpiData.classifiedCount} sub={`${kpiData.classifiedPct}%`} icon={CheckCircle2} />
              <KpiCard title="Routed" value={kpiData.routedCount} sub={`${kpiData.routedPct}%`} icon={ArrowRightLeft} />
              <KpiCard title="Queue Size" value={kpiData.unknownQueueSize} icon={Inbox} />
              <KpiCard title="Low Conf. Rate" value={kpiData.lowConfidenceRate} sub={`${kpiData.lowConfidencePct}%`} icon={AlertTriangle} />
            </div>

            {/* Charts + Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="bg-card border-border">
                    <CardHeader className="pb-2 pt-4 px-4">
                      <CardTitle className="text-sm font-medium">Flows Over Time</CardTitle>
                    </CardHeader>
                    <CardContent className="px-2 pb-4">
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={flowsOverTime}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                          <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                          <YAxis tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                          <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
                          <Line type="monotone" dataKey="flows" stroke="hsl(210,100%,56%)" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader className="pb-2 pt-4 px-4">
                      <CardTitle className="text-sm font-medium">Classified vs Routed</CardTitle>
                    </CardHeader>
                    <CardContent className="px-2 pb-4">
                      <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={classifiedVsRouted}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                          <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                          <YAxis tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                          <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
                          <Area type="monotone" dataKey="classified" stackId="1" stroke="hsl(142,70%,49%)" fill="hsl(142,70%,49%)" fillOpacity={0.3} />
                          <Area type="monotone" dataKey="routed" stackId="1" stroke="hsl(270,70%,60%)" fill="hsl(270,70%,60%)" fillOpacity={0.3} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader className="pb-2 pt-4 px-4">
                      <CardTitle className="text-sm font-medium">Traffic Mix</CardTitle>
                    </CardHeader>
                    <CardContent className="flex justify-center pb-4">
                      <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                          <Pie data={trafficMix} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={2}>
                            {trafficMix.map((_, i) => (
                              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
                          <Legend wrapperStyle={{ fontSize: 10 }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader className="pb-2 pt-4 px-4">
                      <CardTitle className="text-sm font-medium">Confidence Distribution</CardTitle>
                    </CardHeader>
                    <CardContent className="px-2 pb-4">
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={confidenceDistribution}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                          <XAxis dataKey="range" tick={{ fontSize: 9, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                          <YAxis tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
                          <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
                          <Bar dataKey="count" fill="hsl(187,85%,53%)" radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </div>
              </div>

              {/* Alerts Panel */}
              <div>
                <Card className="bg-card border-border">
                  <CardHeader className="pb-2 pt-4 px-4">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-status-warning" />
                      Active Alerts
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-4 pb-4 space-y-3">
                    {alerts.map(alert => (
                      <button
                        key={alert.id}
                        onClick={() => navigate("/live-flows")}
                        className="w-full text-left p-3 rounded-md bg-secondary/50 hover:bg-secondary transition-colors border border-border"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <div className={`h-2 w-2 rounded-full ${
                            alert.severity === "error" ? "bg-status-error" : "bg-status-warning"
                          }`} />
                          <span className="text-xs font-semibold text-foreground">{alert.title}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground">{alert.message}</p>
                        <p className="text-[10px] text-muted-foreground mt-1">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                        </p>
                      </button>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
