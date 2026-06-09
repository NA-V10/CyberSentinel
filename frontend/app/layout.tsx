import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "CyberSentinel AI - AI-Powered Cybersecurity Incident Response",
    template: "%s | CyberSentinel AI",
  },
  description:
    "Enterprise-grade AI-powered cybersecurity incident response platform with multi-agent analysis, RAG-powered search, and real-time threat intelligence.",
  keywords: ["cybersecurity", "incident response", "AI", "threat intelligence", "SIEM", "SOC"],
  authors: [{ name: "CyberSentinel AI" }],
  icons: { icon: "/favicon.ico" },
  openGraph: {
    title: "CyberSentinel AI",
    description: "AI-Powered Cybersecurity Incident Response Platform",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0e1a",
};

const CLERK_APPEARANCE = {
  variables: {
    colorPrimary: "#00d4ff",
    colorBackground: "#0a0e1a",
    colorInputBackground: "#1e2537",
    colorInputText: "#e2e8f0",
    colorText: "#e2e8f0",
    colorTextSecondary: "#94a3b8",
    colorNeutral: "#1f2937",
    borderRadius: "0.5rem",
    fontFamily: "Inter, sans-serif",
  },
  elements: {
    card: { backgroundColor: "#111827", border: "1px solid #1f2937" },
    headerTitle: { color: "#e2e8f0" },
    headerSubtitle: { color: "#94a3b8" },
    formFieldLabel: { color: "#94a3b8" },
    formFieldInput: {
      backgroundColor: "#1e2537",
      border: "1px solid #1f2937",
      color: "#e2e8f0",
    },
    formButtonPrimary: {
      backgroundColor: "#00d4ff",
      color: "#0a0e1a",
      fontWeight: "600",
    },
    footerActionLink: { color: "#00d4ff" },
  },
};

// Detect whether a real Clerk key is configured.
const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "";
const isClerkConfigured =
  (clerkKey.startsWith("pk_test_") || clerkKey.startsWith("pk_live_")) &&
  !clerkKey.includes("your_publishable_key") &&
  !clerkKey.includes("your-clerk");

const Inner = ({ children }: { children: React.ReactNode }) => (
  <html lang="en" className="dark" suppressHydrationWarning>
    <head>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap"
        rel="stylesheet"
      />
    </head>
    <body className={`${inter.variable} font-sans bg-background text-foreground antialiased`}>
      {!isClerkConfigured && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-yellow-500/20 border-b border-yellow-500/40 px-4 py-2 text-center text-xs text-yellow-300">
          ⚠ Clerk not configured — add{" "}
          <code className="font-mono bg-yellow-500/20 px-1 rounded">NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code>{" "}
          to <code className="font-mono bg-yellow-500/20 px-1 rounded">frontend/.env.local</code>.{" "}
          Get keys at{" "}
          <a
            href="https://dashboard.clerk.com"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            dashboard.clerk.com
          </a>
        </div>
      )}
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: "#111827", border: "1px solid #1f2937", color: "#e2e8f0" },
        }}
      />
    </body>
  </html>
);

export default function RootLayout({ children }: { children: React.ReactNode }) {
  if (!isClerkConfigured) {
    return <Inner>{children}</Inner>;
  }
  return (
    <ClerkProvider appearance={CLERK_APPEARANCE}>
      <Inner>{children}</Inner>
    </ClerkProvider>
  );
}
