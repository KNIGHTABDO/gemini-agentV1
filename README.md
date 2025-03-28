# 🤖 Gemini 2.5 Pro AI Agent

A powerful local AI agent built by [ABDO (KNIGHT)](https://github.com/KNIGHTABDO) that leverages Google's Gemini 2.5 Pro model with chat history support, tool integration, web search capabilities, and file creation tools. This agent can search the web, extract page content, create files, and provide comprehensive responses to user queries.

<div align="center">
  <img src="https://api.dicebear.com/7.x/bottts/svg?seed=gemini&backgroundColor=1e1e2e" width="200" alt="Gemini Agent Logo">
</div>

## ✨ Features

- 🏠 **Local Execution** - Runs locally using Python
- 💬 **Chat History** - Maintains conversation history
- 🔄 **Error Handling** - Robust error handling with automatic retries
- 🧰 **Tool Integration** - Flexible tool execution framework
- 🌐 **Web Search** - Searches multiple engines (Google, Bing, DuckDuckGo)
- 📄 **Page Content Extraction** - Visits web pages to gather detailed information
- 📝 **File Creation** - Generates files with code, text, or other content
- 🐞 **Debug Mode** - Toggle detailed logging for troubleshooting
- 💻 **CLI and Web Interface** - Choose your preferred interface
- 📸 **Screenshots** - Captures search results and web pages

## 🚀 Latest Enhancements

- **Creator Identity**: The agent now knows it was created by ABDO (KNIGHT)
- **Web Interface**: Beautiful dark-themed web UI using Gradio
- **File Creation Tool**: Generate code and content files from conversations
- **Multi-Engine Search**: Searches across Google, Bing, and DuckDuckGo
- **Improved Error Recovery**: Better fallback strategies when things go wrong
- **Page Content Extraction**: Gets detailed text from top search results
- **Screenshot Gallery**: View results visually in the web interface

## 📋 Prerequisites

- Python 3.8 or higher
- Google Gemini API key (can be obtained from [Google AI Studio](https://aistudio.google.com/))

## 📦 Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/gemini-agentV1.git
cd gemini-agentV1
```

2. Install the required packages:

```bash
pip install -r requirements.txt
```

## 🔧 Usage

1. Set your Gemini API key as an environment variable:

```bash
# On Windows
set GEMINI_API_KEY=your-api-key-here

# On macOS/Linux
export GEMINI_API_KEY=your-api-key-here
```

Alternatively, you can provide the API key when prompted.

2. Run the agent using the command line:

```bash
python main.py
```

3. Or launch the web interface:

```bash
python main.py --web
```

4. Interact with the agent:
   - Type your questions or commands
   - Type `debug` to toggle debug mode (shows detailed logs)
   - Type `reset` to clear the conversation history
   - Type `web` to launch the web interface from command line
   - Type `exit` or `quit` to end the session

## 🧠 How It Works

The agent processes user input in the following way:

1. The user's message is sent to the Gemini 2.5 Pro model
2. The agent parses the response to identify if any tools need to be executed
3. If tools are requested, the agent executes them and gathers the results
4. The tool results are sent back to Gemini for analysis and to generate a final response
5. The agent extracts the main response, removing any "thinking" sections or tool request markers
6. The final, clean response is presented to the user

### 🔍 Web Search Capabilities

The agent includes powerful web search functionality:

- Searches multiple engines (Google, Bing, DuckDuckGo)
- Automatically extracts and processes content from top search results
- Stores screenshots of search results and page content for reference
- Handles failures gracefully with fallback mechanisms

### 📁 File Creation

The agent can create files based on your requests:

- Code files with appropriate syntax highlighting
- Text documents with formatted content
- Markdown files for documentation
- JSON, XML, and other data formats
- Files are saved in the OUTPUTS directory

## 🛠️ Extending with New Tools

The project uses a flexible tool architecture that makes it easy to add new capabilities:

1. Create a new class that inherits from the `Tool` base class in `tools.py`
2. Implement the `name`, `description`, and `execute` methods
3. Register your tool in the `Agent` class by adding it to the tool registry in the `__init__` method

Example:

```python
class WeatherTool(Tool):
    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Get weather information for a location"

    def execute(self, location: str) -> Dict[str, Any]:
        # Implementation here
        pass

# Register in Agent.__init__
self.tool_registry.register_tool(WeatherTool())
```

## 📂 Project Structure

- `main.py` - Entry point with CLI and web interface launching
- `agent.py` - Core agent implementation with Gemini integration
- `tools.py` - Tool implementations and registry
- `web_interface.py` - Gradio-based web UI
- `OUTPUTS/` - Where generated files are saved
- `page_screenshots/` - Stores screenshots of visited web pages
- `search_screenshots/` - Stores screenshots of search results

## 👨‍💻 About the Creator

This project was created by ABDO (KNIGHT), a web developer who expanded into Python development to build this AI agent. The agent represents a fusion of web development expertise with new Python skills to create a powerful AI assistant.

### Connect with ABDO

- GitHub: [KNIGHTABDO](https://github.com/KNIGHTABDO)
- Instagram: [@jup0e](https://www.instagram.com/jup0e)

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

MIT
