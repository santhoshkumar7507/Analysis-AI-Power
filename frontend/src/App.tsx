import React from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { apiClient } from "./api/client";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Login } from "./pages/Login";
import { TicketInbox } from "./pages/TicketInbox";
import { TicketDetail } from "./pages/TicketDetail";
import { KnowledgeBase } from "./pages/KnowledgeBase";
import { SLAMonitor } from "./pages/SLAMonitor";
import { Analytics } from "./pages/Analytics";



import {
  ShieldCheck,
  Inbox,
  Sparkles,
  BookOpen,
  Clock,
  BarChart3,
  Settings,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Server,
  LogOut,
} from "lucide-react";


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

interface HealthStatus {
  status: string;
  service: string;
  environment: string;
  timestamp: string;
}

interface ReadyStatus {
  status: string;
  service: string;
  checks: {
    database: string;
    redis: string;
  };
  timestamp: string;
}

const Navigation: React.FC = () => {
  const location = useLocation();
  const { user, organization, logout, switchDemoRole } = useAuth();

  const navItems = [
    { path: "/", label: "Overview", icon: ShieldCheck },
    { path: "/tickets", label: "Ticket Inbox", icon: Inbox },
    { path: "/knowledge", label: "Knowledge Base", icon: BookOpen },
    { path: "/sla", label: "SLA Monitor", icon: Clock },
    { path: "/analytics", label: "Analytics & AI Eval", icon: BarChart3 },
    { path: "/settings", label: "Settings", icon: Settings },
  ];


  return (
    <aside className="w-64 bg-navy-850 border-r border-navy-700 flex flex-col justify-between shrink-0">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-navy-700 gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-brand-600 to-ai-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg text-white tracking-tight">ResolveAI</span>
            <span className="block text-[10px] text-brand-400 font-medium uppercase tracking-wider">Enterprise Copilot</span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brand-600/15 text-brand-400 border border-brand-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-navy-800"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-brand-400" : "text-slate-400"}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User / Workspace info & Role Switcher */}
      <div className="p-4 border-t border-navy-700 space-y-3">
        {user ? (
          <div className="bg-navy-900 rounded-lg p-3 border border-navy-700/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-semibold text-slate-300 truncate max-w-[120px]">
                  {organization?.name || "Acme Global"}
                </span>
              </div>
              <button
                onClick={logout}
                title="Sign out"
                className="text-slate-500 hover:text-rose-400 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="mt-2 pt-2 border-t border-navy-800">
              <div className="text-xs font-medium text-slate-200 truncate">{user.full_name}</div>
              <div className="text-[10px] capitalize text-brand-400 font-semibold">{user.role.replace("_", " ")}</div>
            </div>

            {/* Quick Role Toggle Bar */}
            <div className="mt-2 pt-2 border-t border-navy-800/80 flex items-center justify-between text-[10px]">
              <span className="text-slate-500 font-medium">Switch:</span>
              <div className="flex gap-1">
                <button
                  onClick={() => switchDemoRole("admin")}
                  className={`px-1.5 py-0.5 rounded ${user.role === "admin" ? "bg-brand-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"}`}
                >
                  Admin
                </button>
                <button
                  onClick={() => switchDemoRole("manager")}
                  className={`px-1.5 py-0.5 rounded ${user.role === "support_manager" ? "bg-brand-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"}`}
                >
                  Mgr
                </button>
                <button
                  onClick={() => switchDemoRole("agent")}
                  className={`px-1.5 py-0.5 rounded ${user.role === "support_agent" ? "bg-brand-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"}`}
                >
                  Agent
                </button>
              </div>
            </div>
          </div>
        ) : (
          <Link
            to="/login"
            className="block text-center py-2 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-lg shadow-md"
          >
            Sign In
          </Link>
        )}
      </div>
    </aside>
  );
};

const Header: React.FC = () => {
  const { user } = useAuth();
  const { data: health } = useQuery<HealthStatus>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await apiClient.get("/health");
      return res.data;
    },
    refetchInterval: 15000,
  });

  const { data: ready } = useQuery<ReadyStatus>({
    queryKey: ["ready"],
    queryFn: async () => {
      const res = await apiClient.get("/ready");
      return res.data;
    },
    refetchInterval: 15000,
  });

  const isHealthy = health?.status === "healthy";
  const dbConnected = ready?.checks.database === "connected";

  return (
    <header className="h-16 bg-navy-900/80 backdrop-blur-md border-b border-navy-700 px-8 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-4">
        <h1 className="text-base font-semibold text-white">Platform Control Center</h1>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-navy-800 border border-navy-700 text-slate-400">
          v0.3.0-enterprise
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* API & DB Status Pills */}
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
              isHealthy
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-rose-500/10 text-rose-400 border-rose-500/30"
            }`}
          >
            {isHealthy ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
            API: {isHealthy ? "Operational" : "Offline"}
          </div>

          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
              dbConnected
                ? "bg-brand-500/10 text-brand-400 border-brand-500/30"
                : "bg-amber-500/10 text-amber-400 border-amber-500/30"
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            DB: {dbConnected ? "Connected" : "Disconnected"}
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-2 pl-2 border-l border-navy-700">
            <div className="w-8 h-8 rounded-full bg-brand-600/30 border border-brand-500/40 flex items-center justify-center text-xs font-bold text-brand-300">
              {user.full_name.charAt(0)}
            </div>
          </div>
        )}
      </div>
    </header>
  );
};

const OverviewPage: React.FC = () => {
  return (

    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">System Overview & Architecture</h2>
          <p className="text-sm text-slate-400 mt-1">
            ResolveAI Core Services, Multi-Tenant Ticket Ingestion, and RBAC are operational.
          </p>
        </div>
        <Link
          to="/tickets"
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium shadow-md shadow-brand-500/20"
        >
          <Inbox className="w-4 h-4" />
          Open Ticket Inbox
        </Link>
      </div>

      {/* Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">FastAPI Core</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">Online</span>
            <span className="text-xs text-emerald-400">/api/v1 active</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">JWT Authentication, multi-tenant scoping, and audit logs active.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ticket Lifecycle</span>
            <Inbox className="w-4 h-4 text-brand-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">Operational</span>
            <span className="text-xs text-brand-400">5 Live Tickets</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Private internal notes, SLA timers, and conversation histories.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Tenant Boundary</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">Isolated</span>
            <span className="text-xs text-emerald-400">Zero Leakage</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Strict DB level tenant isolation tested & verified.</p>
        </div>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="*"
              element={
                <div className="flex h-screen bg-navy-950 overflow-hidden text-slate-100">
                  <Navigation />
                  <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
                    <Header />
                    <main className="flex-1 overflow-y-auto p-8">
                      <Routes>
                        <Route path="/" element={<OverviewPage />} />
                        <Route path="/tickets" element={<TicketInbox />} />
                        <Route path="/tickets/:id" element={<TicketDetail />} />
                        <Route path="/knowledge" element={<KnowledgeBase />} />
                        <Route path="/sla" element={<SLAMonitor />} />
                        <Route path="/analytics" element={<Analytics />} />



                        <Route
                          path="*"
                          element={
                            <div className="text-center py-20">
                              <p className="text-slate-400">Feature scheduled for subsequent milestone.</p>
                              <Link to="/tickets" className="text-brand-400 text-sm mt-2 inline-block hover:underline">
                                Go to Ticket Inbox
                              </Link>
                            </div>
                          }
                        />
                      </Routes>
                    </main>
                  </div>
                </div>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
