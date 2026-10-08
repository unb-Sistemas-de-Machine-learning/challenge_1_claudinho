# Duas etapas: "dev" roda o Vite com recarga automatica (e o que o docker compose usa),
# "producao" gera o build estatico e serve com nginx.

FROM node:22-alpine AS dev
WORKDIR /app
# Dependencias primeiro: a camada so e refeita quando o package-lock muda.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
# --host para o servidor aceitar conexao de fora do container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM dev AS build
RUN npm run build

FROM nginx:alpine AS producao
COPY --from=build /app/dist /usr/share/nginx/html
# PWA e aplicacao de pagina unica: qualquer rota cai no index.html.
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
