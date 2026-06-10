FROM node:20-slim

WORKDIR /app

# Install git and basic tools (lighter than puppeteer deps)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY package.json .
RUN npm cache clean --force
RUN rm -f package-lock.json
RUN npm install

# Copy all bot code
COPY . .

# Create auth and temp directories
RUN mkdir -p auth_info temp

# Run bot
CMD ["npm", "start"]
