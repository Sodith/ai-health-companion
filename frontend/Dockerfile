# ─────────────────────────────────────────────────────────────────────────────
#  AI Health Companion — Frontend Dockerfile
#  Multi-stage build: Angular build → nginx static server
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Angular build ───────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package manifests first for layer-cache efficiency
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies needed for ng build)
RUN npm ci --legacy-peer-deps

# Copy source tree
COPY . .

# Production build — outputs to dist/frontend/browser
RUN npx ng build --configuration production


# ── Stage 2: nginx runtime ───────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled Angular artefacts
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

# Custom nginx config — handles Angular routing + API proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

