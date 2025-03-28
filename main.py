import os
import argparse
import sys
from getpass import getpass
from agent import Agent

def setup_api_key():
    """Set up the API key if not already in environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("🔑 GEMINI_API_KEY environment variable not found.")
        api_key = getpass("🔐 Please enter your Gemini API key: ")
        os.environ["GEMINI_API_KEY"] = api_key
    
    return api_key

def main():
    parser = argparse.ArgumentParser(description='Gemini AI Agent with Chat History & Tools')
    parser.add_argument('--api-key', help='Gemini API key (if not provided, will use GEMINI_API_KEY env var)')
    parser.add_argument('--debug', action='store_true', help='Start with debug mode enabled')
    args = parser.parse_args()
    
    api_key = args.api_key or setup_api_key()
    
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