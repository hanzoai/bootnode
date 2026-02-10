# Bootnode Web Dashboard
# Next.js 15 with React 19

FROM node:22-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable pnpm && pnpm install --frozen-lockfile

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Production build-time environment variables
# Brand is auto-detected from domain at runtime (see lib/brand.ts)
# Override via K8s env vars: NEXT_PUBLIC_BRAND, NEXT_PUBLIC_API_URL, etc.
ARG NEXT_PUBLIC_BRAND=bootnode
ARG NEXT_PUBLIC_API_URL=https://api.bootno.de
ARG NEXT_PUBLIC_WS_URL=wss://ws.bootno.de
ARG NEXT_PUBLIC_IAM_URL=https://iam.bootno.de
ARG NEXT_PUBLIC_IAM_CLIENT_ID=bootnode-web

ENV NEXT_PUBLIC_BRAND=$NEXT_PUBLIC_BRAND
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_IAM_URL=$NEXT_PUBLIC_IAM_URL
ENV NEXT_PUBLIC_IAM_CLIENT_ID=$NEXT_PUBLIC_IAM_CLIENT_ID
ENV NEXT_TELEMETRY_DISABLED=1

RUN corepack enable pnpm && pnpm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3001

ENV PORT=3001
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
