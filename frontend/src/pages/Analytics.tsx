import React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import {
  BarChart3,
  Download,
  Users,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";


interface AnalyticsOverview {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  waiting_customer_tickets: number;
  resolved_tickets: number;
  overdue_tickets: number;
  sla_compliance_rate: number;
  average_first_response_minutes: number;
  average_resolution_hours: number;
  category_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  agent_workload: Array<{
    agent_id: string;
    agent_name: string;
    role: string;
    active_tickets: number;
    resolved_tickets: number;
  }>;
  ai_classification_summary: {
    total_analyzed: number;
    average_confidence: number;
  };
}

interface AIEvaluationMetrics {
  benchmark_name: string;
  total_samples: number;
  accuracy_score: number;
  precision_score: number;
  recall_score: number;
  f1_score: number;
  priority_accuracy: number;
  avg_latency_ms: number;
  grounding_faithfulness: number;
}

export const Analytics: React.FC = () => {
  const { data: metrics, isLoading } = useQuery<AnalyticsOverview>({
    queryKey: ["analytics-overview"],
    queryFn: async () => {
      const res = await apiClient.get("/analytics/overview");
      return res.data;
    },
    refetchInterval: 15000,
  });

  const { data: aiMetrics } = useQuery<AIEvaluationMetrics>({
    queryKey: ["ai-performance"],
    queryFn: async () => {
      const res = await apiClient.get("/analytics/ai-performance");
      return res.data;
    },
  });

  const handleExportCSV = async () => {
    try {
      const res = await apiClient.get("/analytics/export", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `resolveai_tickets_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (e) {
      alert("Failed to export CSV. Please try again.");
    }
  };

  if (isLoading || !metrics) {
    return <div className="p-12 text-center text-slate-400">Loading performance analytics...</div>;
  }

  const categoryEntries = Object.entries(metrics.category_distribution || {});
  const priorityEntries = Object.entries(metrics.priority_distribution || {});
  const maxCategoryCount = Math.max(1, ...Object.values(metrics.category_distribution || {}));

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-brand-400" />
            Operational Analytics & AI Quality Intelligence
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Persisted metrics computed from real tickets, SLA timestamps, and AI benchmark evaluations.
          </p>
        </div>

        <button
          onClick={handleExportCSV}
          className="inline-flex items-center gap-2 px-4 py-2 bg-navy-800 hover:bg-navy-700 text-slate-200 hover:text-white text-sm font-medium rounded-lg border border-navy-700 shadow-sm transition-colors"
        >
          <Download className="w-4 h-4 text-brand-400" />
          Export Sanitized CSV
        </button>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            Total Tickets Ingested
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{metrics.total_tickets}</span>
            <span className="text-xs text-brand-400 font-semibold">{metrics.open_tickets} Open</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Across email, web, and API channels.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            Avg First Response Time
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-brand-400">
              {metrics.average_first_response_minutes}
            </span>
            <span className="text-xs text-slate-400 font-medium">Minutes</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Calculated from first agent message.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            Avg Resolution Time
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400">
              {metrics.average_resolution_hours}
            </span>
            <span className="text-xs text-slate-400 font-medium">Hours</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Strictly excludes unresolved tickets.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            SLA Compliance Rate
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{metrics.sla_compliance_rate}%</span>
            <span className="text-xs text-rose-400 font-semibold">{metrics.overdue_tickets} Overdue</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Target benchmark: &gt; 90% compliance.</p>
        </div>
      </div>

      {/* Distribution Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <div className="bg-navy-850 border border-navy-700 rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-400" />
            Ticket Volume by Category
          </h3>
          <div className="space-y-3 pt-2">
            {categoryEntries.map(([cat, count]) => {
              const pct = Math.round((count / maxCategoryCount) * 100);
              return (
                <div key={cat} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="capitalize text-slate-300 font-medium">{cat}</span>
                    <span className="font-mono text-slate-400">{count} tickets</span>
                  </div>
                  <div className="w-full bg-navy-900 rounded-full h-2 overflow-hidden border border-navy-800">
                    <div
                      className="bg-brand-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(8, pct)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Priority Breakdown */}
        <div className="bg-navy-850 border border-navy-700 rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            Ticket Volume by Urgency & Priority
          </h3>
          <div className="grid grid-cols-2 gap-3 pt-2">
            {priorityEntries.map(([pri, count]) => (
              <div key={pri} className="p-4 bg-navy-900 rounded-xl border border-navy-800/80">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-1">
                  {pri}
                </span>
                <span
                  className={`text-2xl font-extrabold ${
                    pri === "critical"
                      ? "text-rose-400"
                      : pri === "high"
                      ? "text-amber-400"
                      : pri === "medium"
                      ? "text-blue-400"
                      : "text-slate-300"
                  }`}
                >
                  {count}
                </span>
                <span className="text-[11px] text-slate-500 block mt-1">
                  {((count / (metrics.total_tickets || 1)) * 100).toFixed(0)}% of total volume
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AI Copilot Benchmark Quality Panel */}
      <div className="bg-gradient-to-b from-navy-850 to-navy-900 border border-ai-500/40 rounded-xl p-6 shadow-lg space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-navy-700/60">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-ai-500" />
              AI Quality & RAG Retrieval Evaluation Benchmark
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Measured against our curated, ground-truth labeled benchmark dataset ({aiMetrics?.total_samples || 10} scenarios).
            </p>
          </div>
          <span className="text-xs px-3 py-1 rounded-full bg-ai-500/15 text-ai-400 border border-ai-500/30 font-semibold font-mono">
            {aiMetrics?.benchmark_name || "Benchmark v1.0"}
          </span>
        </div>

        {aiMetrics && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3.5 bg-navy-950/70 rounded-xl border border-navy-800">
              <span className="text-[11px] text-slate-400 block mb-1">Accuracy</span>
              <span className="text-xl font-bold text-emerald-400 font-mono">
                {(aiMetrics.accuracy_score * 100).toFixed(1)}%
              </span>
            </div>

            <div className="p-3.5 bg-navy-950/70 rounded-xl border border-navy-800">
              <span className="text-[11px] text-slate-400 block mb-1">Macro Precision</span>
              <span className="text-xl font-bold text-brand-400 font-mono">
                {(aiMetrics.precision_score * 100).toFixed(1)}%
              </span>
            </div>

            <div className="p-3.5 bg-navy-950/70 rounded-xl border border-navy-800">
              <span className="text-[11px] text-slate-400 block mb-1">Macro Recall</span>
              <span className="text-xl font-bold text-blue-400 font-mono">
                {(aiMetrics.recall_score * 100).toFixed(1)}%
              </span>
            </div>

            <div className="p-3.5 bg-navy-950/70 rounded-xl border border-navy-800">
              <span className="text-[11px] text-slate-400 block mb-1">Macro F1 Score</span>
              <span className="text-xl font-bold text-ai-400 font-mono">
                {(aiMetrics.f1_score * 100).toFixed(1)}%
              </span>
            </div>

            <div className="p-3.5 bg-navy-950/70 rounded-xl border border-navy-800">
              <span className="text-[11px] text-slate-400 block mb-1">Faithfulness</span>
              <span className="text-xl font-bold text-emerald-400 font-mono">
                {(aiMetrics.grounding_faithfulness * 100).toFixed(1)}%
              </span>
            </div>

            <div className="p-3.5 bg-navy-950/70 rounded-xl border border-navy-800">
              <span className="text-[11px] text-slate-400 block mb-1">Avg Latency</span>
              <span className="text-xl font-bold text-amber-400 font-mono">
                {aiMetrics.avg_latency_ms} ms
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Support Agent Workload Table */}
      <div className="bg-navy-850 border border-navy-700 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-navy-700/60 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Users className="w-4 h-4 text-emerald-400" />
            Support Agent Workload & Allocation
          </h3>
          <span className="text-xs text-slate-500">Live active ticket counts</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-navy-900/60 border-b border-navy-700 text-xs text-slate-400 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-6 py-3.5">Agent Name</th>
                <th className="px-6 py-3.5">Role</th>
                <th className="px-6 py-3.5">Active Assigned</th>
                <th className="px-6 py-3.5">Resolved Lifetime</th>
                <th className="px-6 py-3.5">Capacity Load</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-700/60">
              {metrics.agent_workload.map((agent) => {
                const loadPct = Math.min(100, agent.active_tickets * 25);
                return (
                  <tr key={agent.agent_id} className="hover:bg-navy-800/40 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-200">
                      {agent.agent_name}
                    </td>
                    <td className="px-6 py-4 text-xs capitalize text-slate-400">
                      {agent.role.replace("_", " ")}
                    </td>
                    <td className="px-6 py-4 font-mono font-bold text-brand-400">
                      {agent.active_tickets}
                    </td>
                    <td className="px-6 py-4 font-mono text-slate-300">
                      {agent.resolved_tickets}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-navy-900 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${
                              loadPct > 75 ? "bg-rose-500" : loadPct > 50 ? "bg-amber-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${Math.max(10, loadPct)}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-slate-400">{loadPct}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
