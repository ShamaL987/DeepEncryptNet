import { useCallback, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useNavigate } from "react-router-dom";
import {
  Clock,
  Waves,
  Zap,
  CheckCircle2,
  ArrowRightLeft,
  Inbox,
  AlertTriangle,
} from "lucide-react";
import { KpiSkeleton, ChartSkeleton, PipelineSkeleton } from "@/components/Skeletons";
import { Skeleton } from "@/components/ui/skeleton";
import { usePolling } from "@/hooks/usePolling";
import { fetchDashboardOverview } from "@/api/dashboardApi";
import { mapDashboardOverviewToViewModel } from "@/mappers/dashboardMapper";

const CHART_COLORS = [
  "hsl(210,100%,56%)",
  "hsl(142,70%,49%)",
  "hsl(25,95%,53%)",
  "hsl(270,70%,60%)",
  "hsl(187,85%,53%)",
  "hsl(0,72%,51%)",
  "hsl(45,93%,58%)",
];

function KpiCard({
                   title,
                   value,
                   sub,
                   icon: Icon,
                 }: {
  title: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
}) {
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
  const [selectedWindow] = useState("1h");

  const fetchOverviewStable = useCallback(() => fetchDashboardOverview(), []);
  const { data, loading } = usePolling(fetchOverviewStable, 5000);

  const pageData = useMemo(() => {
    return data
        ? mapDashboardOverviewToViewModel(data)
        : {
          status: "stopped" as const,
          isRunning: false,
          pipelineName: null,
          kpiData: {
            uptime: "0s",
            uniqueFlows: 0,
            processedPerMin: 0,
            classifiedCount: 0,
            classifiedPct: 0,
            routedCount: 0,
            routedPct: 0,
            unknownQueueSize: 0,
            lowConfidenceRate: 0,
            lowConfidencePct: 0,
          },
          flowsOverTime: [],
          classifiedVsRouted: [],
          trafficMix: [],
          confidenceDistribution: [],
          alerts: [],
        };
  }, [data]);

  const isLoading = loading && !data;

  return (
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-foreground">Overview Dashboard</h1>
              <p className="text-xs text-muted-foreground">
                Encrypted traffic monitoring • Real-time pipeline status
              </p>
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
                        {[1, 2, 3].map((i) => (
                            <Skeleton key={i} className="h-20 w-full rounded-md" />
                        ))}
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </>
          ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                  <KpiCard title="Uptime" value={pageData.kpiData.uptime} icon={Clock} />
                  <KpiCard title="Unique Flows" value={pageData.kpiData.uniqueFlows} icon={Waves} />
                  <KpiCard
                      title="Processed/min"
                      value={pageData.kpiData.processedPerMin}
                      icon={Zap}
                  />
                  <KpiCard
                      title="Classified"
                      value={pageData.kpiData.classifiedCount}
                      sub={`${pageData.kpiData.classifiedPct}%`}
                      icon={CheckCircle2}
                  />
                  <KpiCard
                      title="Routed"
                      value={pageData.kpiData.routedCount}
                      sub={`${pageData.kpiData.routedPct}%`}
                      icon={ArrowRightLeft}
                  />
                  <KpiCard
                      title="Queue Size"
                      value={pageData.kpiData.unknownQueueSize}
                      icon={Inbox}
                  />
                  <KpiCard
                      title="Low Conf. Rate"
                      value={pageData.kpiData.lowConfidenceRate}
                      sub={`${pageData.kpiData.lowConfidencePct}%`}
                      icon={AlertTriangle}
                  />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="lg:col-span-2 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Card className="bg-card border-border">
                        <CardHeader className="pb-2 pt-4 px-4">
                          <CardTitle className="text-sm font-medium">Flows Over Time</CardTitle>
                        </CardHeader>
                        <CardContent className="px-2 pb-4">
                          <ResponsiveContainer width="100%" height={200}>
                            <LineChart data={pageData.flowsOverTime}>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                              <XAxis
                                  dataKey="time"
                                  tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }}
                                  axisLine={false}
                              />
                              <YAxis
                                  tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }}
                                  axisLine={false}
                              />
                              <Tooltip
                                  contentStyle={{
                                    background: "hsl(220,18%,13%)",
                                    border: "1px solid hsl(220,14%,20%)",
                                    borderRadius: 6,
                                    fontSize: 12,
                                  }}
                              />
                              <Line
                                  type="monotone"
                                  dataKey="flows"
                                  stroke="hsl(210,100%,56%)"
                                  strokeWidth={2}
                                  dot={false}
                              />
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
                            <AreaChart data={pageData.classifiedVsRouted}>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                              <XAxis
                                  dataKey="time"
                                  tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }}
                                  axisLine={false}
                              />
                              <YAxis
                                  tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }}
                                  axisLine={false}
                              />
                              <Tooltip
                                  contentStyle={{
                                    background: "hsl(220,18%,13%)",
                                    border: "1px solid hsl(220,14%,20%)",
                                    borderRadius: 6,
                                    fontSize: 12,
                                  }}
                              />
                              <Area
                                  type="monotone"
                                  dataKey="classified"
                                  stackId="1"
                                  stroke="hsl(142,70%,49%)"
                                  fill="hsl(142,70%,49%)"
                                  fillOpacity={0.3}
                              />
                              <Area
                                  type="monotone"
                                  dataKey="routed"
                                  stackId="1"
                                  stroke="hsl(270,70%,60%)"
                                  fill="hsl(270,70%,60%)"
                                  fillOpacity={0.3}
                              />
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
                              <Pie
                                  data={pageData.trafficMix}
                                  dataKey="value"
                                  nameKey="name"
                                  cx="50%"
                                  cy="50%"
                                  innerRadius={50}
                                  outerRadius={80}
                                  paddingAngle={2}
                              >
                                {pageData.trafficMix.map((_, i) => (
                                    <Cell
                                        key={i}
                                        fill={CHART_COLORS[i % CHART_COLORS.length]}
                                    />
                                ))}
                              </Pie>
                              <Tooltip
                                  contentStyle={{
                                    background: "hsl(220,18%,13%)",
                                    border: "1px solid hsl(220,14%,20%)",
                                    borderRadius: 6,
                                    fontSize: 12,
                                  }}
                              />
                              <Legend wrapperStyle={{ fontSize: 10 }} />
                            </PieChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>

                      <Card className="bg-card border-border">
                        <CardHeader className="pb-2 pt-4 px-4">
                          <CardTitle className="text-sm font-medium">
                            Confidence Distribution
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="px-2 pb-4">
                          <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={pageData.confidenceDistribution}>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
                              <XAxis
                                  dataKey="range"
                                  tick={{ fontSize: 9, fill: "hsl(215,15%,55%)" }}
                                  axisLine={false}
                              />
                              <YAxis
                                  tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }}
                                  axisLine={false}
                              />
                              <Tooltip
                                  contentStyle={{
                                    background: "hsl(220,18%,13%)",
                                    border: "1px solid hsl(220,14%,20%)",
                                    borderRadius: 6,
                                    fontSize: 12,
                                  }}
                              />
                              <Bar
                                  dataKey="count"
                                  fill="hsl(187,85%,53%)"
                                  radius={[2, 2, 0, 0]}
                              />
                            </BarChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                    </div>
                  </div>

                  <div>
                    <Card className="bg-card border-border">
                      <CardHeader className="pb-2 pt-4 px-4">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-status-warning" />
                          Active Alerts
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="px-4 pb-4 space-y-3">
                        {pageData.alerts.map((alert) => (
                            <button
                                key={alert.id}
                                onClick={() => navigate("/live-flows")}
                                className="w-full text-left p-3 rounded-md bg-secondary/50 hover:bg-secondary transition-colors border border-border"
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <div
                                    className={`h-2 w-2 rounded-full ${
                                        alert.severity === "high" || alert.severity === "error"
                                            ? "bg-status-error"
                                            : "bg-status-warning"
                                    }`}
                                />
                                <span className="text-xs font-semibold text-foreground">
                            {alert.title}
                          </span>
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