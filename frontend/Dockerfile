FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_SHOP_ID=00000000-0000-0000-0000-000000000101
ARG VITE_DEMO_MODE=true
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_SHOP_ID=$VITE_SHOP_ID \
    VITE_DEMO_MODE=$VITE_DEMO_MODE
RUN npm run build:h5

FROM nginx:1.27-alpine
COPY --from=build /app/dist/build/h5 /usr/share/nginx/html
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
  listen 80;
  root /usr/share/nginx/html;
  location / {
    try_files $uri $uri/ /index.html;
  }
}
EOF
EXPOSE 80
