"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  placeholder?: string;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, placeholder, ...props }, ref) => {
    return (
      <div className="relative">
        <select
          className={cn(
            "flex h-9 w-full appearance-none rounded-md border border-border bg-card px-3 py-1.5 pr-8 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors",
            className
          )}
          ref={ref}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
      </div>
    );
  }
);
Select.displayName = "Select";

export { Select };

// Minimal API-compatible wrappers for shadcn-style usage
interface SelectRootProps {
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  disabled?: boolean;
}

export function SelectRoot({ value, onValueChange, children, disabled }: SelectRootProps) {
  return (
    <div data-value={value} data-disabled={disabled}>
      {children}
    </div>
  );
}

export function SelectTrigger({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("flex items-center justify-between h-9 px-3 rounded-md border border-border bg-card text-sm cursor-pointer", className)}>{children}<ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /></div>;
}

export function SelectValue({ placeholder }: { placeholder?: string }) {
  return <span className="text-muted-foreground">{placeholder}</span>;
}

export function SelectContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("absolute z-50 mt-1 rounded-md border border-border bg-card shadow-lg py-1", className)}>{children}</div>;
}

export function SelectItem({ children, value, className }: { children: React.ReactNode; value: string; className?: string }) {
  return <div className={cn("px-3 py-1.5 text-sm text-foreground hover:bg-muted cursor-pointer", className)} data-value={value}>{children}</div>;
}
