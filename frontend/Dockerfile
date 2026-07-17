# Stage 1: build the static assets. This stage needs the full Node
# toolchain and all devDependencies (TypeScript, Vite, ESLint types, etc.),
# which together are large — but none of that ships in the final image.
FROM node:24-slim AS build

WORKDIR /app

# Copy dependency-relevant files first so Docker can cache this layer and
# skip `npm ci` on rebuilds that only change application code — same
# reasoning as the backend Dockerfile's pyproject.toml-first copy.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked into the JS bundle at this point — see docs/manual/03 for why this
# is different from how the backend reads its config.
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

# Stage 2: serve the built static files with nginx. No Node, no
# node_modules, no source code — just HTML/CSS/JS and a tiny web server.
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80