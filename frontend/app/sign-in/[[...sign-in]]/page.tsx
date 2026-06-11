import { SignIn } from "@clerk/nextjs";
import { Shield } from "lucide-react";
import Link from "next/link";

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center relative">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-100" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/5 rounded-full blur-3xl pointer-events-none" />

      {/* Logo */}
      <div className="relative z-10 mb-8 text-center">
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

      {/* Clerk SignIn Component */}
      <div className="relative z-10">
        <SignIn
          forceRedirectUrl="/dashboard"
          fallbackRedirectUrl="/dashboard"
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "bg-card border border-border shadow-[0_0_40px_rgba(0,212,255,0.05)]",
              headerTitle: "text-foreground",
              headerSubtitle: "text-muted-foreground",
              socialButtonsBlockButton:
                "bg-muted border border-border text-foreground hover:bg-muted/80",
              formFieldLabel: "text-muted-foreground",
              formFieldInput:
                "bg-muted border-border text-foreground focus:border-primary focus:ring-primary",
              formButtonPrimary:
                "bg-primary text-background hover:bg-primary/90 hover:shadow-[0_0_20px_rgba(0,212,255,0.4)]",
              footerActionLink: "text-primary hover:text-primary/80",
              dividerLine: "bg-border",
              dividerText: "text-muted-foreground",
              identityPreviewText: "text-muted-foreground",
              identityPreviewEditButton: "text-primary",
              formFieldSuccessText: "text-accent",
              formFieldErrorText: "text-destructive",
              alertText: "text-destructive",
              alertIcon: "text-destructive",
            },
          }}
        />
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
