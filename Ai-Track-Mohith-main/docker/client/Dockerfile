FROM node:20-alpine AS builder

WORKDIR /app
COPY client/package*.json ./
RUN npm ci
COPY client/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/client/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
