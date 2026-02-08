# VoiceAI Platform - Frontend Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build for production
RUN npm run build

# Expose port
EXPOSE 3000

# Run production server
CMD ["npm", "run", "start"]
