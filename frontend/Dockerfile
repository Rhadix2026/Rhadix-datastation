FROM node:20-alpine AS build
WORKDIR /app

# Build-args vóór COPY zodat de cache wordt gebust als env-waarden veranderen
ARG VITE_API_URL=""
ARG VITE_KIK_ENV=""
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_KIK_ENV=${VITE_KIK_ENV}
ARG VITE_APP_VERSION=""
ENV VITE_APP_VERSION=${VITE_APP_VERSION}

COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
