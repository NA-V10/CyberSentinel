# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM node:20-slim AS builder

LABEL maintainer="CyberSentinel AI"

WORKDIR /app

# Install dependencies (npm install since no lock file is committed)
COPY package.json ./

RUN npm install --legacy-peer-deps

# Copy the rest of the application source
COPY . .

# Build the production Next.js bundle with standalone output
# next.config.js must include: output: 'standalone'
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — runtime image (minimal)
# ---------------------------------------------------------------------------
FROM node:20-alpine AS runner

WORKDIR /app

# Harden: run as a non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

ENV NODE_ENV=production
# Telemetry opt-out
ENV NEXT_TELEMETRY_DISABLED=1

# Copy the standalone server bundle produced by the builder
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./

# Copy static assets and public directory
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME=0.0.0.0

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
