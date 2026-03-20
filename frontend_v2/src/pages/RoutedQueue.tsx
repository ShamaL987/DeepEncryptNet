import { useCallback, useMemo } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Inbox,
  TrendingUp,
  BarChart3,
  CheckCircle,
  Flag,
  MessageSquare,
  Tag,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useSimulatedLoading } from "@/hooks/use-simulated-loading";
import { KpiSkeleton, TableSkeleton } from "@/components/Skeletons";
import { Skeleton } from "@/components/ui/skeleton";
import { usePolling } from "@/hooks/usePolling";
import { fetchRoutedQueueOverview } from "@/api/routedQueueApi";
import { mapRoutedQueueToPageView } from "@/mappers/routedQueueMapper";

function QueueKpi({
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
        <CardContent className="p-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-secondary flex items-center justify-center shrink-0">
            <Icon className="h-5 w-5 text-chart-purple" />
          </div>
          <div>
            <p className="text-[10px] text-muted-foreground uppercase">{title}</p>
            <p className="text-xl font-bold text-foreground">{value}</p>
            {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
          </div>
        </CardContent>
      </Card>
  );
}

export default function RoutedQueue() {
  const navigate = useNavigate();
  const isLoading = useSimulatedLoading(1000);

  const fetchOverviewStable = useCallback(() => fetchRoutedQueueOverview(50), []);
  const { data } = usePolling(fetchOverviewStable, 5000);

  const pageData = useMemo(() => {
    return data
        ? mapRoutedQueueToPageView(data)
        : {
          routedFlows: [],
          groups: [],
          kpiData: {
            unknownQueueSize: 0,
            routedPerMin: 0,
            avgConfidence: "N/A",
            totalRouted: 0,
          },
        };
  }, [data]);

  const { routedFlows, groups, kpiData } = pageData;

  return (
      <DashboardLayout>
        <div className="space-y-4">
          <div>
            <h1 className="text-xl font-bold text-foreground">Routed Queue</h1>
            <p className="text-xs text-muted-foreground">
              Triage center for unconfidently classified flows
            </p>
          </div>

          {isLoading ? (
              <>
                <KpiSkeleton count={4} />
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="lg:col-span-2">
                    <TableSkeleton rows={8} cols={7} />
                  </div>
                  <Card className="bg-card border-border">
                    <CardHeader className="pb-2 pt-4 px-4">
                      <Skeleton className="h-4 w-36" />
                    </CardHeader>
                    <CardContent className="px-4 pb-4 space-y-3">
                      {[1, 2, 3].map((i) => (
                          <Skeleton key={i} className="h-20 w-full rounded-md" />
                      ))}
                    </CardContent>
                  </Card>
                </div>
              </>
          ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <QueueKpi title="Queue Size" value={kpiData.unknownQueueSize} icon={Inbox} />
                  <QueueKpi title="Routed/min" value={kpiData.routedPerMin} icon={TrendingUp} />
                  <QueueKpi title="Avg Confidence" value={kpiData.avgConfidence} icon={BarChart3} />
                  <QueueKpi title="Total Routed" value={kpiData.totalRouted} icon={Inbox} />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="lg:col-span-2">
                    <Card className="bg-card border-border">
                      <CardContent className="p-0">
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className="text-[10px]">Flow ID</TableHead>
                                <TableHead className="text-[10px]">Timestamp</TableHead>
                                <TableHead className="text-[10px]">Type</TableHead>
                                <TableHead className="text-[10px]">Conf.</TableHead>
                                <TableHead className="text-[10px]">Age</TableHead>
                                <TableHead className="text-[10px]">Status</TableHead>
                                <TableHead className="text-[10px]">Actions</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {routedFlows.slice(0, 30).map((f) => (
                                  <TableRow
                                      key={f.id}
                                      className="cursor-pointer hover:bg-accent/50"
                                      onClick={() => navigate(`/flow/${f.id}`)}
                                  >
                                    <TableCell className="text-[11px] font-mono text-primary">
                                      {f.id}
                                    </TableCell>
                                    <TableCell className="text-[11px] text-muted-foreground whitespace-nowrap">
                                      {new Date(f.timestamp).toLocaleTimeString()}
                                    </TableCell>
                                    <TableCell className="text-[11px]">{f.predictedType}</TableCell>
                                    <TableCell className="text-[11px] text-right">
                                      {f.confidence}
                                    </TableCell>
                                    <TableCell className="text-[11px] text-muted-foreground">
                                      {f.ageInQueue}
                                    </TableCell>
                                    <TableCell>
                                      <Badge
                                          className={cn(
                                              "text-[10px] border-0",
                                              f.reviewStatus === "New" &&
                                              "bg-chart-blue/20 text-chart-blue",
                                              f.reviewStatus === "In Review" &&
                                              "bg-chart-orange/20 text-chart-orange",
                                              f.reviewStatus === "Closed" &&
                                              "bg-muted text-muted-foreground"
                                          )}
                                      >
                                        {f.reviewStatus}
                                      </Badge>
                                    </TableCell>
                                    <TableCell>
                                      <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            title="Mark benign"
                                        >
                                          <CheckCircle className="h-3 w-3" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            title="Flag suspicious"
                                        >
                                          <Flag className="h-3 w-3" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            title="Add note"
                                        >
                                          <MessageSquare className="h-3 w-3" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            title="Assign label"
                                        >
                                          <Tag className="h-3 w-3" />
                                        </Button>
                                      </div>
                                    </TableCell>
                                  </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <Card className="bg-card border-border">
                    <CardHeader className="pb-2 pt-4 px-4">
                      <CardTitle className="text-sm font-medium">Grouping Suggestions</CardTitle>
                    </CardHeader>
                    <CardContent className="px-4 pb-4 space-y-3">
                      {groups.map((g) => (
                          <div
                              key={g.label}
                              className="p-3 rounded-md bg-secondary/50 border border-border"
                          >
                            <p className="text-xs font-medium text-foreground">{g.label}</p>
                            <p className="text-lg font-bold text-foreground mt-1">{g.count} flows</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                              Nearest class: {g.nearest}
                            </p>
                          </div>
                      ))}
                    </CardContent>
                  </Card>
                </div>
              </>
          )}
        </div>
      </DashboardLayout>
  );
}