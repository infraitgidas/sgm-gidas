FROM node:20-alpine AS dependencies

WORKDIR /app

COPY package*.json ./
RUN npm ci

FROM dependencies AS build

ARG VITE_APP_ENV=production
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_API_URL=/api
ARG VITE_SERVER_FILTER_PERSONAL=true
ARG VITE_BASE_PATH=/

ENV VITE_APP_ENV=${VITE_APP_ENV} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_API_URL=${VITE_API_URL} \
    VITE_SERVER_FILTER_PERSONAL=${VITE_SERVER_FILTER_PERSONAL} \
    VITE_BASE_PATH=${VITE_BASE_PATH}

COPY . .
RUN npm run build:production

FROM nginxinc/nginx-unprivileged:1.27-alpine AS production

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]

FROM dependencies AS development

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
