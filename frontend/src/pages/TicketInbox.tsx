import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import {
  Inbox,
  Search,
  Plus,
  UserCheck,
  ChevronRight,
  X,
} from "lucide-react";


interface TicketItem {
  id: string;
  reference_number: string;
  customer_name: string;
  customer_email: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
  channel: string;
  assigned_agent_name?: string;
  assigned_team_name?: string;
  first_response_deadline?: string;
  resolution_deadline?: string;
  created_at: string;
}

export const TicketInbox: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);

  // New ticket form state
  const [formData, setFormData] = useState({
    customer_name: "",
    customer_email: "",
    subject: "",
    description: "",
    category: "general",
    priority: "medium",
  });

  const { data, isLoading, isError } = useQuery<{ items: TicketItem[]; total: number }>({
    queryKey: ["tickets", statusFilter, priorityFilter, categoryFilter, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      if (priorityFilter) params.append("priority", priorityFilter);
      if (categoryFilter) params.append("category", categoryFilter);
      if (search) params.append("search", search);

      const res = await apiClient.get(`/tickets?${params.toString()}`);
      return res.data;
    },
    refetchInterval: 10000,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: typeof formData) => {
      const res = await apiClient.post("/tickets", payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
      setIsCreateOpen(false);
      setFormData({
        customer_name: "",
        customer_email: "",
        subject: "",
        description: "",
        category: "general",
        priority: "medium",
      });
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "critical":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">Critical</span>;
      case "high":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">High</span>;
      case "medium":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">Medium</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-500/15 text-slate-400 border border-slate-500/30">Low</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "open":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Open</span>;
      case "in_progress":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-brand-500/10 text-brand-400 border border-brand-500/20">In Progress</span>;
      case "waiting_customer":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">Waiting Customer</span>;
      case "resolved":
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">Resolved</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Inbox className="w-6 h-6 text-brand-400" />
            Support Ticket Inbox
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Manage, triage, and resolve multi-channel customer inquiries.
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg shadow-lg shadow-brand-600/20 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Ticket
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-navy-850 border border-navy-700 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search tickets by subject, customer, or RES-#..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-navy-900 border border-navy-700 rounded-lg text-xs font-medium text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting_customer">Waiting for Customer</option>
            <option value="resolved">Resolved</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-3 py-2 bg-navy-900 border border-navy-700 rounded-lg text-xs font-medium text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 bg-navy-900 border border-navy-700 rounded-lg text-xs font-medium text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="">All Categories</option>
            <option value="billing">Billing</option>
            <option value="refunds">Refunds</option>
            <option value="technical">Technical</option>
            <option value="account">Account</option>
            <option value="orders">Orders</option>
            <option value="general">General</option>
          </select>
        </div>
      </div>

      {/* Tickets Table */}
      <div className="bg-navy-850 border border-navy-700 rounded-xl overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400">Loading tickets...</div>
        ) : isError ? (
          <div className="p-12 text-center text-rose-400">Failed to load tickets. Please check connection.</div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Inbox className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <p className="text-sm">No tickets found matching the selected filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-navy-900/60 border-b border-navy-700 text-xs text-slate-400 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-6 py-3.5">Reference</th>
                  <th className="px-6 py-3.5">Customer & Subject</th>
                  <th className="px-6 py-3.5">Category</th>
                  <th className="px-6 py-3.5">Priority</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Assigned Agent</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700/60">
                {data?.items.map((ticket) => (
                  <tr key={ticket.id} className="hover:bg-navy-800/40 transition-colors group">
                    <td className="px-6 py-4 font-mono font-medium text-brand-400">
                      {ticket.reference_number}
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-200 group-hover:text-brand-300 transition-colors">
                        {ticket.subject}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {ticket.customer_name} ({ticket.customer_email})
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs capitalize text-slate-400 font-medium">
                      {ticket.category}
                    </td>
                    <td className="px-6 py-4">{getPriorityBadge(ticket.priority)}</td>
                    <td className="px-6 py-4">{getStatusBadge(ticket.status)}</td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {ticket.assigned_agent_name ? (
                        <span className="flex items-center gap-1.5 text-slate-300">
                          <UserCheck className="w-3.5 h-3.5 text-brand-400" />
                          {ticket.assigned_agent_name}
                        </span>
                      ) : (
                        <span className="text-slate-500 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/tickets/${ticket.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-brand-600 text-xs font-medium text-slate-300 hover:text-white transition-colors"
                      >
                        View
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Ticket Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-navy-850 border border-navy-700 rounded-xl w-full max-w-lg shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-navy-700 mb-5">
              <h3 className="text-lg font-bold text-white">Create New Customer Ticket</h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                  Customer Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Jane Doe"
                  value={formData.customer_name}
                  onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                  className="w-full px-3.5 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                  Customer Email
                </label>
                <input
                  type="email"
                  required
                  placeholder="customer@domain.com"
                  value={formData.customer_email}
                  onChange={(e) => setFormData({ ...formData, customer_email: e.target.value })}
                  className="w-full px-3.5 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                    Category
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                  >
                    <option value="general">General</option>
                    <option value="billing">Billing</option>
                    <option value="refunds">Refunds</option>
                    <option value="technical">Technical</option>
                    <option value="account">Account</option>
                    <option value="orders">Orders</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                    Priority
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    className="w-full px-3 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                  Subject
                </label>
                <input
                  type="text"
                  required
                  placeholder="Brief summary of the issue"
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  className="w-full px-3.5 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                  Problem Description
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Detailed customer message..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3.5 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-navy-700">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 bg-navy-800 text-slate-300 hover:text-white rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium shadow-md shadow-brand-500/20"
                >
                  {createMutation.isPending ? "Creating..." : "Submit Ticket"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
