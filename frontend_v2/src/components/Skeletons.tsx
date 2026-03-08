import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/** KPI row skeleton — renders n cards */
export function KpiSkeleton({ count = 7 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="bg-card border-border">
          <CardContent className="p-4 space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-7 w-16" />
            <Skeleton className="h-2.5 w-12" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/** Chart card skeleton */
export function ChartSkeleton({ height = 200 }: { height?: number }) {
  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-2 pt-4 px-4">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <Skeleton className="w-full rounded-md" style={{ height }} />
      </CardContent>
    </Card>
  );
}

/** Table skeleton — renders rows of cells */
export function TableSkeleton({ rows = 8, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <Card className="bg-card border-border">
      <CardContent className="p-0">
        <div className="p-4 space-y-3">
          {/* Header row */}
          <div className="flex gap-4">
            {Array.from({ length: cols }).map((_, i) => (
              <Skeleton key={i} className="h-3 flex-1" />
            ))}
          </div>
          {/* Data rows */}
          {Array.from({ length: rows }).map((_, r) => (
            <div key={r} className="flex gap-4">
              {Array.from({ length: cols }).map((_, c) => (
                <Skeleton key={c} className="h-4 flex-1" />
              ))}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/** Pipeline status skeleton */
export function PipelineSkeleton() {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center gap-2">
          <Skeleton className="h-8 w-32 rounded-md" />
          {i < 3 && <Skeleton className="h-3 w-3" />}
        </div>
      ))}
    </div>
  );
}

/** Metric card skeleton for System Health */
export function MetricSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-secondary/50 rounded-md p-4 border border-border space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-2.5 w-16" />
          </div>
          <Skeleton className="h-6 w-14" />
        </div>
      ))}
    </div>
  );
}

/** Full-page loading wrapper — simulates data fetching delay */
export function PageLoader({ children, isLoading }: { children: React.ReactNode; isLoading: boolean }) {
  if (isLoading) return <>{children}</>;
  return null;
}
