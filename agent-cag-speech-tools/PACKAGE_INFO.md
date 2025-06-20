# Agent CAG Speech Tools Package

This directory contains a complete, standalone package for the Agent CAG Speech Tools that can be easily extracted into its own repository.

## Package Contents

| File | Description | Executable |
|------|-------------|------------|
| `README.md` | Main documentation with usage examples | ❌ |
| `agent_speak.sh` | Bash script for speech generation | ✅ |
| `agent_speak.py` | Python script with advanced features | ❌ |
| `requirements.txt` | Python dependencies | ❌ |
| `setup.sh` | Automated setup script | ✅ |
| `examples.sh` | Interactive examples demonstration | ✅ |
| `SPEECH_TOOLS_README.md` | Detailed technical documentation | ❌ |
| `PACKAGE_INFO.md` | This file | ❌ |

## Quick Start

1. **Setup**: `./setup.sh`
2. **Basic Usage**: `./agent_speak.sh "Hello world"`
3. **Sardaukar**: `./agent_speak.sh "Hello world" --sardaukar`
4. **Python**: `python3 agent_speak.py "Hello world"`
5. **Examples**: `./examples.sh`

## Repository Extraction

To extract this as a standalone repository:

```bash
# Copy the entire directory
cp -r agent-cag-speech-tools /path/to/new/location

# Initialize git repository
cd /path/to/new/location
git init
git add .
git commit -m "Initial commit: Agent CAG Speech Tools"

# Add remote and push
git remote add origin https://github.com/username/agent-cag-speech-tools.git
git push -u origin main
```

## Dependencies

### System Dependencies
- `sox` - Audio playback
- `curl` - HTTP requests
- `python3` - Python runtime
- `pip3` - Python package manager

### Python Dependencies
- `requests>=2.25.0` - HTTP client library

## Integration

These tools are designed to work with the [Agent CAG](https://github.com/prettygoodapps/agent-cag) system:

- **Agent CAG API** (port 8000) - Main orchestration
- **TTS Service** (port 8003) - Text-to-speech conversion
- **Sardaukar Translator** (port 8004) - Language translation

## Features

✅ **Two interfaces**: Shell script and Python script  
✅ **Sardaukar translation**: Fictional language support  
✅ **Automatic audio playback**: Generated speech plays automatically  
✅ **Service health checking**: Validates Agent CAG services are running  
✅ **Error handling**: Comprehensive error messages and recovery  
✅ **Easy setup**: Automated installation script  
✅ **Interactive examples**: Guided demonstration script  
✅ **Standalone package**: Can be extracted as independent repository  

## Version Information

- **Created**: 2025-06-20
- **Agent CAG Compatibility**: v1.0.0+
- **Python Version**: 3.6+
- **Shell**: Bash 4.0+

## License

Same as the main Agent CAG project.