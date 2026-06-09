import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const severityBadgeVariants = cva(
  "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border uppercase tracking-wide",
  {
    variants: {
      severity: {
        critical:
          "bg-red-500/15 border-red-500/40 text-red-400 animate-[criticalPulse_1.5s_ease-in-out_infinite]",
        high: "bg-orange-500/15 border-orange-500/40 text-orange-400",
        medium: "bg-yellow-500/15 border-yellow-500/40 text-yellow-400",
        low: "bg-green-500/15 border-green-500/40 text-green-400",
        info: "bg-blue-500/15 border-blue-500/40 text-blue-400",
        unknown: "bg-gray-500/15 border-gray-500/40 text-gray-400",
      },
      size: {
        sm: "px-2 py-0.5 text-xs",
        md: "px-2.5 py-1 text-xs",
        lg: "px-3 py-1.5 text-sm",
      },
    },
    defaultVariants: {
      severity: "unknown",
      size: "md",
    },
  }
);

interface SeverityBadgeProps extends VariantProps<typeof severityBadgeVariants> {
  className?: string;
  showDot?: boolean;
}

const severityDotColors: Record<string, string> = {
  critical: "bg-red-400",
  high: "bg-orange-400",
  medium: "bg-yellow-400",
  low: "bg-green-400",
  info: "bg-blue-400",
  unknown: "bg-gray-400",
};

export function SeverityBadge({
  severity,
  size,
  className,
  showDot = true,
}: SeverityBadgeProps) {
  const sev = (severity || "unknown") as string;
  const dotColor = severityDotColors[sev] || "bg-gray-400";

  return (
    <span className={cn(severityBadgeVariants({ severity, size }), className)}>
      {showDot && (
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full shrink-0",
            dotColor,
            sev === "critical" && "animate-pulse"
          )}
        />
      )}
      {sev}
    </span>
  );
}

// Escalation level badge
const escalationBadgeVariants = cva(
  "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border uppercase tracking-wide",
  {
    variants: {
      level: {
        P1: "bg-red-500/15 border-red-500/40 text-red-400",
        P2: "bg-orange-500/15 border-orange-500/40 text-orange-400",
        P3: "bg-yellow-500/15 border-yellow-500/40 text-yellow-400",
        P4: "bg-green-500/15 border-green-500/40 text-green-400",
      },
    },
    defaultVariants: {
      level: "P4",
    },
  }
);

interface EscalationBadgeProps extends VariantProps<typeof escalationBadgeVariants> {
  className?: string;
}

export function EscalationBadge({ level, className }: EscalationBadgeProps) {
  const labelMap: Record<string, string> = {
    P1: "P1 - Critical",
    P2: "P2 - High",
    P3: "P3 - Medium",
    P4: "P4 - Low",
  };

  return (
    <span className={cn(escalationBadgeVariants({ level }), className)}>
      {labelMap[level as string] || level}
    </span>
  );
}

// Threat class badge
export function ThreatClassBadge({
  threatClass,
  className,
}: {
  threatClass: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium border bg-secondary/10 border-secondary/30 text-purple-400",
        className
      )}
    >
      {threatClass}
    </span>
  );
}

export default SeverityBadge;
