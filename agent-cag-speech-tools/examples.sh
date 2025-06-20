#!/bin/bash

# Agent CAG Speech Tools Examples
# This script demonstrates various usage patterns

set -e

echo "🎤 Agent CAG Speech Tools - Examples"
echo "===================================="
echo ""

# Check if services are running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Agent CAG services are not running!"
    echo "Please start them first:"
    echo "  cd /path/to/agent-cag"
    echo "  sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d"
    exit 1
fi

echo "✅ Agent CAG services are running"
echo ""

# Example 1: Basic speech generation
echo "📝 Example 1: Basic speech generation"
echo "Command: ./agent_speak.sh \"Hello, welcome to Agent CAG!\""
echo "Press Enter to continue..."
read -r
./agent_speak.sh "Hello, welcome to Agent CAG!"
echo ""

# Example 2: Sardaukar translation
echo "📝 Example 2: Sardaukar translation"
echo "Command: ./agent_speak.sh \"The spice must flow\" --sardaukar"
echo "Press Enter to continue..."
read -r
./agent_speak.sh "The spice must flow" --sardaukar
echo ""

# Example 3: Python tool basic usage
echo "📝 Example 3: Python tool basic usage"
echo "Command: python3 agent_speak.py \"Python speech generation is working\""
echo "Press Enter to continue..."
read -r
python3 agent_speak.py "Python speech generation is working"
echo ""

# Example 4: Python tool with Sardaukar
echo "📝 Example 4: Python tool with Sardaukar translation"
echo "Command: python3 agent_speak.py \"Fear is the mind-killer\" --sardaukar"
echo "Press Enter to continue..."
read -r
python3 agent_speak.py "Fear is the mind-killer" --sardaukar
echo ""

# Example 5: Python tool JSON output
echo "📝 Example 5: Python tool JSON output (no audio)"
echo "Command: python3 agent_speak.py \"JSON output example\" --json"
echo "Press Enter to continue..."
read -r
python3 agent_speak.py "JSON output example" --json
echo ""

# Example 6: Python tool with custom user ID
echo "📝 Example 6: Python tool with custom user ID"
echo "Command: python3 agent_speak.py \"Custom user ID test\" --user-id demo-examples"
echo "Press Enter to continue..."
read -r
python3 agent_speak.py "Custom user ID test" --user-id demo-examples
echo ""

echo "🎉 Examples complete!"
echo ""
echo "💡 Try your own examples:"
echo "  ./agent_speak.sh \"Your text here\""
echo "  ./agent_speak.sh \"Your text here\" --sardaukar"
echo "  python3 agent_speak.py \"Your text here\" [options]"
echo ""
echo "📖 For more options, run:"
echo "  ./agent_speak.sh --help"
echo "  python3 agent_speak.py --help"