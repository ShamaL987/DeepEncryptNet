import { useCallback, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent } from "@/components/ui/card";
import { ReliabilityBadge, DecisionBadge } from "@/components/StatusBadges";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { TableSkeleton } from "@/components/Skeletons";
import { Skeleton } from "@/components/ui/skeleton";
import { usePolling } from "@/hooks/usePolling";
import { fetchLiveFlowsOverview } from "@/api/liveFlowsApi";
import { mapLiveFlowsOverviewToViewModel } from "@/mappers/liveFlowsMapper";

export default function LiveFlows() {
  // const navigate = useNavigate();
  const [decision, setDecision] = useState("All");
  const [predictedClass, setPredictedClass] = useState("All");
  const [reliability, setReliability] = useState("All");
  const [alertsOnly, setAlertsOnly] = useState(false);

  const fetchOverviewStable = useCallback(() => {
    return fetchLiveFlowsOverview({
      decision,
      predictedClass,
      reliability,
      alertsOnly,
      limit: 50,
    });
  }, [decision, predictedClass, reliability, alertsOnly]);

  const { data, loading } = usePolling(fetchOverviewStable, 5000);

  const viewModel = useMemo(() => {
    return data
        ? mapLiveFlowsOverviewToViewModel(data)
        : {
          items: [],
          summary: {
            total: 0,
            classified: 0,
            routed: 0,
            reliable: 0,
            unreliable: 0,
            unknown: 0,
            alerts: 0,
          },
          filterOptions: {
            decisions: ["All", "Classified", "Routed"],
            predictedClasses: ["All"],
            reliabilities: ["All", "Reliable", "Unreliable", "Unknown"],
          },
        };
  }, [data]);

  const isLoading = loading && !data;

  return (
      <DashboardLayout>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-foreground">Live Flows</h1>
              <p className="text-xs text-muted-foreground">
                Real-time flow monitoring and analysis
              </p>
            </div>
            <Button variant="outline" size="sm" className="gap-2">
              <Download className="h-3.5 w-3.5" /> Export CSV
            </Button>
          </div>

          {isLoading ? (
              <>
                <Card className="bg-card border-border">
                  <CardContent className="p-4">
                    <div className="flex flex-wrap gap-4">
                      {Array.from({ length: 4 }).map((_, index) => (
                          <Skeleton key={index} className="h-8 w-[130px] rounded-md" />
                      ))}
                    </div>
                  </CardContent>
                </Card>
                <TableSkeleton rows={10} cols={13} />
              </>
          ) : (
              <>
                <Card className="bg-card border-border">
                  <CardContent className="p-4">
                    <div className="flex flex-wrap items-end gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] text-muted-foreground uppercase">
                          Decision
                        </label>
                        <Select value={decision} onValueChange={setDecision}>
                          <SelectTrigger className="w-[130px] h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {viewModel.filterOptions.decisions.map((value) => (
                                <SelectItem key={value} value={value}>
                                  {value}
                                </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] text-muted-foreground uppercase">
                          Predicted Class
                        </label>
                        <Select value={predictedClass} onValueChange={setPredictedClass}>
                          <SelectTrigger className="w-[140px] h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {viewModel.filterOptions.predictedClasses.map((value) => (
                                <SelectItem key={value} value={value}>
                                  {value}
                                </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] text-muted-foreground uppercase">
                          Reliability
                        </label>
                        <Select value={reliability} onValueChange={setReliability}>
                          <SelectTrigger className="w-[130px] h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {viewModel.filterOptions.reliabilities.map((value) => (
                                <SelectItem key={value} value={value}>
                                  {value}
                                </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex items-center gap-2">
                        <Switch checked={alertsOnly} onCheckedChange={setAlertsOnly} />
                        <span className="text-xs text-muted-foreground">Alerts only</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-card border-border">
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="text-[10px]">Timestamp</TableHead>
                            <TableHead className="text-[10px]">Flow ID</TableHead>
                            <TableHead className="text-[10px]">Src → Dst</TableHead>
                            <TableHead className="text-[10px]">Protocol</TableHead>
                            <TableHead className="text-[10px]">Pkts</TableHead>
                            <TableHead className="text-[10px]">Bytes</TableHead>
                            <TableHead className="text-[10px]">Dur (s)</TableHead>
                            <TableHead className="text-[10px]">Type</TableHead>
                            <TableHead className="text-[10px]">Conf.</TableHead>
                            <TableHead className="text-[10px]">Decision</TableHead>
                            <TableHead className="text-[10px]">Reliability</TableHead>
                            <TableHead className="text-[10px]">Reason</TableHead>
                            <TableHead className="text-[10px]">Model</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {viewModel.items.map((flow) => (
                              <TableRow
                                  key={flow.id}
                                  className="cursor-pointer hover:bg-accent/50"
                                  // onClick={() => navigate(`/flow/${flow.id}`)}
                              >
                                <TableCell className="text-[11px] text-muted-foreground whitespace-nowrap">
                                  {new Date(flow.timestamp).toLocaleTimeString()}
                                </TableCell>
                                <TableCell className="text-[11px] font-mono text-primary">
                                  {flow.id}
                                </TableCell>
                                <TableCell className="text-[10px] font-mono text-muted-foreground whitespace-nowrap">
                                  {flow.srcToDst}
                                </TableCell>
                                <TableCell className="text-[11px]">{flow.protocol}</TableCell>
                                <TableCell className="text-[11px] text-right">
                                  {flow.packets.toLocaleString()}
                                </TableCell>
                                <TableCell className="text-[11px] text-right">
                                  {(flow.bytes / 1024).toFixed(1)}KB
                                </TableCell>
                                <TableCell className="text-[11px] text-right">
                                  {flow.duration !== null ? `${flow.duration}s` : "N/A"}
                                </TableCell>
                                <TableCell className="text-[11px]">{flow.predictedType}</TableCell>
                                <TableCell className="text-[11px] text-right">
                                  {flow.confidence.toFixed(2)}
                                </TableCell>
                                <TableCell>
                                  <DecisionBadge decision={flow.decision} />
                                </TableCell>
                                <TableCell>
                                  <ReliabilityBadge reliability={flow.reliability} />
                                </TableCell>
                                <TableCell className="text-[10px] text-muted-foreground max-w-[200px] truncate">
                                  {flow.reason}
                                </TableCell>
                                <TableCell className="text-[10px] text-muted-foreground">
                                  {flow.modelVersion}
                                </TableCell>
                              </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="p-3 border-t border-border">
                      <p className="text-xs text-muted-foreground">
                        Showing {viewModel.items.length} of {viewModel.summary.total} flows
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </>
          )}
        </div>
      </DashboardLayout>
  );
}