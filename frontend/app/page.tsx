"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import Link from "next/link";
import { useRef } from "react";
import {
  Shield,
  Search,
  Brain,
  Activity,
  GitBranch,
  ArrowRight,
  Zap,
  Lock,
  Eye,
  ChevronRight,
} from "lucide-react";

const features = [
  {
    icon: Search,
    title: "RAG-Powered Search",
    description:
      "Semantic search across 10,000+ historical incidents using vector embeddings and Neo4j graph database for contextual retrieval.",
    color: "text-cyan-400",
    bgColor: "bg-cyan-400/10",
    borderColor: "border-cyan-400/20",
  },
  {
    icon: Brain,
    title: "Multi-Agent AI System",
    description:
      "8 specialized AI agents collaborate: Validation, Classification, Retrieval, Mitigation, Escalation, Summary, Judge, and Coordinator.",
    color: "text-purple-400",
    bgColor: "bg-purple-400/10",
    borderColor: "border-purple-400/20",
  },
  {
    icon: Activity,
    title: "Real-time Analysis",
    description:
      "WebSocket-powered live updates stream agent progress in real-time as your incident is analyzed and mitigation plans are generated.",
    color: "text-green-400",
    bgColor: "bg-green-400/10",
    borderColor: "border-green-400/20",
  },
  {
    icon: GitBranch,
    title: "Graph Intelligence",
    description:
      "Interactive Neo4j-powered knowledge graph showing incident relationships, attack patterns, asset connections, and mitigation pathways.",
    color: "text-orange-400",
    bgColor: "bg-orange-400/10",
    borderColor: "border-orange-400/20",
  },
];

const stats = [
  { value: "10,000+", label: "Incidents Analyzed", icon: Shield },
  { value: "8", label: "AI Agents", icon: Brain },
  { value: "< 2s", label: "Response Time", icon: Zap },
  { value: "99.9%", label: "Uptime SLA", icon: Lock },
];

const agentNames = [
  "Validation Agent",
  "Classification Agent",
  "Retrieval Agent",
  "Mitigation Agent",
  "Escalation Agent",
  "Summary Agent",
  "Judge Agent",
  "Coordinator Agent",
];

export default function LandingPage() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });

  const heroOpacity = useTransform(scrollYProgress, [0, 1], [1, 0]);
  const heroY = useTransform(scrollYProgress, [0, 1], [0, -80]);

  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 backdrop-blur-md bg-background/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Shield className="w-8 h-8 text-primary" />
              <span className="text-xl font-bold text-foreground">
                CyberSentinel{" "}
                <span className="text-primary">AI</span>
              </span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Features
              </a>
              <a href="#stats" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Platform
              </a>
              <a href="#agents" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                AI Agents
              </a>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/sign-in"
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/sign-up"
                className="px-4 py-2 text-sm font-semibold bg-primary text-background rounded-md hover:bg-primary/90 transition-all duration-200 hover:shadow-[0_0_20px_rgba(0,212,255,0.4)]"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section
        ref={heroRef}
        className="relative min-h-screen flex items-center justify-center pt-16"
      >
        {/* Background grid */}
        <div className="absolute inset-0 bg-grid opacity-100" />

        {/* Glow orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/5 rounded-full blur-3xl pointer-events-none" />

        {/* Scan line */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div
            className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent"
            style={{ animation: "scanLine 8s linear infinite" }}
          />
        </div>

        <motion.div
          style={{ opacity: heroOpacity, y: heroY }}
          className="relative z-10 text-center max-w-5xl mx-auto px-4 sm:px-6"
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/10 text-primary text-sm font-medium mb-8"
          >
            <Zap className="w-4 h-4" />
            <span>AI-Powered Threat Response Platform</span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight mb-6 leading-[1.1]"
          >
            <span className="text-foreground">AI-Powered</span>
            <br />
            <span
              className="gradient-text-cyan-purple"
              style={{
                background: "linear-gradient(135deg, #00d4ff 0%, #7c3aed 60%, #10b981 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Cybersecurity Incident
            </span>
            <br />
            <span className="text-foreground">Response</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto mb-10 leading-relaxed"
          >
            Analyze security incidents with 8 specialized AI agents, RAG-powered
            historical context, and graph-based relationship intelligence. Get
            actionable mitigation plans in under 2 seconds.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link
              href="/sign-up"
              className="group flex items-center gap-2 px-8 py-4 text-base font-semibold bg-primary text-background rounded-lg hover:bg-primary/90 transition-all duration-200 hover:shadow-[0_0_30px_rgba(0,212,255,0.5)] w-full sm:w-auto justify-center"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              href="/dashboard"
              className="group flex items-center gap-2 px-8 py-4 text-base font-semibold border border-border hover:border-primary/50 text-foreground rounded-lg hover:bg-primary/5 transition-all duration-200 w-full sm:w-auto justify-center"
            >
              <Eye className="w-5 h-5 text-primary" />
              View Demo
            </Link>
          </motion.div>

          {/* Trust indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="mt-12 flex items-center justify-center gap-6 text-xs text-muted-foreground flex-wrap"
          >
            <div className="flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-accent" />
              <span>SOC 2 Compliant</span>
            </div>
            <div className="w-px h-3 bg-border" />
            <div className="flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-accent" />
              <span>End-to-End Encrypted</span>
            </div>
            <div className="w-px h-3 bg-border" />
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-accent" />
              <span>99.9% Uptime SLA</span>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Stats Section */}
      <section id="stats" className="py-20 border-y border-border/50 bg-card/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="text-center"
              >
                <div className="flex justify-center mb-3">
                  <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
                    <stat.icon className="w-6 h-6 text-primary" />
                  </div>
                </div>
                <div className="text-3xl sm:text-4xl font-extrabold text-foreground mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
              Enterprise-Grade Security Intelligence
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
              Built on cutting-edge AI technology to give your security team superpowers
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className={`cyber-card p-6 border ${feature.borderColor} hover:border-opacity-50 transition-all duration-300 group`}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${feature.bgColor} shrink-0 group-hover:scale-110 transition-transform duration-300`}>
                    <feature.icon className={`w-6 h-6 ${feature.color}`} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Agents Section */}
      <section id="agents" className="py-24 bg-card/20 border-y border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
              8 Specialized AI Agents
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
              A coordinated multi-agent system that mirrors how elite SOC teams operate
            </p>
          </motion.div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {agentNames.map((agent, i) => (
              <motion.div
                key={agent}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.07 }}
                className="cyber-card p-4 text-center border border-border hover:border-primary/30 transition-all duration-300 group cursor-default"
              >
                <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-3 group-hover:bg-primary/20 transition-colors">
                  <span className="text-primary font-bold text-sm">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <p className="text-sm font-medium text-foreground">{agent}</p>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            className="text-center mt-12"
          >
            <Link
              href="/sign-up"
              className="group inline-flex items-center gap-2 px-8 py-4 text-base font-semibold bg-primary text-background rounded-lg hover:bg-primary/90 transition-all duration-200 hover:shadow-[0_0_30px_rgba(0,212,255,0.5)]"
            >
              Start Analyzing Incidents
              <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
              How It Works
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Submit Incident",
                description: "Paste your incident description, add metadata like IPs, protocols, and severity level.",
                color: "text-primary",
                borderColor: "border-primary/30",
              },
              {
                step: "02",
                title: "AI Agent Pipeline",
                description: "8 specialized agents validate, classify, retrieve context, generate mitigations, and judge quality in real-time.",
                color: "text-secondary",
                borderColor: "border-secondary/30",
              },
              {
                step: "03",
                title: "Actionable Response",
                description: "Receive a complete response plan with 4-phase mitigations, escalation level, similar incidents, and quality score.",
                color: "text-accent",
                borderColor: "border-accent/30",
              },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className={`cyber-card p-6 border ${item.borderColor}`}
              >
                <div className={`text-5xl font-black mb-4 ${item.color} opacity-40`}>
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  {item.title}
                </h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {item.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-secondary/5 to-accent/5" />
        <div className="absolute inset-0 bg-grid opacity-50" />
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <Shield className="w-16 h-16 text-primary mx-auto mb-6 opacity-80" />
            <h2 className="text-3xl sm:text-5xl font-bold text-foreground mb-6">
              Ready to Secure Your Infrastructure?
            </h2>
            <p className="text-muted-foreground text-lg mb-10 max-w-2xl mx-auto">
              Join security teams using CyberSentinel AI to respond faster, smarter, and with more confidence.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/sign-up"
                className="group flex items-center gap-2 px-8 py-4 text-base font-semibold bg-primary text-background rounded-lg hover:bg-primary/90 transition-all duration-200 hover:shadow-[0_0_30px_rgba(0,212,255,0.5)] w-full sm:w-auto justify-center"
              >
                Get Started Free
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/dashboard"
                className="px-8 py-4 text-base font-semibold border border-border hover:border-primary/50 text-foreground rounded-lg hover:bg-primary/5 transition-all duration-200 w-full sm:w-auto"
              >
                View Demo Dashboard
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              <span className="text-sm font-semibold text-foreground">
                CyberSentinel AI
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              © {new Date().getFullYear()} CyberSentinel AI. Enterprise cybersecurity intelligence platform.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
