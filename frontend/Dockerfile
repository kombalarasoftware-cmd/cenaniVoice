# VoiceAI Platform - Frontend Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build for production (optional for dev)
# RUN npm run build

# Expose port
EXPOSE 3000

# Default command for development
CMD ["npm", "run", "dev"]
