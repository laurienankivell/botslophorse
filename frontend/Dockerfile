# Use Node.js for React
FROM node:22-alpine

WORKDIR /app

# Install dependencies
COPY package.json yarn.lock ./
RUN yarn install

# Copy source
COPY . .

# Expose React dev server
EXPOSE 3000

# Start React app
CMD ["yarn", "start"]
