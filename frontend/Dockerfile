# Stages:
#   dev  - hot-reload server used by docker-compose (service `web`)
#   prod - optimized `next build` + `next start`, required to exercise the
#          PWA service worker (it is only registered in production builds)
#
# Build the production image with the public API URL baked in, because
# NEXT_PUBLIC_* values are inlined at build time:
#   docker build --target prod --build-arg NEXT_PUBLIC_API_URL=https://api.example.com/api/v1 ./frontend

FROM node:20-alpine AS dev

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]


FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build


FROM node:20-alpine AS prod

WORKDIR /app
ENV NODE_ENV=production

COPY --from=build --chown=node:node /app/package.json /app/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/next.config.js ./

USER node
EXPOSE 3000

CMD ["npx", "next", "start", "-p", "3000"]
