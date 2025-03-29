"""
Gemini AI Agent V1
-----------------
A powerful local AI agent built with Google's Gemini 2.5 Pro model

Created by: ABDO (KNIGHT)
Repository: https://github.com/KNIGHTABDO/gemini-agentV1
Contact: 
    - GitHub: https://github.com/KNIGHTABDO
    - Instagram: @jup0e

Version: 1.0.0
Date: March 28, 2025
License: MIT
"""

import os
import argparse
import sys
import re
from getpass import getpass
from agent import Agent
from dotenv import load_dotenv
import shutil
import time

def setup_api_key():
    """Set up the API key if not already in environment variables."""
    # Try to load API key from .env file first
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("🔑 GEMINI_API_KEY environment variable not found.")
        api_key = getpass("🔐 Please enter your Gemini API key: ")
        os.environ["GEMINI_API_KEY"] = api_key
    
    return api_key

def process_file_path(file_path):
    """Process a file path (potentially from drag-and-drop) and return the cleaned path."""
    import time
    
    # Strip quotes that might be added when dragging files to terminal
    file_path = file_path.strip().strip('"\'')
    
    # Check if file exists
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    # Check if it's a file and not a directory
    if not os.path.isfile(file_path):
        return None, f"Not a file: {file_path}"
    
    # Check file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    supported_extensions = [".pdf", ".txt", ".text", ".docx", ".pptx", ".xlsx", ".csv"]
    if ext not in supported_extensions:
        return None, f"Unsupported file type: {ext}. Supported formats: {', '.join(supported_extensions)}"
    
    # Create UPLOADS directory if it doesn't exist
    uploads_dir = "UPLOADS"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    # Generate a destination path
    filename = os.path.basename(file_path)
    timestamp = int(time.time())
    dest_filename = f"{timestamp}_{filename}"
    dest_path = os.path.join(uploads_dir, dest_filename)
    
    # Copy the file to our uploads directory
    try:
        shutil.copy2(file_path, dest_path)
        return dest_path, None
    except Exception as e:
        return None, f"Error copying file: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Gemini AI Agent with Chat History & Tools')
    parser.add_argument('--api-key', help='Gemini API key (if not provided, will use GEMINI_API_KEY env var)')
    parser.add_argument('--debug', action='store_true', help='Start with debug mode enabled')
    parser.add_argument('--web', action='store_true', help='Launch the web interface')
    parser.add_argument('--share', action='store_true', help='Create a public link for sharing (only with --web)')
    args = parser.parse_args()
    
    api_key = args.api_key or setup_api_key()
    
    # Launch the web interface if requested
    if args.web:
        try:
            from web_interface import WebInterface
            print("🌐 Launching Gemini Agent Web Interface...")
            interface = WebInterface(api_key=api_key)
            return interface.launch(share=args.share)
        except ImportError as e:
            if "gradio" in str(e):
                print("❌ Error: Gradio is required for the web interface.")
                print("📦 Please install it with: pip install gradio")
                return 1
            else:
                print(f"❌ Error launching web interface: {str(e)}")
                return 1
    
    try:
        print("🚀 Initializing Gemini Agent...")
        agent = Agent(api_key=api_key)
        
        # Set initial debug mode if specified via command line
        if args.debug:
            agent.debug_mode = True
            print("🐞 Debug mode is enabled.")
        
        print("\n" + "="*50)
        print("🤖 GEMINI AI AGENT v1")
        print("="*50)
        print("📝 Type 'exit' or 'quit' to end the conversation.")
        print("🔄 Type 'reset' to start a new conversation.")
        print("🐞 Type 'debug' to toggle debug mode on/off.")
        print("🌐 Type 'web' to launch the web interface.")
        print("="*50 + "\n")
        
        while True:
            user_input = input("\n💬 You: ")
            
            if user_input.lower() in ['exit', 'quit']:
                print("\n👋 Goodbye! Thanks for using Gemini Agent.")
                break
            
            if user_input.lower() == 'reset':
                agent.reset_conversation()
                print("🔄 Conversation history has been reset.")
                continue
            
            if user_input.lower() == 'debug':
                result = agent.toggle_debug_mode()
                if agent.debug_mode:
                    print("🐞 Debug mode enabled.")
                else:
                    print("🚫 Debug mode disabled.")
                continue
            
            if user_input.lower() == 'web':
                print("\n🌐 Launching web interface...")
                try:
                    from web_interface import WebInterface
                    interface = WebInterface(api_key=api_key)
                    print("🌐 Web interface is starting in your browser...")
                    interface.launch(share=False)
                    print("\n🔙 Back to console mode.")
                    continue
                except ImportError as e:
                    if "gradio" in str(e):
                        print("❌ Error: Gradio is required for the web interface.")
                        print("📦 Please install it with: pip install gradio")
                    else:
                        print(f"❌ Error launching web interface: {str(e)}")
                    continue
            
            # Check if input looks like a file path (common file extensions or full paths)
            if (os.path.exists(user_input) or 
                re.search(r'["\']?.*\.(pdf|txt|text|docx|pptx|xlsx|csv)["\']?', user_input, re.IGNORECASE)):
                
                # Process the potential file path
                processed_path, error = process_file_path(user_input)
                
                if error:
                    print(f"\n❌ {error}")
                    continue
                
                # Add context about the file to the message
                message = f"I've uploaded a file: {os.path.basename(processed_path)} (Located at: {processed_path}). Please analyze this document."
                
                print(f"\n📄 File uploaded successfully: {os.path.basename(processed_path)}")
                print("\n🧠 Analyzing document...")
                
                try:
                    response = agent.process_message(message)
                    print(f"\n🤖 Gemini: {response}")
                    continue
                except Exception as e:
                    print(f"\n❌ Error analyzing document: {str(e)}")
                    continue
            
            # Always show "Thinking..." regardless of debug mode
            print("\n🧠 Thinking...")
            
            try:
                response = agent.process_message(user_input)
                print(f"\n🤖 Gemini: {response}")
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    except Exception as e:
        print(f"\n❌ Error initializing agent: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())