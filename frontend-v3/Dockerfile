# 青芽 SproutLearn 新前端主线：Node 构建静态产物 → Nginx 托管并同源反代 /api。
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime
WORKDIR /usr/share/nginx/html

# 生产 compose 会挂载 deploy/nginx/nginx.conf；此默认配置也支持独立运行。
RUN printf '%s\n' \
  'server {' \
  '    listen 80;' \
  '    server_name _;' \
  '    client_max_body_size 110m;' \
  '    proxy_read_timeout 180s;' \
  '    root /usr/share/nginx/html;' \
  '    index index.html;' \
  '    location /api/ {' \
  '        proxy_pass http://api:8000;' \
  '        proxy_http_version 1.1;' \
  '        proxy_set_header Host $host;' \
  '        proxy_set_header X-Real-IP $remote_addr;' \
  '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
  '        proxy_set_header X-Forwarded-Proto $scheme;' \
  '    }' \
  '    location /health {' \
  '        proxy_pass http://api:8000/health;' \
  '        proxy_set_header Host $host;' \
  '    }' \
  '    location / {' \
  '        try_files $uri $uri/ /index.html;' \
  '    }' \
  '}' \
  > /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
