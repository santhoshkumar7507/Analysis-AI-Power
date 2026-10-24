import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import {
  ArrowLeft,
  Clock,
  Send,
  Lock,
  CheckCircle,
  Sparkles,
  ShieldCheck,
  FileCheck,
  Check,
  Edit3,
} from "lucide-react";


interface TicketMessage {
  id: string;
  sender_type: string;
  sender_name?: string;
  body: string;
  is_internal_note: boolean;
  created_at: string;
}

interface TicketDetail {
  id: string;
  reference_number: string;
  customer_name: string;
  customer_email: string;
  subject: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  channel: string;
  assigned_agent_id?: string;
  assigned_agent_name?: string;
  assigned_team_id?: string;
  assigned_team_name?: string;
  first_response_deadline?: string;
  resolution_deadline?: string;
  first_responded_at?: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
  messages: TicketMessage[];
}

interface AIAnalysis {
  category: string;
  priority: string;
  sentiment: string;
  issue_summary: string;
  suggested_team_name?: string;
  recommended_action: string;
  confidence_score: number;
  model_provider: string;
}

interface AICopilotDraft {
  id: string;
  suggested_reply: string;
  reasoning: string;
  citations: Array<{ chunk_id: string; document_title: string; citation: string }>;
  status: string;
  is_grounded: boolean;
}

export const TicketDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [replyBody, setReplyBody] = useState("");
  const [isInternalNote, setIsInternalNote] = useState(false);
  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [editedDraftText, setEditedDraftText] = useState("");

  // Ticket data
  const { data: ticket, isLoading, isError } = useQuery<TicketDetail>({
    queryKey: ["ticket", id],
    queryFn: async () => {
      const res = await apiClient.get(`/tickets/${id}`);
      return res.data;
    },
    refetchInterval: 8000,
  });

  // AI Analysis
  const { data: aiAnalysis } = useQuery<AIAnalysis>({
    queryKey: ["ticket-ai-analysis", id],
    queryFn: async () => {
      const res = await apiClient.get(`/tickets/${id}/ai-analysis`);
      return res.data;
    },
    enabled: !!id,
  });

  // Active Copilot Draft
  const { data: draftData } = useQuery<{ draft: AICopilotDraft | null }>({
    queryKey: ["ticket-copilot-draft", id],

    queryFn: async () => {
      const res = await apiClient.get(`/tickets/${id}/copilot/draft`);
      return res.data;
    },
    enabled: !!id,
  });

  const activeDraft = draftData?.draft;

  // Mutations
  const messageMutation = useMutation({
    mutationFn: async ({ body, is_internal_note }: { body: string; is_internal_note: boolean }) => {
      const res = await apiClient.post(`/tickets/${id}/messages`, { body, is_internal_note });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
      setReplyBody("");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (status: string) => {
      const res = await apiClient.patch(`/tickets/${id}`, { status });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });

  const generateDraftMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/tickets/${id}/copilot/generate`);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["ticket-copilot-draft", id] });
      setEditedDraftText(data.suggested_reply);
    },
  });

  const approveDraftMutation = useMutation({
    mutationFn: async (payload: { edited_reply?: string }) => {
      const res = await apiClient.post(`/tickets/${id}/copilot/approve`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      queryClient.invalidateQueries({ queryKey: ["ticket-copilot-draft", id] });
      setIsEditingDraft(false);
    },
  });

  const rejectDraftMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/tickets/${id}/copilot/reject`, {
        rejection_reason: "Agent requested regeneration or alternate approach.",
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticket-copilot-draft", id] });
    },
  });

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyBody.trim()) return;
    messageMutation.mutate({ body: replyBody, is_internal_note: isInternalNote });
  };

  if (isLoading) {
    return <div className="p-12 text-center text-slate-400">Loading ticket details...</div>;
  }

  if (isError || !ticket) {
    return (
      <div className="p-12 text-center text-rose-400">
        <p>Ticket not found or inaccessible.</p>
        <Link to="/tickets" className="text-brand-400 text-sm mt-2 inline-block hover:underline">
          Return to Inbox
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-navy-700">
        <div className="flex items-center gap-3">
          <Link
            to="/tickets"
            className="p-2 bg-navy-850 hover:bg-navy-800 text-slate-400 hover:text-white rounded-lg border border-navy-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-brand-400">
                {ticket.reference_number}
              </span>
              <span className="text-xs px-2.5 py-0.5 rounded-full capitalize bg-navy-800 text-slate-300 border border-navy-700">
                {ticket.category}
              </span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase ${
                  ticket.priority === "critical"
                    ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                    : ticket.priority === "high"
                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                    : "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                }`}
              >
                {ticket.priority}
              </span>
            </div>
            <h1 className="text-xl font-bold text-white mt-1">{ticket.subject}</h1>
          </div>
        </div>

        {/* Status Transition Control */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-400 uppercase">Status:</label>
          <select
            value={ticket.status}
            onChange={(e) => statusMutation.mutate(e.target.value)}
            disabled={statusMutation.isPending}
            className="px-3 py-1.5 bg-navy-850 border border-navy-700 rounded-lg text-xs font-semibold text-slate-200 focus:outline-none focus:border-brand-500"
          >
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting_customer">Waiting for Customer</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Conversation Feed & AI Copilot Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Columns: Conversation Timeline */}
        <div className="lg:col-span-7 space-y-5">
          {/* Messages Feed */}
          <div className="space-y-4">
            {ticket.messages.map((m) => {
              const isCustomer = m.sender_type === "customer";
              const isInternal = m.is_internal_note;

              return (
                <div
                  key={m.id}
                  className={`rounded-xl p-4 border transition-all ${
                    isInternal
                      ? "bg-amber-500/5 border-amber-500/30 text-amber-200"
                      : isCustomer
                      ? "bg-navy-850 border-navy-700 text-slate-200"
                      : "bg-brand-950/40 border-brand-500/30 text-slate-200"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2 pb-2 border-b border-navy-700/60">
                    <div className="flex items-center gap-2">
                      {isInternal ? (
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                          <Lock className="w-3.5 h-3.5" />
                          Internal Team Note (Private)
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                              isCustomer
                                ? "bg-slate-700 text-slate-300"
                                : "bg-brand-600 text-white"
                            }`}
                          >
                            {isCustomer ? "C" : "A"}
                          </div>
                          <span className="text-xs font-bold text-slate-300">
                            {m.sender_name || (isCustomer ? ticket.customer_name : "Support Agent")}
                          </span>
                        </div>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {new Date(m.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-sm whitespace-pre-wrap leading-relaxed text-slate-300">
                    {m.body}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Reply Box */}
          <div className="bg-navy-850 border border-navy-700 rounded-xl p-4 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-300">Compose Response</span>
              <button
                type="button"
                onClick={() => setIsInternalNote(!isInternalNote)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  isInternalNote
                    ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                    : "bg-navy-900 text-slate-400 border-navy-700 hover:text-slate-200"
                }`}
              >
                <Lock className="w-3 h-3" />
                {isInternalNote ? "Internal Note Active" : "Make Internal Note"}
              </button>
            </div>

            <form onSubmit={handleSendMessage} className="space-y-3">
              <textarea
                rows={4}
                placeholder={
                  isInternalNote
                    ? "Write private internal note (visible only to agents)..."
                    : "Write customer-facing reply..."
                }
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                className={`w-full p-3 bg-navy-900 border rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none transition-colors ${
                  isInternalNote ? "border-amber-500/40 focus:border-amber-400" : "border-navy-700 focus:border-brand-500"
                }`}
              />

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  {isInternalNote
                    ? "Internal notes will not notify the customer."
                    : "This message will be sent to the customer."}
                </span>

                <button
                  type="submit"
                  disabled={messageMutation.isPending || !replyBody.trim()}
                  className={`inline-flex items-center gap-2 px-4 py-2 text-white text-sm font-medium rounded-lg shadow-md transition-colors ${
                    isInternalNote
                      ? "bg-amber-600 hover:bg-amber-500 shadow-amber-600/20"
                      : "bg-brand-600 hover:bg-brand-500 shadow-brand-600/20"
                  }`}
                >
                  <Send className="w-4 h-4" />
                  {messageMutation.isPending ? "Sending..." : isInternalNote ? "Post Note" : "Send Reply"}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right 5 Columns: AI Copilot Panel & Ticket Metadata */}
        <div className="lg:col-span-5 space-y-5">
          {/* AI Ticket Intelligence Card */}
          <div className="bg-gradient-to-b from-navy-850 to-navy-900 border border-ai-500/30 rounded-xl p-5 shadow-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-ai-500/10 rounded-full blur-2xl pointer-events-none" />

            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-ai-500" />
                <h3 className="text-sm font-bold text-white tracking-wide">AI Ticket Intelligence</h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-ai-500/15 text-ai-500 border border-ai-500/30 font-semibold">
                {aiAnalysis?.model_provider || "AI Ready"}
              </span>
            </div>

            {aiAnalysis ? (
              <div className="space-y-3 text-xs">
                <div className="p-2.5 bg-navy-950/70 rounded-lg border border-navy-800">
                  <span className="text-slate-400 block mb-1">Issue Summary</span>
                  <p className="text-slate-200 font-medium leading-relaxed">{aiAnalysis.issue_summary}</p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 bg-navy-950/70 rounded-lg border border-navy-800">
                    <span className="text-slate-400 block">Customer Sentiment</span>
                    <span
                      className={`font-semibold capitalize ${
                        aiAnalysis.sentiment === "urgent"
                          ? "text-rose-400"
                          : aiAnalysis.sentiment === "negative"
                          ? "text-amber-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {aiAnalysis.sentiment}
                    </span>
                  </div>

                  <div className="p-2.5 bg-navy-950/70 rounded-lg border border-navy-800">
                    <span className="text-slate-400 block">AI Confidence</span>
                    <span className="font-semibold text-brand-400 font-mono">
                      {(aiAnalysis.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div className="p-2.5 bg-navy-950/70 rounded-lg border border-navy-800">
                  <span className="text-slate-400 block mb-1">Recommended Next Action</span>
                  <p className="text-brand-300 font-medium">{aiAnalysis.recommended_action}</p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">Analyzing ticket semantics...</p>
            )}
          </div>

          {/* AI Grounded Reply Copilot Card */}
          <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileCheck className="w-4 h-4 text-emerald-400" />
                Grounded Reply Copilot
              </h3>

              {!activeDraft && (
                <button
                  type="button"
                  onClick={() => generateDraftMutation.mutate()}
                  disabled={generateDraftMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-3 py-1 bg-ai-600 hover:bg-ai-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-ai-500/20 transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {generateDraftMutation.isPending ? "Retrieving & Drafting..." : "Generate Grounded Draft"}
                </button>
              )}
            </div>

            {activeDraft && activeDraft.status === "draft" ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" /> Verified Grounded Draft
                  </span>
                  <button
                    onClick={() => {
                      setIsEditingDraft(!isEditingDraft);
                      setEditedDraftText(activeDraft.suggested_reply);
                    }}
                    className="text-slate-400 hover:text-brand-400 text-[11px] flex items-center gap-1"
                  >
                    <Edit3 className="w-3 h-3" />
                    {isEditingDraft ? "Cancel Edit" : "Edit Draft"}
                  </button>
                </div>

                {isEditingDraft ? (
                  <textarea
                    rows={6}
                    value={editedDraftText}
                    onChange={(e) => setEditedDraftText(e.target.value)}
                    className="w-full p-2.5 bg-navy-900 border border-brand-500/40 rounded-lg text-xs text-slate-200 focus:outline-none"
                  />
                ) : (
                  <div className="p-3 bg-navy-900 rounded-lg border border-navy-700/80 text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                    {activeDraft.suggested_reply}
                  </div>
                )}

                {/* Supporting Citations */}
                {activeDraft.citations && activeDraft.citations.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Supporting Citations:
                    </span>
                    <div className="space-y-1">
                      {activeDraft.citations.map((c, idx) => (
                        <div
                          key={idx}
                          className="px-2.5 py-1 rounded bg-navy-950 border border-navy-800 text-[11px] font-mono text-slate-300 flex items-center justify-between"
                        >
                          <span className="truncate max-w-[240px] text-brand-400">{c.citation}</span>
                          <span className="text-emerald-400 font-semibold text-[10px]">Verified</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Human Approval Action Buttons */}
                <div className="pt-2 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => rejectDraftMutation.mutate()}
                    disabled={rejectDraftMutation.isPending}
                    className="px-3 py-1.5 bg-navy-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 border border-navy-700 rounded-lg text-xs font-medium transition-colors"
                  >
                    Discard Draft
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      approveDraftMutation.mutate(
                        isEditingDraft ? { edited_reply: editedDraftText } : {}
                      )
                    }
                    disabled={approveDraftMutation.isPending}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-emerald-600/20 transition-colors"
                  >
                    <Check className="w-3.5 h-3.5" />
                    {approveDraftMutation.isPending ? "Approving..." : isEditingDraft ? "Approve Edited Draft" : "Approve & Send to Customer"}
                  </button>
                </div>
              </div>
            ) : activeDraft && activeDraft.status !== "draft" ? (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 shrink-0" />
                <span>
                  Previous draft {activeDraft.status.replace("_", " ")} and dispatched into customer thread.
                </span>
              </div>
            ) : (
              <p className="text-xs text-slate-400 leading-relaxed">
                Click "Generate Grounded Draft" to retrieve relevant knowledge base evidence and synthesize an approved reply.
              </p>
            )}
          </div>

          {/* SLA Tracking Card */}
          <div className="bg-navy-850 border border-navy-700 rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-brand-400" />
              SLA Tracking
            </h3>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-navy-900 rounded-lg border border-navy-700/60">
                <div className="flex items-center justify-between text-slate-400">
                  <span>First Response</span>
                  {ticket.first_responded_at ? (
                    <span className="text-emerald-400 font-semibold flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" /> Met
                    </span>
                  ) : (
                    <span className="text-amber-400 font-semibold">Active</span>
                  )}
                </div>
                <div className="font-mono text-slate-300 text-xs mt-1">
                  {ticket.first_response_deadline
                    ? new Date(ticket.first_response_deadline).toLocaleString()
                    : "Not set"}
                </div>
              </div>

              <div className="p-3 bg-navy-900 rounded-lg border border-navy-700/60">
                <div className="flex items-center justify-between text-slate-400">
                  <span>Resolution Target</span>
                  {ticket.resolved_at ? (
                    <span className="text-emerald-400 font-semibold flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" /> Resolved
                    </span>
                  ) : (
                    <span className="text-brand-400 font-semibold">In Progress</span>
                  )}
                </div>
                <div className="font-mono text-slate-300 text-xs mt-1">
                  {ticket.resolution_deadline
                    ? new Date(ticket.resolution_deadline).toLocaleString()
                    : "Not set"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
