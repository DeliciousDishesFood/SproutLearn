# 青芽 SproutLearn 前端镜像：Node 构建静态产物 → Nginx 托管并同源反代 /api。
# 生产 compose 会挂载 deploy/nginx/nginx.conf 覆盖 default.conf；这里仍内置一份，
# 保证单独 `docker build/run frontend` 时前端与 api 容器可以直接联通。

FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# .env.production 已声明 VITE_API_BASE_URL=/api，构建产物只请求同源 /api。
RUN npm run build

FROM nginx:1.27-alpine AS runtime
WORKDIR /usr/share/nginx/html

# client_max_body_size 覆盖契约第 9 章的 110m（必须 ≥ 单次上传 100MB），
# 否则文件在 Nginx 层就被 413，前端拿不到后端 fail_list。
RUN printf '%s\n' \
  'server {' \
  '    listen 80;' \
  '    server_name _;' \
  '    client_max_body_size 110m;' \
  '    proxy_read_timeout 180s;' \
  '' \
  '    root /usr/share/nginx/html;' \
  '    index index.html;' \
  '' \
  '    location /api/ {' \
  '        proxy_pass http://api:8000;' \
  '        proxy_http_version 1.1;' \
  '        proxy_set_header Host $host;' \
  '        proxy_set_header X-Real-IP $remote_addr;' \
  '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
  '        proxy_set_header X-Forwarded-Proto $scheme;' \
  '    }' \
  '' \
  '    location /health {' \
  '        proxy_pass http://api:8000/health;' \
  '        proxy_set_header Host $host;' \
  '    }' \
  '' \
  '    location / {' \
  '        try_files $uri $uri/ /index.html;' \
  '    }' \
  '}' \
  > /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
