# syntax=docker/dockerfile:1

FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./

ARG VITE_DATA_SOURCE=api
ARG VITE_API_BASE_URL=/api
RUN VITE_DATA_SOURCE="$VITE_DATA_SOURCE" \
    VITE_API_BASE_URL="$VITE_API_BASE_URL" \
    npm run build

FROM nginx:alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
