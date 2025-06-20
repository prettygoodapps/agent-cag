#!/usr/bin/env python3
"""
Agent CAG Speech Generator
A Python tool to generate speech from text using the Agent CAG system.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional

import requests


class AgentSpeaker:
    """Agent CAG Speech Generator."""
    
    def __init__(self, api_url: str = "http://localhost:8000", tts_url: str = "http://localhost:8003"):
        self.api_url = api_url
        self.tts_url = tts_url
        self.temp_dir = tempfile.gettempdir()
    
    def check_services(self) -> bool:
        """Check if Agent CAG services are running."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def generate_speech(self, text: str, use_sardaukar: bool = False, user_id: Optional[str] = None) -> dict:
        """Generate speech from text using Agent CAG API."""
        if user_id is None:
            user_id = f"python-cli-{int(time.time())}"
        
        payload = {
            "text": text,
            "user_id": user_id,
            "generate_speech": True,
            "use_sardaukar": use_sardaukar
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/query",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to generate speech: {e}")
    
    def download_audio(self, audio_url: str) -> str:
        """Download audio file from TTS service."""
        audio_file = os.path.join(self.temp_dir, f"agent_speech_{int(time.time())}.wav")
        
        try:
            response = requests.get(f"{self.tts_url}{audio_url}", timeout=30)
            response.raise_for_status()
            
            with open(audio_file, 'wb') as f:
                f.write(response.content)
            
            return audio_file
        except requests.RequestException as e:
            raise Exception(f"Failed to download audio: {e}")
    
    def play_audio(self, audio_file: str) -> None:
        """Play audio file using sox."""
        try:
            # Check if sox/play is available
            subprocess.run(["which", "play"], check=True, capture_output=True)
            
            # Play the audio file
            subprocess.run(["play", audio_file], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            raise Exception("Sox/play not found. Install with: sudo apt install sox")
        except Exception as e:
            raise Exception(f"Failed to play audio: {e}")
    
    def speak(self, text: str, use_sardaukar: bool = False, user_id: Optional[str] = None) -> dict:
        """Complete speech generation and playback pipeline."""
        print(f"🎤 Generating speech for: \"{text}\"")
        if use_sardaukar:
            print("🌌 Using Sardaukar translation")
        
        # Check services
        if not self.check_services():
            raise Exception(f"Agent CAG API service is not running on {self.api_url}")
        
        # Generate speech
        print("📡 Sending request to Agent CAG...")
        response = self.generate_speech(text, use_sardaukar, user_id)
        
        # Extract response data
        response_text = response.get("text", "")
        audio_url = response.get("audio_url", "")
        
        if not audio_url:
            raise Exception("No audio URL received from API")
        
        print(f"💬 AI Response: {response_text}")
        
        # Download and play audio
        print("🔊 Downloading and playing audio...")
        audio_file = self.download_audio(audio_url)
        
        try:
            print("▶️  Playing audio...")
            self.play_audio(audio_file)
            print("✅ Done!")
        finally:
            # Clean up
            if os.path.exists(audio_file):
                os.remove(audio_file)
        
        return response


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Agent CAG Speech Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 agent_speak.py "Hello, how are you?"
  python3 agent_speak.py "Tell me about the weather" --sardaukar
  python3 agent_speak.py "What is the meaning of life?" -s --user-id my-user
        """
    )
    
    parser.add_argument("text", help="Text to convert to speech")
    parser.add_argument(
        "--sardaukar", "-s", 
        action="store_true", 
        help="Translate to Sardaukar language"
    )
    parser.add_argument(
        "--user-id", "-u", 
        help="User ID for the request (default: auto-generated)"
    )
    parser.add_argument(
        "--api-url", 
        default="http://localhost:8000", 
        help="Agent CAG API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--tts-url", 
        default="http://localhost:8003", 
        help="TTS service URL (default: http://localhost:8003)"
    )
    parser.add_argument(
        "--json", "-j", 
        action="store_true", 
        help="Output response as JSON instead of playing audio"
    )
    
    args = parser.parse_args()
    
    try:
        speaker = AgentSpeaker(args.api_url, args.tts_url)
        
        if args.json:
            # Just generate and return JSON response
            response = speaker.generate_speech(args.text, args.sardaukar, args.user_id)
            print(json.dumps(response, indent=2))
        else:
            # Full speech generation and playback
            speaker.speak(args.text, args.sardaukar, args.user_id)
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()