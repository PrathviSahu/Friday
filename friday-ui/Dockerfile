# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────
#  F.R.I.D.A.Y. frontend image — React/Vite build served by
#  nginx, which proxies /api and /temp_audio to the backend
#  service (same-origin → no CORS, relative URLs everywhere).
# ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

RUN npm run build

# ── Runtime: nginx ──────────────────────────────────────────
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
