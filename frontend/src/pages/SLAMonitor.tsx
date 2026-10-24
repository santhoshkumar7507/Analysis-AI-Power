import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import {
  Clock,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Play,
  Sliders,
  ChevronRight,
} from "lucide-react";


interface SLAPolicy {
  id: string;
  priority: string;
  first_response_minutes: number;
  resolution_minutes: number;
  is_active: boolean;
}

interface TicketItem {
  id: string;
  reference_number: string;
  customer_name: string;
  subject: string;
  priority: string;
  status: string;
  first_response_deadline?: string;
  resolution_deadline?: string;
  first_responded_at?: string;
  resolved_at?: string;
  created_at: string;
}

export const SLAMonitor: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedPriority, setSelectedPriority] = useState<string>("critical");
  const [firstRespMins, setFirstRespMins] = useState<number>(60);
  const [resMins, setResMins] = useState<number>(240);
  const [evalResult, setEvalResult] = useState<string | null>(null);

  // Policies query
  const { data: policies = [] } = useQuery<SLAPolicy[]>({
    queryKey: ["sla-policies"],
    queryFn: async () => {
      const res = await apiClient.get("/sla/policies");
      return res.data;
    },
  });

  // Active tickets query
  const { data: ticketData } = useQuery<{ items: TicketItem[]; total: number }>({
    queryKey: ["tickets-sla-monitor"],
    queryFn: async () => {
      const res = await apiClient.get("/tickets?limit=50");
      return res.data;
    },
    refetchInterval: 8000,
  });

  // Evaluate SLA Mutation
  const evalMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/sla/evaluate");
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["tickets-sla-monitor"] });
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
      setEvalResult(
        `Evaluation complete: ${data.active_tickets_evaluated} evaluated, ${data.warnings_triggered} warnings, ${data.breaches_triggered} breaches.`
      );
    },
  });

  // Update Policy Mutation
  const updatePolicyMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.put("/sla/policies", {
        priority: selectedPriority,
        first_response_minutes: Number(firstRespMins),
        resolution_minutes: Number(resMins),
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sla-policies"] });
    },
  });

  const tickets = ticketData?.items || [];
  const now = new Date();

  // Metrics computation
  let totalActive = 0;
  let warningCount = 0;
  let breachCount = 0;
  let metCount = 0;

  tickets.forEach((t) => {
    if (t.status === "resolved" || t.status === "closed") {
      metCount++;
      return;
    }
    totalActive++;

    if (t.first_response_deadline && !t.first_responded_at) {
      const deadline = new Date(t.first_response_deadline);
      const diffMins = (deadline.getTime() - now.getTime()) / (1000 * 60);
      if (diffMins <= 0) {
        breachCount++;
      } else if (diffMins <= 30) {
        warningCount++;
      }
    }
  });

  const totalEvaluated = totalActive + metCount;
  const complianceRate = totalEvaluated > 0 ? (((totalEvaluated - breachCount) / totalEvaluated) * 100).toFixed(1) : "100.0";

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Clock className="w-6 h-6 text-brand-400" />
            SLA & Escalation Monitoring Engine
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Real-time tracking of first-response and resolution deadlines with automated manager escalation.
          </p>
        </div>

        <button
          onClick={() => evalMutation.mutate()}
          disabled={evalMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg shadow-lg shadow-brand-600/20 transition-colors"
        >
          <Play className="w-4 h-4" />
          {evalMutation.isPending ? "Evaluating..." : "Run Evaluation Cycle"}
        </button>
      </div>

      {evalResult && (
        <div className="p-3 bg-brand-500/10 border border-brand-500/30 rounded-lg text-xs text-brand-300 flex items-center justify-between">
          <span>{evalResult}</span>
          <button onClick={() => setEvalResult(null)} className="text-slate-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            SLA Compliance Rate
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{complianceRate}%</span>
            <span className="text-xs text-emerald-400 font-semibold">Active Target: 95%</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Calculated from persisted ticket events.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            Active Tickets Monitored
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-brand-400">{totalActive}</span>
            <span className="text-xs text-slate-400 font-medium">Under SLA</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Open and in-progress inquiries.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            At Risk (Warning)
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-400">{warningCount}</span>
            <span className="text-xs text-amber-400 font-medium">&lt; 30 mins left</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Requires immediate agent response.</p>
        </div>

        <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            Breached Deadlines
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-rose-400">{breachCount}</span>
            <span className="text-xs text-rose-400 font-medium">Escalated</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Auto-routed to support managers.</p>
        </div>
      </div>

      {/* Main SLA Tracking Table */}
      <div className="bg-navy-850 border border-navy-700 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-navy-700/60 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Clock className="w-4 h-4 text-brand-400" />
            Live SLA Countdown Table ({tickets.length} tickets)
          </h3>
          <span className="text-xs text-slate-500">Scheduled checks run every 60s via Celery Beat</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-navy-900/60 border-b border-navy-700 text-xs text-slate-400 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-6 py-3.5">Reference & Customer</th>
                <th className="px-6 py-3.5">Priority</th>
                <th className="px-6 py-3.5">First Response Status</th>
                <th className="px-6 py-3.5">Resolution Target</th>
                <th className="px-6 py-3.5">SLA Health</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-700/60">
              {tickets.map((t) => {
                const isResolved = t.status === "resolved" || t.status === "closed";
                let isBreached = false;
                let isWarning = false;
                let remainingMins = 0;

                if (!isResolved && t.first_response_deadline && !t.first_responded_at) {
                  const deadline = new Date(t.first_response_deadline);
                  remainingMins = Math.round((deadline.getTime() - now.getTime()) / (1000 * 60));
                  if (remainingMins <= 0) isBreached = true;
                  else if (remainingMins <= 30) isWarning = true;
                }

                return (
                  <tr key={t.id} className="hover:bg-navy-800/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-mono font-medium text-brand-400">{t.reference_number}</div>
                      <div className="text-xs text-slate-300 font-medium truncate max-w-[220px]">
                        {t.subject}
                      </div>
                      <div className="text-[11px] text-slate-500">{t.customer_name}</div>
                    </td>

                    <td className="px-6 py-4">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase ${
                          t.priority === "critical"
                            ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                            : t.priority === "high"
                            ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                            : "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                        }`}
                      >
                        {t.priority}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-xs font-mono">
                      {t.first_responded_at ? (
                        <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Met
                        </span>
                      ) : isBreached ? (
                        <span className="text-rose-400 font-bold flex items-center gap-1">
                          <ShieldAlert className="w-3.5 h-3.5" /> Breached ({Math.abs(remainingMins)}m ago)
                        </span>
                      ) : isWarning ? (
                        <span className="text-amber-400 font-bold flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" /> {remainingMins}m remaining
                        </span>
                      ) : (
                        <span className="text-slate-300 font-medium">
                          {remainingMins > 0 ? `${remainingMins}m remaining` : "Active"}
                        </span>
                      )}
                    </td>

                    <td className="px-6 py-4 text-xs font-mono text-slate-400">
                      {t.resolution_deadline
                        ? new Date(t.resolution_deadline).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                        : "N/A"}
                    </td>

                    <td className="px-6 py-4">
                      {isResolved ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                          Complete
                        </span>
                      ) : isBreached ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/40 animate-pulse">
                          Escalated
                        </span>
                      ) : isWarning ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/40">
                          At Risk
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/30">
                          Healthy
                        </span>
                      )}
                    </td>

                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/tickets/${t.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-brand-600 text-xs font-medium text-slate-300 hover:text-white transition-colors"
                      >
                        Triage
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* SLA Policy Threshold Configuration */}
      <div className="bg-navy-850 border border-navy-700 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-navy-700/60">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sliders className="w-5 h-5 text-brand-400" />
              SLA Policy Thresholds
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Configure maximum first-response and resolution minutes by ticket priority.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {policies.map((p) => (
            <div
              key={p.id}
              className={`p-4 rounded-xl border transition-all ${
                selectedPriority === p.priority
                  ? "bg-navy-900 border-brand-500 shadow-md shadow-brand-500/10"
                  : "bg-navy-900/50 border-navy-800"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  {p.priority}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedPriority(p.priority);
                    setFirstRespMins(p.first_response_minutes);
                    setResMins(p.resolution_minutes);
                  }}
                  className="text-xs text-brand-400 hover:underline"
                >
                  Edit
                </button>
              </div>
              <div className="text-xs text-slate-400 space-y-1">
                <div>First Response: <span className="font-mono text-slate-200 font-semibold">{p.first_response_minutes}m</span></div>
                <div>Resolution: <span className="font-mono text-slate-200 font-semibold">{p.resolution_minutes}m</span></div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Edit Form */}
        <div className="p-4 bg-navy-900 rounded-xl border border-navy-700/60 flex flex-wrap items-center gap-4">
          <span className="text-xs font-semibold text-slate-300 capitalize">
            Editing {selectedPriority} Thresholds:
          </span>

          <div className="flex items-center gap-2 text-xs">
            <label className="text-slate-400">First Response (mins):</label>
            <input
              type="number"
              value={firstRespMins}
              onChange={(e) => setFirstRespMins(Number(e.target.value))}
              className="w-20 px-2 py-1 bg-navy-950 border border-navy-700 rounded text-slate-200 font-mono text-xs"
            />
          </div>

          <div className="flex items-center gap-2 text-xs">
            <label className="text-slate-400">Resolution (mins):</label>
            <input
              type="number"
              value={resMins}
              onChange={(e) => setResMins(Number(e.target.value))}
              className="w-24 px-2 py-1 bg-navy-950 border border-navy-700 rounded text-slate-200 font-mono text-xs"
            />
          </div>

          <button
            type="button"
            onClick={() => updatePolicyMutation.mutate()}
            disabled={updatePolicyMutation.isPending}
            className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded text-xs font-semibold"
          >
            {updatePolicyMutation.isPending ? "Saving..." : "Save Policy"}
          </button>
        </div>
      </div>
    </div>
  );
};
