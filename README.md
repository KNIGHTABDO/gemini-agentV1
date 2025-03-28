# Gemini 2.5 Pro AI Agent

A powerful local AI agent that leverages Google's Gemini 2.5 Pro model with chat history support, tool integration, and web search capabilities. This agent can search the web, extract page content, and provide comprehensive responses to user queries.

## Features

- Runs locally using Python
- Maintains conversation history
- Robust error handling with automatic retries
- Tool execution framework with web search capabilities
- Extracts and visits web pages to gather detailed information
- Debug mode for detailed logging
- Clean response formatting by removing "thinking" sections
- Command-line interface for easy interaction

## Prerequisites

- Python 3.8 or higher
- Google Gemini API key (can be obtained from [Google AI Studio](https://ai.google.dev/))

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/gemini-2.0pro-agent.git
cd gemini-2.0pro-agent
```

2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Set your Gemini API key as an environment variable:

```bash
# On Windows
set GEMINI_API_KEY=your-api-key-here

# On macOS/Linux
export GEMINI_API_KEY=your-api-key-here
```

Alternatively, you can provide the API key when prompted.

2. Run the agent:

```bash
python main.py
```

3. Interact with the agent through the command line:
   - Type your questions or commands
   - Type `debug` to toggle debug mode (shows detailed logs in console)
   - Type `reset` to clear the conversation history
   - Type `exit` or `quit` to end the session

## How It Works

The agent processes user input in the following way:

1. The user's message is sent to the Gemini 2.5 Pro model
2. The agent parses the response to identify if any tools need to be executed
3. If tools are requested, the agent executes them and gathers the results
4. The tool results are sent back to Gemini for analysis and to generate a final response
5. The agent extracts the main response, removing any "thinking" sections or tool request markers
6. The final, clean response is presented to the user

### Web Search Capabilities

The agent includes powerful web search functionality:

- Can search using popular search engines
- Automatically extracts and processes content from top search results
- Stores screenshots of search results and page content for reference
- Handles failures gracefully with fallback mechanisms

## Extending with New Tools

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

## Project Structure

- `main.py` - Entry point that sets up the command-line interface
- `agent.py` - Core agent implementation with Gemini integration
- `tools.py` - Tool implementations and registry
- `page_screenshots/` - Stores HTML snapshots of visited web pages
- `search_screenshots/` - Stores HTML snapshots of search results

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

MIT
