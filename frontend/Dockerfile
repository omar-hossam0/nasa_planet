# Trend Detective frontend image: Vite build stage + static Nginx runtime.
FROM node:22-alpine AS build

WORKDIR /app

# Dependency layer is cached until the lockfile changes.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# vite.config.ts writes to ../dist/product, i.e. /dist/product inside the builder.
RUN npm run build


FROM nginx:1.27-alpine AS runtime

# Serves the compiled product and proxies API paths to the backend service.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /dist/product /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
