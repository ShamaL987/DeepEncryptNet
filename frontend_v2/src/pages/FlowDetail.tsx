// import { DashboardLayout } from "@/components/DashboardLayout";
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import { ReliabilityBadge, DecisionBadge } from "@/components/StatusBadges";
// import { useParams, useNavigate } from "react-router-dom";
// import { Button } from "@/components/ui/button";
// import { ArrowLeft } from "lucide-react";
// import {
//   LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
// } from "recharts";
// import { useMemo } from "react";
// import { useSimulatedLoading } from "@/hooks/use-simulated-loading";
// import { KpiSkeleton, ChartSkeleton } from "@/components/Skeletons";
// import { Skeleton } from "@/components/ui/skeleton";
//
// export default function FlowDetail() {
//   const { flowId } = useParams();
//   const navigate = useNavigate();
//   const flow = mockFlows.find(f => f.id === flowId);
//   const isLoading = useSimulatedLoading(800);
//
//   const behaviorData = useMemo(() => {
//     if (!flow) return [];
//     return generateFlowBehavior(flow.duration);
//   }, [flow]);
//
//   if (!flow) {
//     return (
//       <DashboardLayout>
//         <div className="text-center py-20">
//           <p className="text-muted-foreground">Flow not found</p>
//           <Button variant="ghost" onClick={() => navigate("/live-flows")} className="mt-4">
//             <ArrowLeft className="h-4 w-4 mr-2" /> Back to Live Flows
//           </Button>
//         </div>
//       </DashboardLayout>
//     );
//   }
//
//   const stats = [
//     { label: "packets_total", value: flow.packets },
//     { label: "bytes_total", value: flow.bytes.toLocaleString() },
//     { label: "duration (s)", value: flow.duration },
//     { label: "avg_pkt_size", value: flow.avgPktSize },
//     { label: "pkt_rate_mean", value: flow.pktRateMean },
//     { label: "pkt_rate_std", value: flow.pktRateStd },
//     { label: "byte_rate_mean", value: flow.byteRateMean.toLocaleString() },
//     { label: "byte_rate_std", value: flow.byteRateStd.toLocaleString() },
//     { label: "burst_count", value: flow.burstCount },
//     { label: "burst_avg_length", value: flow.burstAvgLength },
//   ];
//
//   return (
//     <DashboardLayout>
//       <div className="space-y-4">
//         <div className="flex items-center gap-3">
//           <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
//             <ArrowLeft className="h-4 w-4" />
//           </Button>
//           <div>
//             <h1 className="text-xl font-bold text-foreground font-mono">{flow.id}</h1>
//             <p className="text-xs text-muted-foreground">Flow Detail — Drill-Down View</p>
//           </div>
//         </div>
//
//         {isLoading ? (
//           <div className="space-y-4">
//             <Card className="bg-card border-border">
//               <CardContent className="p-4">
//                 <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
//                   {Array.from({ length: 7 }).map((_, i) => (
//                     <div key={i} className="space-y-1">
//                       <Skeleton className="h-2.5 w-14" />
//                       <Skeleton className="h-5 w-24" />
//                     </div>
//                   ))}
//                 </div>
//               </CardContent>
//             </Card>
//             <Card className="bg-card border-border">
//               <CardHeader className="pb-2 pt-4 px-4"><Skeleton className="h-4 w-32" /></CardHeader>
//               <CardContent className="px-4 pb-4">
//                 <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
//                   {Array.from({ length: 5 }).map((_, i) => (
//                     <div key={i} className="space-y-1">
//                       <Skeleton className="h-2.5 w-20" />
//                       <Skeleton className="h-5 w-16" />
//                     </div>
//                   ))}
//                 </div>
//               </CardContent>
//             </Card>
//             <Card className="bg-card border-border">
//               <CardHeader className="pb-2 pt-4 px-4"><Skeleton className="h-4 w-28" /></CardHeader>
//               <CardContent className="px-4 pb-4">
//                 <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
//                   {Array.from({ length: 10 }).map((_, i) => (
//                     <Skeleton key={i} className="h-14 rounded-md" />
//                   ))}
//                 </div>
//               </CardContent>
//             </Card>
//             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
//               <ChartSkeleton />
//               <ChartSkeleton />
//             </div>
//           </div>
//         ) : (
//           <>
//             {/* Flow Header */}
//             <Card className="bg-card border-border">
//               <CardContent className="p-4">
//                 <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
//                   {[
//                     ["First Seen", new Date(flow.timestamp).toLocaleString()],
//                     ["Src", flow.src],
//                     ["Dst", flow.dst],
//                     ["Protocol", flow.protocol],
//                     ["Packets", flow.packets.toLocaleString()],
//                     ["Bytes", `${(flow.bytes / 1024).toFixed(1)} KB`],
//                     ["Duration", `${flow.duration}s`],
//                   ].map(([k, v]) => (
//                     <div key={k as string}>
//                       <p className="text-[10px] text-muted-foreground uppercase">{k}</p>
//                       <p className="text-sm font-mono text-foreground mt-0.5">{v}</p>
//                     </div>
//                   ))}
//                 </div>
//               </CardContent>
//             </Card>
//
//             {/* Decision Summary */}
//             <Card className="bg-card border-border">
//               <CardHeader className="pb-2 pt-4 px-4">
//                 <CardTitle className="text-sm font-medium">Decision Summary</CardTitle>
//               </CardHeader>
//               <CardContent className="px-4 pb-4">
//                 <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
//                   <div>
//                     <p className="text-[10px] text-muted-foreground uppercase">Predicted Class</p>
//                     <p className="text-sm font-semibold text-foreground mt-1">{flow.predictedType}</p>
//                   </div>
//                   <div>
//                     <p className="text-[10px] text-muted-foreground uppercase">Confidence</p>
//                     <p className="text-sm font-mono font-semibold text-foreground mt-1">{flow.confidence}</p>
//                   </div>
//                   <div>
//                     <p className="text-[10px] text-muted-foreground uppercase">Decision</p>
//                     <div className="mt-1"><DecisionBadge decision={flow.decision} /></div>
//                   </div>
//                   <div>
//                     <p className="text-[10px] text-muted-foreground uppercase">Reliability</p>
//                     <div className="mt-1"><ReliabilityBadge reliability={flow.reliability} /></div>
//                   </div>
//                   <div>
//                     <p className="text-[10px] text-muted-foreground uppercase">Reason</p>
//                     <p className="text-xs text-muted-foreground mt-1">{flow.reason}</p>
//                   </div>
//                 </div>
//               </CardContent>
//             </Card>
//
//             {/* Stats Summary */}
//             <Card className="bg-card border-border">
//               <CardHeader className="pb-2 pt-4 px-4">
//                 <CardTitle className="text-sm font-medium">Feature Snapshot</CardTitle>
//               </CardHeader>
//               <CardContent className="px-4 pb-4">
//                 <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
//                   {stats.map(s => (
//                     <div key={s.label} className="bg-secondary/50 rounded-md p-3">
//                       <p className="text-[10px] text-muted-foreground font-mono">{s.label}</p>
//                       <p className="text-sm font-mono font-semibold text-foreground mt-1">{s.value}</p>
//                     </div>
//                   ))}
//                 </div>
//               </CardContent>
//             </Card>
//
//             {/* Behavior Charts */}
//             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
//               <Card className="bg-card border-border">
//                 <CardHeader className="pb-2 pt-4 px-4">
//                   <CardTitle className="text-sm font-medium">Packets/sec Over Time</CardTitle>
//                 </CardHeader>
//                 <CardContent className="px-2 pb-4">
//                   <ResponsiveContainer width="100%" height={200}>
//                     <LineChart data={behaviorData}>
//                       <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
//                       <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
//                       <YAxis tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
//                       <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
//                       <Line type="monotone" dataKey="packetsPerSec" stroke="hsl(210,100%,56%)" strokeWidth={2} dot={false} />
//                     </LineChart>
//                   </ResponsiveContainer>
//                 </CardContent>
//               </Card>
//
//               <Card className="bg-card border-border">
//                 <CardHeader className="pb-2 pt-4 px-4">
//                   <CardTitle className="text-sm font-medium">Bytes/sec Over Time</CardTitle>
//                 </CardHeader>
//                 <CardContent className="px-2 pb-4">
//                   <ResponsiveContainer width="100%" height={200}>
//                     <LineChart data={behaviorData}>
//                       <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,20%)" />
//                       <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
//                       <YAxis tick={{ fontSize: 10, fill: "hsl(215,15%,55%)" }} axisLine={false} />
//                       <Tooltip contentStyle={{ background: "hsl(220,18%,13%)", border: "1px solid hsl(220,14%,20%)", borderRadius: 6, fontSize: 12 }} />
//                       <Line type="monotone" dataKey="bytesPerSec" stroke="hsl(142,70%,49%)" strokeWidth={2} dot={false} />
//                     </LineChart>
//                   </ResponsiveContainer>
//                 </CardContent>
//               </Card>
//             </div>
//           </>
//         )}
//       </div>
//     </DashboardLayout>
//   );
// }
