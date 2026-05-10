#!/bin/bash
# vibe proving Docker quick start script

set -e

echo "vibe proving Docker quick start"
echo "==============================="
echo ""

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker was not found."
    echo "Please install and start Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    echo "ERROR: Docker Compose was not found."
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check config file
if [ ! -f "app/config.toml" ]; then
    echo "First run: creating app/config.toml"
    cp app/config.example.toml app/config.toml
    echo ""
    echo "Please edit app/config.toml before continuing."
    echo "Required fields:"
    echo "   [auth]"
    echo "   superuser_username = \"dev_user\""
    echo "   superuser_password = \"change-this-password\""
    echo ""
    echo "   [llm]"
    echo "   base_url = \"https://api.deepseek.com/v1\""
    echo "   api_key  = \"sk-your-api-key\""
    echo "   model    = \"deepseek-chat\""
    echo ""
    echo "Use the [auth] superuser account to log in and configure APIs."
    echo "Regular users can register and use the app but cannot edit API settings."
    echo ""
    read -p "Press Enter to continue after editing app/config.toml... " -r
fi

# Create data directory
mkdir -p data

# Build and start
echo "Building Docker image..."
$COMPOSE build

echo ""
echo "Starting service..."
$COMPOSE up -d

echo ""
echo "Waiting for service..."
sleep 5

# Check health
if curl -s http://localhost:8080/health > /dev/null; then
    echo ""
    echo "Service started successfully."
    echo ""
    echo "URL:"
    echo "   http://localhost:8080/ui/"
    echo ""
    echo "Useful commands:"
    echo "   Logs:    $COMPOSE logs -f"
    echo "   Stop:    $COMPOSE down"
    echo "   Restart: $COMPOSE restart"
    echo "   Status:  $COMPOSE ps"
    echo ""
else
    echo ""
    echo "The service may still be starting. Try:"
    echo "   http://localhost:8080/ui/"
    echo ""
    echo "Logs:"
    echo "   $COMPOSE logs -f"
fi
