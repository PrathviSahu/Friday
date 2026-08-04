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

# API token baked into the bundle so every request carries
# X-FRIDAY-Token (required: in Docker all traffic is non-loopback).
# Passed automatically by docker-compose from FRIDAY_API_TOKEN.
ARG VITE_FRIDAY_TOKEN=""
ENV VITE_FRIDAY_TOKEN=$VITE_FRIDAY_TOKEN

RUN npm run build

# ── Runtime: nginx ──────────────────────────────────────────
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
