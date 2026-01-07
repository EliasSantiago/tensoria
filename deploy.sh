#!/bin/bash
# Tensoria - Production Deployment Script
# Domain: tensoria.orkestrai.com.br

set -e

echo "🚀 Tensoria - Production Deployment"
echo "===================================="

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Create required directories
mkdir -p certbot/www certbot/conf

# Copy environment file if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from .env.example"
    echo "⚠️  Please edit .env with your production settings"
fi

# Step 1: Start services without nginx first (for SSL certificate)
echo ""
echo "📦 Step 1: Starting Ollama and API services..."
docker compose -f docker-compose.prod.yml up -d ollama api
sleep 10

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
docker compose -f docker-compose.prod.yml ps

# Step 2: Generate SSL certificate (only first time)
if [ ! -d "certbot/conf/live/tensoria.orkestrai.com.br" ]; then
    echo ""
    echo "🔐 Step 2: Generating SSL certificate..."
    echo "⚠️  Make sure DNS is pointing to this server!"
    
    # Start nginx without SSL first
    cat > nginx/nginx-init.conf << 'EOF'
events { worker_connections 1024; }
http {
    server {
        listen 80;
        server_name tensoria.orkestrai.com.br;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 200 'Tensoria is starting...';
        }
    }
}
EOF
    
    # Start nginx with initial config
    docker run -d --name tensoria-nginx-temp \
        -p 80:80 \
        -v $(pwd)/nginx/nginx-init.conf:/etc/nginx/nginx.conf:ro \
        -v $(pwd)/certbot/www:/var/www/certbot:ro \
        nginx:alpine
    
    # Request certificate
    docker run --rm \
        -v $(pwd)/certbot/www:/var/www/certbot \
        -v $(pwd)/certbot/conf:/etc/letsencrypt \
        certbot/certbot certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email admin@orkestrai.com.br \
        --agree-tos \
        --no-eff-email \
        -d tensoria.orkestrai.com.br
    
    # Stop temporary nginx
    docker stop tensoria-nginx-temp
    docker rm tensoria-nginx-temp
    rm nginx/nginx-init.conf
    
    echo "✅ SSL certificate generated!"
else
    echo "✅ SSL certificate already exists"
fi

# Step 3: Start all services including nginx
echo ""
echo "🌐 Step 3: Starting all services with nginx..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 API URL: https://tensoria.orkestrai.com.br"
echo "🏥 Health check: https://tensoria.orkestrai.com.br/health"
echo "📖 API Docs: https://tensoria.orkestrai.com.br/docs"
echo ""
echo "🤖 Install models:"
echo "   docker exec -it tensoria-ollama ollama pull mistral"
echo "   docker exec -it tensoria-ollama ollama pull qwen"
echo "   docker exec -it tensoria-ollama ollama pull deepseek-coder"
echo ""
echo "📋 Check logs:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
