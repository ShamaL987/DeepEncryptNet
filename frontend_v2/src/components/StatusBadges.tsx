import { Badge } from "@/components/ui/badge";
import type { Reliability } from "@/data/mockData";
import { cn } from "@/lib/utils";

export function ReliabilityBadge({ reliability }: { reliability: Reliability }) {
  return (
    <Badge
      className={cn(
        "text-[10px] font-semibold border-0",
        reliability === "Reliable" && "bg-reliable/20 text-reliable",
        reliability === "Unreliable" && "bg-unreliable/20 text-unreliable",
        reliability === "Unknown" && "bg-unknown/20 text-unknown"
      )}
    >
      {reliability}
    </Badge>
  );
}

export function DecisionBadge({ decision }: { decision: "Classified" | "Routed" }) {
  return (
    <Badge
      className={cn(
        "text-[10px] font-semibold border-0",
        decision === "Classified" && "bg-chart-green/20 text-chart-green",
        decision === "Routed" && "bg-chart-purple/20 text-chart-purple"
      )}
    >
      {decision}
    </Badge>
  );
}

export function StatusBadge({ status }: { status: "OK" | "Degraded" | "Down" }) {
  return (
    <Badge
      className={cn(
        "text-[10px] font-semibold border-0",
        status === "OK" && "bg-status-ok/20 text-status-ok",
        status === "Degraded" && "bg-status-degraded/20 text-status-degraded",
        status === "Down" && "bg-status-error/20 text-status-error"
      )}
    >
      {status}
    </Badge>
  );
}
