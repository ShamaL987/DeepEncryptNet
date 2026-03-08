import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReliabilityBadge, DecisionBadge } from "@/components/StatusBadges";
import { mockFlows } from "@/data/mockData";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell
} from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useSimulatedLoading } from "@/hooks/use-simulated-loading";
import { TableSkeleton } from "@/components/Skeletons";
import { Skeleton } from "@/components/ui/skeleton";

const trafficTypes = ["All", "Browsing", "Streaming", "File Transfer", "VoIP", "Download", "Email", "Chat"];
const protocols = ["All", "TLS 1.3", "TLS 1.2", "QUIC", "DTLS", "TCP/TLS"];

export default function LiveFlows() {
  const navigate = useNavigate();
  const [decision, setDecision] = useState("All");
  const [reliability, setReliability] = useState("All");
  const [confRange, setConfRange] = useState([0]);
  const [predictedClass, setPredictedClass] = useState("All");
  const [protocol, setProtocol] = useState("All");
  const [alertsOnly, setAlertsOnly] = useState(false);
  const isLoading = useSimulatedLoading(1000);

  const filtered = useMemo(() => {
    return mockFlows.filter(f => {
      if (decision !== "All" && f.decision !== decision) return false;
      if (reliability !== "All" && f.reliability !== reliability) return false;
      if (f.confidence < confRange[0]) return false;
      if (predictedClass !== "All" && f.predictedType !== predictedClass) return false;
      if (protocol !== "All" && f.protocol !== protocol) return false;
      if (alertsOnly && f.reliability === "Reliable") return false;
      return true;
    });
  }, [decision, reliability, confRange, predictedClass, protocol, alertsOnly]);

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground">Live Flows</h1>
            <p className="text-xs text-muted-foreground">Real-time flow monitoring and analysis</p>
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
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-[130px] rounded-md" />
                  ))}
                </div>
              </CardContent>
            </Card>
            <TableSkeleton rows={10} cols={8} />
          </>
        ) : (
          <>
            {/* Filters */}
            <Card className="bg-card border-border">
              <CardContent className="p-4">
                <div className="flex flex-wrap items-end gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase">Decision</label>
                    <Select value={decision} onValueChange={setDecision}>
                      <SelectTrigger className="w-[130px] h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {["All", "Classified", "Routed"].map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase">Reliability</label>
                    <Select value={reliability} onValueChange={setReliability}>
                      <SelectTrigger className="w-[130px] h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {["All", "Reliable", "Unreliable", "Unknown"].map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase">Min Confidence: {confRange[0]}</label>
                    <Slider value={confRange} onValueChange={setConfRange} min={0} max={1} step={0.05} className="w-[140px]" />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase">Predicted Class</label>
                    <Select value={predictedClass} onValueChange={setPredictedClass}>
                      <SelectTrigger className="w-[140px] h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {trafficTypes.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase">Protocol</label>
                    <Select value={protocol} onValueChange={setProtocol}>
                      <SelectTrigger className="w-[120px] h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {protocols.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
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

            {/* Table */}
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
                      {filtered.slice(0, 50).map(f => (
                        <TableRow key={f.id} className="cursor-pointer hover:bg-accent/50" onClick={() => navigate(`/flow/${f.id}`)}>
                          <TableCell className="text-[11px] text-muted-foreground whitespace-nowrap">{new Date(f.timestamp).toLocaleTimeString()}</TableCell>
                          <TableCell className="text-[11px] font-mono text-primary">{f.id}</TableCell>
                          <TableCell className="text-[10px] font-mono text-muted-foreground whitespace-nowrap">{f.src} → {f.dst}</TableCell>
                          <TableCell className="text-[11px]">{f.protocol}</TableCell>
                          <TableCell className="text-[11px] text-right">{f.packets.toLocaleString()}</TableCell>
                          <TableCell className="text-[11px] text-right">{(f.bytes / 1024).toFixed(1)}KB</TableCell>
                          <TableCell className="text-[11px] text-right">{f.duration}s</TableCell>
                          <TableCell className="text-[11px]">{f.predictedType}</TableCell>
                          <TableCell className="text-[11px] text-right">{f.confidence}</TableCell>
                          <TableCell><DecisionBadge decision={f.decision} /></TableCell>
                          <TableCell><ReliabilityBadge reliability={f.reliability} /></TableCell>
                          <TableCell className="text-[10px] text-muted-foreground max-w-[200px] truncate">{f.reason}</TableCell>
                          <TableCell className="text-[10px] text-muted-foreground">{f.modelVersion}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <div className="p-3 border-t border-border">
                  <p className="text-xs text-muted-foreground">Showing {Math.min(50, filtered.length)} of {filtered.length} flows</p>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
