#!/bin/bash

# Agent CAG Speech Tools Setup Script
# This script installs dependencies and sets up the speech tools

set -e

echo "🔧 Setting up Agent CAG Speech Tools..."

# Check if running on supported system
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  Warning: This setup script is designed for Linux systems."
    echo "   You may need to manually install dependencies on other systems."
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y sox curl python3 python3-pip
elif command -v yum &> /dev/null; then
    # RHEL/CentOS/Fedora
    sudo yum install -y sox curl python3 python3-pip
elif command -v pacman &> /dev/null; then
    # Arch Linux
    sudo pacman -S sox curl python python-pip
else
    echo "❌ Unsupported package manager. Please install manually:"
    echo "   - sox (for audio playback)"
    echo "   - curl (for HTTP requests)"
    echo "   - python3 and pip3 (for Python script)"
    exit 1
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
if [[ -f "requirements.txt" ]]; then
    pip3 install -r requirements.txt
else
    pip3 install requests
fi

# Make shell script executable
echo "🔐 Making shell script executable..."
chmod +x agent_speak.sh

# Test installations
echo "🧪 Testing installations..."

# Test sox
if command -v play &> /dev/null; then
    echo "✅ Sox (audio playback) installed successfully"
else
    echo "❌ Sox installation failed"
    exit 1
fi

# Test curl
if command -v curl &> /dev/null; then
    echo "✅ Curl installed successfully"
else
    echo "❌ Curl installation failed"
    exit 1
fi

# Test Python and requests
if python3 -c "import requests" 2>/dev/null; then
    echo "✅ Python and requests library installed successfully"
else
    echo "❌ Python or requests installation failed"
    exit 1
fi

echo ""
echo "🎉 Setup complete! Agent CAG Speech Tools are ready to use."
echo ""
echo "📋 Next steps:"
echo "1. Start Agent CAG services:"
echo "   cd /path/to/agent-cag"
echo "   sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d"
echo ""
echo "2. Test the tools:"
echo "   ./agent_speak.sh \"Hello, this is a test\""
echo "   python3 agent_speak.py \"Hello, this is a test\""
echo ""
echo "3. Try Sardaukar translation:"
echo "   ./agent_speak.sh \"Welcome to Agent CAG\" --sardaukar"
echo ""
echo "📖 For more information, see README.md"