import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Sparkles, Shield, User, ArrowRight } from "lucide-react";


export const Login: React.FC = () => {
  const { login, switchDemoRole } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@acme.com");
  const [password, setPassword] = useState("Password123!");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await login(email, password);
      navigate("/tickets");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid login credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickRole = async (role: "admin" | "manager" | "agent") => {
    setIsLoading(true);
    setError(null);
    try {
      await switchDemoRole(role);
      navigate("/tickets");
    } catch {
      setError("Failed to sign in with demo role.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center items-center p-6 text-slate-100">
      <div className="w-full max-w-md space-y-6">
        {/* Branding Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-brand-600 to-ai-500 mx-auto flex items-center justify-center shadow-xl shadow-brand-500/25">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">ResolveAI Platform</h1>
          <p className="text-xs text-slate-400">Enterprise AI Customer Support Automation</p>
        </div>

        {/* Login Box */}
        <div className="bg-navy-850 border border-navy-700 rounded-2xl p-6 shadow-2xl space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-navy-700/60">
            <span className="text-sm font-semibold text-slate-300">Sign in to your Workspace</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              Acme Global
            </span>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-navy-900 border border-navy-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-brand-500 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-semibold shadow-lg shadow-brand-600/20 flex items-center justify-center gap-2 transition-colors"
            >
              {isLoading ? "Signing in..." : "Enter Workspace"}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Sign-In */}
          <div className="pt-4 border-t border-navy-700/60 space-y-2">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block text-center">
              One-Click Role Demonstration
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickRole("admin")}
                className="p-2 bg-navy-900 hover:bg-navy-800 border border-navy-700 rounded-lg text-center transition-colors group"
              >
                <Shield className="w-4 h-4 text-emerald-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
                <span className="text-[11px] font-semibold text-slate-300 block">Admin</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickRole("manager")}
                className="p-2 bg-navy-900 hover:bg-navy-800 border border-navy-700 rounded-lg text-center transition-colors group"
              >
                <User className="w-4 h-4 text-brand-400 mx-auto mb-1 group-hover:scale-110 transition-transform" />
                <span className="text-[11px] font-semibold text-slate-300 block">Manager</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickRole("agent")}
                className="p-2 bg-navy-900 hover:bg-navy-800 border border-navy-700 rounded-lg text-center transition-colors group"
              >
                <User className="w-4 h-4 text-ai-500 mx-auto mb-1 group-hover:scale-110 transition-transform" />
                <span className="text-[11px] font-semibold text-slate-300 block">Agent</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
