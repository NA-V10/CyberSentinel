"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, User, Crown, Loader2 } from "lucide-react";
import Link from "next/link";

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRoleSelect(role: "admin" | "user") {
    setSelected(role);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/set-role", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) throw new Error("Failed to set role");
      router.push("/dashboard");
    } catch {
      setError("Something went wrong. Please try again.");
      setLoading(false);
      setSelected(null);
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center relative">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-100" />
      <div className="absolute top-1/4 right-1/3 w-96 h-96 bg-secondary/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

      {/* Logo */}
      <div className="relative z-10 mb-10 text-center">
        <Link href="/" className="inline-flex items-center gap-2 group">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 group-hover:border-primary/40 transition-colors">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <div className="text-left">
            <div className="text-xl font-bold text-foreground">
              CyberSentinel <span className="text-primary">AI</span>
            </div>
            <div className="text-xs text-muted-foreground">
              Security Intelligence Platform
            </div>
          </div>
        </Link>
      </div>

      {/* Role Selection Card */}
      <div className="relative z-10 w-full max-w-md px-4">
        <div className="bg-card border border-border rounded-xl shadow-[0_0_40px_rgba(0,212,255,0.05)] p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-foreground mb-2">
              Choose Your Role
            </h1>
            <p className="text-sm text-muted-foreground">
              Select your access level to continue
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* User Role */}
            <button
              onClick={() => handleRoleSelect("user")}
              disabled={loading}
              className={`flex flex-col items-center gap-3 p-6 rounded-lg border transition-all duration-200
                ${
                  selected === "user"
                    ? "border-primary bg-primary/10 shadow-[0_0_20px_rgba(0,212,255,0.15)]"
                    : "border-border bg-muted/30 hover:border-primary/50 hover:bg-primary/5"
                } disabled:opacity-60 disabled:cursor-not-allowed`}
            >
              {selected === "user" && loading ? (
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              ) : (
                <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
                  <User className="w-6 h-6 text-primary" />
                </div>
              )}
              <div className="text-center">
                <div className="font-semibold text-foreground text-sm">User</div>
                <div className="text-xs text-muted-foreground mt-1 leading-tight">
                  Analyst access
                </div>
              </div>
            </button>

            {/* Admin Role */}
            <button
              onClick={() => handleRoleSelect("admin")}
              disabled={loading}
              className={`flex flex-col items-center gap-3 p-6 rounded-lg border transition-all duration-200
                ${
                  selected === "admin"
                    ? "border-secondary bg-secondary/10 shadow-[0_0_20px_rgba(168,85,247,0.15)]"
                    : "border-border bg-muted/30 hover:border-secondary/50 hover:bg-secondary/5"
                } disabled:opacity-60 disabled:cursor-not-allowed`}
            >
              {selected === "admin" && loading ? (
                <Loader2 className="w-6 h-6 text-secondary animate-spin" />
              ) : (
                <div className="p-3 rounded-lg bg-secondary/10 border border-secondary/20">
                  <Crown className="w-6 h-6 text-secondary" />
                </div>
              )}
              <div className="text-center">
                <div className="font-semibold text-foreground text-sm">Admin</div>
                <div className="text-xs text-muted-foreground mt-1 leading-tight">
                  Full access
                </div>
              </div>
            </button>
          </div>

          {error && (
            <p className="mt-5 text-center text-sm text-destructive">{error}</p>
          )}

          {loading && !error && (
            <p className="mt-5 text-center text-sm text-muted-foreground">
              Setting up your account…
            </p>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="relative z-10 mt-8 text-center text-xs text-muted-foreground">
        <Link href="/" className="hover:text-foreground transition-colors">
          ← Back to Home
        </Link>
      </div>
    </div>
  );
}
