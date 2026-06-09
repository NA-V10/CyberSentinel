import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "#1f2937",
        input: "#1f2937",
        ring: "#00d4ff",
        background: "#0a0e1a",
        foreground: "#e2e8f0",
        primary: {
          DEFAULT: "#00d4ff",
          foreground: "#0a0e1a",
        },
        secondary: {
          DEFAULT: "#7c3aed",
          foreground: "#e2e8f0",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#e2e8f0",
        },
        muted: {
          DEFAULT: "#1e2537",
          foreground: "#94a3b8",
        },
        accent: {
          DEFAULT: "#10b981",
          foreground: "#0a0e1a",
        },
        popover: {
          DEFAULT: "#111827",
          foreground: "#e2e8f0",
        },
        card: {
          DEFAULT: "#111827",
          foreground: "#e2e8f0",
        },
        chart: {
          "1": "#00d4ff",
          "2": "#7c3aed",
          "3": "#10b981",
          "4": "#ef4444",
          "5": "#f59e0b",
        },
        cyber: {
          cyan: "#00d4ff",
          purple: "#7c3aed",
          green: "#10b981",
          red: "#ef4444",
          orange: "#f97316",
          yellow: "#f59e0b",
          navy: "#0a0e1a",
          dark: "#111827",
          muted: "#1e2537",
          border: "#1f2937",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "pulse-glow": {
          "0%, 100%": {
            boxShadow: "0 0 5px #00d4ff, 0 0 10px #00d4ff",
          },
          "50%": {
            boxShadow: "0 0 20px #00d4ff, 0 0 40px #00d4ff, 0 0 60px #00d4ff",
          },
        },
        "scan-line": {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "scan-line": "scan-line 8s linear infinite",
        float: "float 3s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(0, 212, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.05) 1px, transparent 1px)",
        "cyber-gradient":
          "linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0a0e1a 100%)",
        "glow-cyan":
          "radial-gradient(circle, rgba(0, 212, 255, 0.15) 0%, transparent 70%)",
        "glow-purple":
          "radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, transparent 70%)",
      },
      backgroundSize: {
        grid: "40px 40px",
      },
    },
  },
  plugins: [],
};

export default config;
