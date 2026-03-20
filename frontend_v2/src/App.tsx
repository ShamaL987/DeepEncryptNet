import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import LiveFlows from "./pages/LiveFlows";
import FlowDetail from "./pages/FlowDetail";
import RoutedQueue from "./pages/RoutedQueue";
import SystemHealth from "./pages/SystemHealth";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import {Layout} from "@/layout/layout.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Login />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/live-flows" element={<LiveFlows />} />
            {/*<Route path="/flow/:flowId" element={<FlowDetail />} />*/}
            <Route path="/routed-queue" element={<RoutedQueue />} />
            <Route path="/system-health" element={<SystemHealth />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
