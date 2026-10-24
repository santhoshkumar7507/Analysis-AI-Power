import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import {
  BookOpen,
  Upload,
  Search,
  Trash2,
  Sparkles,
  Layers,
  CheckCircle2,
  X,
} from "lucide-react";


interface KnowledgeDoc {
  id: string;
  title: string;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  error_message?: string;
  created_at: string;
}

interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_title: string;
  chunk_index: number;
  content: string;
  metadata: { section?: string; page?: number };
  similarity_score: number;
  citation: string;
}

export const KnowledgeBase: React.FC = () => {
  const queryClient = useQueryClient();
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);

  // Search playground state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const { data: docs = [], isLoading } = useQuery<KnowledgeDoc[]>({
    queryKey: ["knowledge-docs"],
    queryFn: async () => {
      const res = await apiClient.get("/knowledge/documents");
      return res.data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file || !title) return;
      const formData = new FormData();
      formData.append("title", title);
      formData.append("file", file);

      const res = await apiClient.post("/knowledge/documents", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-docs"] });
      setIsUploadOpen(false);
      setTitle("");
      setFile(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (docId: string) => {
      await apiClient.delete(`/knowledge/documents/${docId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-docs"] });
      setSearchResults([]);
    },
  });

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await apiClient.post("/knowledge/search", {
        query: searchQuery,
        top_k: 4,
        threshold: 0.35,
      });
      setSearchResults(res.data.results || []);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <BookOpen className="w-6 h-6 text-brand-400" />
            Knowledge Base & Semantic Vector Index
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Index policy documents, SOPs, and FAQs into vector embeddings for grounded AI Copilot replies.
          </p>
        </div>

        <button
          onClick={() => setIsUploadOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg shadow-lg shadow-brand-600/20 transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload Document
        </button>
      </div>

      {/* Indexed Documents Table */}
      <div className="bg-navy-850 border border-navy-700 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-navy-700/60 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand-400" />
            Indexed Knowledge Sources ({docs.length})
          </h3>
          <span className="text-xs text-slate-500">PostgreSQL pgvector / 384-dim embeddings</span>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Loading knowledge documents...</div>
        ) : docs.length === 0 ? (
          <div className="p-10 text-center text-slate-400">
            <BookOpen className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <p className="text-sm">No knowledge documents indexed yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-navy-900/60 border-b border-navy-700 text-xs text-slate-400 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="px-6 py-3.5">Document Title</th>
                  <th className="px-6 py-3.5">Format</th>
                  <th className="px-6 py-3.5">Size</th>
                  <th className="px-6 py-3.5">Vector Chunks</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700/60">
                {docs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-navy-800/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-200">{doc.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        Added: {new Date(doc.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-0.5 uppercase font-mono text-xs font-semibold bg-navy-900 border border-navy-700 rounded text-brand-400">
                        {doc.file_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {(doc.file_size / 1024).toFixed(1)} KB
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-500/15 text-brand-400 border border-brand-500/30">
                        {doc.chunk_count} chunks
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Indexed
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => deleteMutation.mutate(doc.id)}
                        disabled={deleteMutation.isPending}
                        title="Delete document and vector chunks"
                        className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-navy-800 rounded transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Semantic Vector Search Playground */}
      <div className="bg-navy-850 border border-navy-700 rounded-xl p-6 shadow-sm space-y-5">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-ai-500" />
            Semantic Vector Retrieval Playground
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Test natural language queries against your indexed vector chunks and verify similarity scores and citations.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="e.g. What is our refund policy on double charges?"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching || !searchQuery.trim()}
            className="px-5 py-2.5 bg-ai-600 hover:bg-ai-500 text-white rounded-lg text-sm font-semibold shadow-md shadow-ai-500/20 transition-colors"
          >
            {isSearching ? "Searching..." : "Vector Search"}
          </button>
        </form>

        {/* Quick Test Queries */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-500">Try quick query:</span>
          <button
            type="button"
            onClick={() => setSearchQuery("How to handle duplicate charges and refund timelines?")}
            className="px-2.5 py-1 bg-navy-900 hover:bg-navy-800 border border-navy-700 rounded text-slate-300"
          >
            Refund Timelines
          </button>
          <button
            type="button"
            onClick={() => setSearchQuery("Resolving HTTP 504 gateway timeouts on REST API")}
            className="px-2.5 py-1 bg-navy-900 hover:bg-navy-800 border border-navy-700 rounded text-slate-300"
          >
            API 504 Timeouts
          </button>
          <button
            type="button"
            onClick={() => setSearchQuery("Customer locked out of account and missing 2FA code")}
            className="px-2.5 py-1 bg-navy-900 hover:bg-navy-800 border border-navy-700 rounded text-slate-300"
          >
            2FA Lockout
          </button>
        </div>

        {/* Search Results Display */}
        {searchResults.length > 0 && (
          <div className="space-y-3 pt-3 border-t border-navy-700/60">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
              Retrieved Grounded Chunks ({searchResults.length})
            </span>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {searchResults.map((result) => (
                <div
                  key={result.chunk_id}
                  className="p-4 bg-navy-900 rounded-xl border border-navy-700/80 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-brand-400 truncate max-w-[200px]">
                      {result.document_title}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      {(result.similarity_score * 100).toFixed(1)}% Match
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed italic bg-navy-950 p-2.5 rounded border border-navy-800">
                    "{result.content}"
                  </p>

                  <div className="pt-2 border-t border-navy-800 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Citation:</span>
                    <span className="font-mono text-slate-400">{result.citation}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-navy-850 border border-navy-700 rounded-xl w-full max-w-lg shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-navy-700 mb-5">
              <h3 className="text-lg font-bold text-white">Upload Knowledge Document</h3>
              <button
                onClick={() => setIsUploadOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                uploadMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                  Document Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Enterprise SLA Guidelines"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                  Select File (.pdf, .docx, .txt, .md, .json)
                </label>
                <input
                  type="file"
                  required
                  accept=".pdf,.docx,.txt,.md,.json"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full px-3.5 py-2 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-300 focus:outline-none file:mr-3 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-brand-600 file:text-white"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Max file size: 15 MB. Text will be chunked into 384-dimensional dense embeddings.
                </span>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-navy-700">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 bg-navy-800 text-slate-300 hover:text-white rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadMutation.isPending || !file || !title}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium shadow-md shadow-brand-500/20"
                >
                  {uploadMutation.isPending ? "Indexing..." : "Upload & Index"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
