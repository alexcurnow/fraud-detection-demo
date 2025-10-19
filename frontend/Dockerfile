# Frontend Dockerfile - builds and serves the SvelteKit application
# Multi-stage build: stage 1 builds the app, stage 2 serves it

# Stage 1: Build the SvelteKit app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the SvelteKit app (creates production build)
RUN npm run build

# Stage 2: Serve the built app
FROM node:20-alpine

WORKDIR /app

# Copy built app from builder stage
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json

# Install only production dependencies
RUN npm ci --omit=dev

# Expose port 3000 (SvelteKit default for adapter-node)
EXPOSE 3000

# Set environment variable for production
ENV NODE_ENV=production

# Run the SvelteKit server
CMD ["node", "build"]
