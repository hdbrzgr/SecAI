# Build context: the repository root (the web app uses the packages/ui workspace).
FROM node:22-alpine AS deps
WORKDIR /repo
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/
COPY packages/ui/package.json packages/ui/
RUN npm ci --no-audit --no-fund

FROM node:22-alpine AS build
WORKDIR /repo
# Baked into the Next.js rewrite that proxies /api/* to the backend.
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=$API_INTERNAL_URL NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /repo/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY packages/ui packages/ui
COPY apps/web apps/web
RUN npm run build -w secai-web

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S -g 10001 secai && adduser -S -u 10001 -G secai secai
COPY --from=build --chown=secai:secai /repo/apps/web/.next/standalone ./
COPY --from=build --chown=secai:secai /repo/apps/web/.next/static ./apps/web/.next/static
USER secai
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
