import os
import sys
import gradio as gr
from agent import Agent

class WebInterface:
    def __init__(self, api_key=None):
        """Initialize the web interface with an optional API key."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set or provided explicitly")
        
        self.agent = Agent(api_key=self.api_key)
        self.chat_history = []
    
    def respond(self, message, history):
        """Process a message and update the chat history."""
        if not message:
            return "Please enter a message."
        
        # Special commands
        if message.lower() == 'reset':
            self.agent.reset_conversation()
            self.chat_history = []
            return "🔄 Conversation history has been reset."
        
        if message.lower() == 'debug':
            result = self.agent.toggle_debug_mode()
            if self.agent.debug_mode:
                return "🐞 Debug mode enabled."
            else:
                return "🚫 Debug mode disabled."
        
        # Process the message with the agent
        try:
            response = self.agent.process_message(message)
            return response
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def launch(self, share=False):
        """Launch the web interface."""
        # Custom CSS for dark mode and better styling
        custom_css = """
        :root {
            --primary-color: #7e57c2;
            --secondary-color: #4f3b78;
            --background-color: #1e1e2e;
            --container-color: #2d2d3f;
            --text-color: #e2e2e2;
            --border-color: #444466;
            --accent-color: #9d68fe;
            --error-color: #ff5757;
            --success-color: #42d392;
            --card-radius: 12px;
            --shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }
        
        body.dark {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        
        .dark .gradio-container {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        
        .dark .gr-button-primary {
            background-color: var(--primary-color) !important;
            border: none !important;
        }
        
        .dark .gr-button {
            color: var(--text-color);
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
        }
        
        .dark .gr-button:hover {
            background-color: var(--secondary-color);
        }
        
        .dark .gr-box, .dark .gr-form, .dark .gr-panel {
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
            border-radius: var(--card-radius);
            box-shadow: var(--shadow);
        }
        
        .dark .gr-input, .dark .gr-textarea {
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            border-radius: 8px;
        }
        
        .dark .gr-input:focus, .dark .gr-textarea:focus {
            border-color: var(--primary-color);
        }
        
        .dark .gr-accordion {
            border: 1px solid var(--border-color);
            background-color: var(--container-color);
        }
        
        .dark .gr-chatbot {
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow);
            border-radius: var(--card-radius);
        }

        .dark .gr-chatbot .user-message {
            background-color: var(--primary-color);
            color: white;
            border-radius: 14px 14px 2px 14px;
            padding: 10px 14px;
            margin: 8px 0;
        }
        
        .dark .gr-chatbot .bot-message {
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            border-radius: 14px 14px 14px 2px;
            padding: 10px 14px;
            margin: 8px 0;
        }
        
        .header-container {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
        }
        
        .header-logo {
            width: 40px;
            height: 40px;
            margin-right: 10px;
        }
        
        .header-text {
            margin: 0;
            padding: 0;
            font-weight: 700;
        }
        
        .command-box {
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
            border-radius: var(--card-radius);
            padding: 10px 15px;
            margin-bottom: 10px;
        }
        
        .command-title {
            font-weight: 600;
            color: var(--primary-color);
            margin-bottom: 5px;
        }
        
        .screenshot-gallery {
            margin-top: 15px;
        }
        
        /* Footer styling */
        footer {
            display: none !important;
        }
        
        /* Custom buttons */
        .custom-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            border-radius: 8px;
            padding: 8px 15px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .button-primary {
            background-color: var(--primary-color);
            color: white;
        }
        
        .button-secondary {
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
        }
        
        /* Message input styling */
        .message-input-container {
            margin-top: 15px;
            position: relative;
        }
        
        .dark .message-input {
            background-color: var(--container-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px;
            font-size: 16px;
            transition: border-color 0.3s ease;
            width: 100%;
        }
        
        .dark .message-input:focus {
            border-color: var(--primary-color);
            outline: none;
            box-shadow: 0 0 0 2px rgba(126, 87, 194, 0.3);
        }
        """
        
        # Create a Gradio interface with dark mode theme
        chatbot = gr.Chatbot(
            label="Chat",
            bubble_full_width=False,
            avatar_images=(
                "https://api.dicebear.com/7.x/identicon/svg?seed=user&backgroundColor=7e57c2", 
                "https://api.dicebear.com/7.x/bottts/svg?seed=gemini&backgroundColor=1e1e2e"
            ),
            type="messages",
            height=500,
        )
        
        # Create the interface components with dark theme
        with gr.Blocks(
            title="Gemini Agent",
            theme="soft",
            css=custom_css
        ) as interface:
            # Dark mode by default
            interface.load(lambda: None, js="""() => { document.body.classList.add('dark'); }""")
            
            # Header with logo
            with gr.Row(elem_classes="header-container"):
                gr.Image(
                    "https://api.dicebear.com/7.x/bottts/svg?seed=gemini&backgroundColor=1e1e2e",
                    height=40, width=40, 
                    elem_classes="header-logo"
                )
                gr.Markdown("# 🤖 Gemini Agent", elem_classes="header-text")
            
            # Main chat area and sidebar
            with gr.Row():
                # Chat column
                with gr.Column(scale=4):
                    gr.Markdown("Ask questions or give commands to interact with Gemini Agent.")
                    chatbot.render()
                    
                    # Input area with buttons
                    with gr.Group():
                        msg = gr.Textbox(
                            placeholder="Type your message here...",
                            label="Your Message",
                            scale=4,
                            show_label=False,
                            container=False,
                            elem_classes="message-input"
                        )
                        
                        with gr.Row():
                            submit_btn = gr.Button("🚀 Send", variant="primary", elem_classes="custom-button button-primary")
                            clear_btn = gr.Button("🗑️ Clear", elem_classes="custom-button button-secondary")
                            reset_btn = gr.Button("🔄 Reset Chat", elem_classes="custom-button button-secondary")
                
                # Sidebar
                with gr.Column(scale=1):
                    # Commands section
                    with gr.Group(elem_classes="command-box"):
                        gr.Markdown("### 🛠️ Commands", elem_classes="command-title")
                        gr.Markdown("- `reset` - Clear conversation history")
                        gr.Markdown("- `debug` - Toggle debug mode")
                    
                    # Theme toggle
                    theme_toggle = gr.Button("🌓 Toggle Light/Dark Mode")
                    theme_toggle.click(None, js="""
                        () => {
                            document.body.classList.toggle('dark');
                        }
                    """)
                    
                    # Screenshots gallery
                    with gr.Accordion("📸 Screenshots", open=False):
                        gallery = gr.Gallery(
                            label="Recent Screenshots",
                            columns=1,
                            rows=3,
                            object_fit="contain",
                            height="auto",
                            elem_classes="screenshot-gallery"
                        )
                        
                        refresh_btn = gr.Button("🔄 Refresh Screenshots", elem_classes="custom-button button-secondary")
                        refresh_btn.click(self.refresh_screenshots, outputs=gallery)
            
            # Define the new message handler with the updated format
            def message_handler(message, history):
                if message:
                    # Add user message
                    user_msg = {"role": "user", "content": message}
                    
                    # Get bot response
                    bot_response = self.respond(message, history)
                    bot_msg = {"role": "assistant", "content": bot_response}
                    
                    # Return updated history
                    history = history + [user_msg, bot_msg]
                    return "", history
                return "", history
            
            # Define the reset chat handler
            def reset_chat_handler():
                self.agent.reset_conversation()
                self.chat_history = []
                return []
            
            # Connect the handlers
            submit_action = msg.submit(
                message_handler, 
                [msg, chatbot], 
                [msg, chatbot]
            ).then(
                self.refresh_screenshots,
                None,
                gallery
            )
            
            submit_btn.click(
                message_handler, 
                [msg, chatbot], 
                [msg, chatbot]
            ).then(
                self.refresh_screenshots,
                None,
                gallery
            )
            
            clear_btn.click(lambda: "", None, [msg], queue=False)
            
            reset_btn.click(
                reset_chat_handler,
                None,
                [chatbot]
            ).then(
                self.refresh_screenshots,
                None,
                gallery
            )
            
            # Initial refresh of screenshots
            interface.load(self.refresh_screenshots, outputs=gallery)
        
        # Launch the interface
        interface.launch(share=share, server_name="127.0.0.1")
    
    def reset_chat(self):
        """Reset the agent and chat history."""
        self.agent.reset_conversation()
        self.chat_history = []
        return []
    
    def refresh_screenshots(self):
        """Get recent screenshots from the screenshots directories."""
        screenshots = []
        
        # Check page screenshots
        page_dir = "page_screenshots"
        if os.path.exists(page_dir):
            for file in os.listdir(page_dir):
                if file.endswith(".png"):
                    screenshots.append(os.path.join(page_dir, file))
        
        # Check search screenshots
        search_dir = "search_screenshots"
        if os.path.exists(search_dir):
            for file in os.listdir(search_dir):
                if file.endswith(".png"):
                    screenshots.append(os.path.join(search_dir, file))
        
        # Sort by modification time (newest first)
        screenshots.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Return up to 5 most recent screenshots
        return screenshots[:5]

def main():
    """Main function to launch the web interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Launch Gemini Agent Web Interface')
    parser.add_argument('--api-key', help='Gemini API key (if not provided, will use GEMINI_API_KEY env var)')
    parser.add_argument('--share', action='store_true', help='Create a public link for sharing')
    args = parser.parse_args()
    
    try:
        interface = WebInterface(api_key=args.api_key)
        print("🌐 Launching Gemini Agent Web Interface...")
        interface.launch(share=args.share)
    except Exception as e:
        print(f"❌ Error initializing web interface: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())