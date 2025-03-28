import os
import json
import logging
import time
import random
from typing import Dict, List, Any, Optional, Tuple
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

from tools import ToolRegistry, RequestsWebSearchTool  # Changed import here

# Configure logging - only log to file by default, not to console
file_handler = logging.FileHandler("agent_debug.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Create a console handler but don't add it yet - we'll add it when debug mode is enabled
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Set up the root logger with just the file handler
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler]
)
logger = logging.getLogger("agent")

class Agent:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini agent."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set or provided explicitly")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-pro-exp-03-25"
        self.conversation_history = []
        self.tool_registry = ToolRegistry()
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.debug_mode = False  # New attribute to control debug output
        
        # Register the requests-based web search tool instead of the Playwright one
        self.tool_registry.register_tool(RequestsWebSearchTool())
    
    def toggle_debug_mode(self) -> str:
        """Toggle debug mode on/off and update logger configuration."""
        self.debug_mode = not self.debug_mode
        
        # Update the logger configuration based on debug mode
        if self.debug_mode:
            # Add console handler if debug mode is enabled
            if console_handler not in logger.handlers:
                logger.addHandler(console_handler)
                # Also add to root logger and tool logger
                logging.getLogger().addHandler(console_handler)
                logging.getLogger("tools").addHandler(console_handler)
                logging.getLogger("httpx").addHandler(console_handler)
                logging.getLogger("google_genai").addHandler(console_handler)
        else:
            # Remove console handler if debug mode is disabled
            if console_handler in logger.handlers:
                logger.removeHandler(console_handler)
                # Also remove from root logger and tool logger
                logging.getLogger().removeHandler(console_handler)
                logging.getLogger("tools").removeHandler(console_handler)
                logging.getLogger("httpx").removeHandler(console_handler)
                logging.getLogger("google_genai").removeHandler(console_handler)
        
        return f"Debug mode {'enabled' if self.debug_mode else 'disabled'}"
        
    def add_user_message(self, message: str) -> None:
        """Add a user message to the conversation history."""
        self.conversation_history.append({"role": "user", "parts": [{"text": message}]})
    
    def add_assistant_message(self, message: str) -> None:
        """Add an assistant message to the conversation history."""
        self.conversation_history.append({"role": "model", "parts": [{"text": message}]})
    
    def format_conversation_for_api(self) -> List[types.Content]:
        """Format the conversation history for the API request."""
        contents = []
        
        for message in self.conversation_history:
            role = message["role"]
            # Fix: Create Part objects correctly
            parts = []
            for part in message["parts"]:
                # Create a Part object with text content
                parts.append(types.Part(text=part["text"]))
            
            if role == "user":
                contents.append(types.Content(role="user", parts=parts))
            elif role == "model":
                contents.append(types.Content(role="model", parts=parts))
        
        return contents
    
    def parse_tool_requests(self, response: str) -> List[Dict[str, Any]]:
        """Parse tool calls from the response with improved parsing."""
        # Look for different possible formats for tool requests
        formats = [
            ("[TOOL_REQUESTS]", "[/TOOL_REQUESTS]"),
            ("<tool_requests>", "</tool_requests>"),
            ("I need to use the following tools:", "\n\n"),
            ("I'll search for", "\n\n")
        ]
        
        tool_requests = []
        
        # Try all possible formats
        for start_marker, end_marker in formats:
            tool_section_start = response.find(start_marker)
            
            # If we find this format
            if tool_section_start != -1:
                if end_marker == "\n\n":
                    # For free-form formats, search for double newline after the start marker
                    tool_section_end = response.find(end_marker, tool_section_start + len(start_marker))
                    if tool_section_end == -1:  # If no double newline, go to end of text
                        tool_section_end = len(response)
                else:
                    # For explicit end markers
                    tool_section_end = response.find(end_marker, tool_section_start)
                    if tool_section_end == -1:
                        continue  # Skip if no matching end marker
                
                # Extract the tool section
                tool_section = response[tool_section_start + len(start_marker):tool_section_end].strip()
                logger.info(f"Found tool section with format {start_marker}: {tool_section}")
                
                # Handle structured JSON format
                if start_marker == "[TOOL_REQUESTS]" or start_marker == "<tool_requests>":
                    for line in tool_section.split("\n"):
                        line = line.strip()
                        if line:
                            try:
                                # Make sure we're dealing with valid JSON by ensuring it starts with {
                                if line.startswith("{"):
                                    tool_request = json.loads(line)
                                    
                                    # Keep the original query exactly as is (don't modify the model's response)
                                    tool_requests.append(tool_request)
                                    logger.info(f"Parsed tool request: {tool_request}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing JSON: {str(e)} in line: '{line}'")
                                continue
                
                # Handle free-form text for web search
                elif "search" in start_marker.lower() or "search" in tool_section.lower():
                    # Extract the search query
                    search_query = tool_section
                    
                    # Clean up the query if needed, but preserve the core query
                    search_query = search_query.replace("I need to search for", "")
                    search_query = search_query.replace("I'll search for", "")
                    search_query = search_query.replace("Let me search for", "")
                    search_query = search_query.strip()
                    
                    if search_query:
                        tool_requests.append({
                            "tool_name": "web_search",
                            "parameters": {"query": search_query}
                        })
                        logger.info(f"Created web search tool request with query: {search_query}")
        
        # If we couldn't find structured tool requests but the response mentions searching
        if not tool_requests and "search" in response.lower():
            # Try to extract a search query from the response
            search_indicators = [
                "I'll search for",
                "I need to search for",
                "Let me search for",
                "I should search for",
                "I need to find information about",
                "Let me look up"
            ]
            
            for indicator in search_indicators:
                if indicator.lower() in response.lower():
                    # Find the case-insensitive position
                    indicator_pos = response.lower().find(indicator.lower())
                    # Calculate real start position using the length of the original indicator
                    start_idx = indicator_pos + len(indicator)
                    
                    # Find end of the query (period, question mark, or newline)
                    end_markers = [".", "?", "\n"]
                    end_positions = [response.find(marker, start_idx) for marker in end_markers]
                    # Filter out -1 (not found)
                    end_positions = [pos for pos in end_positions if pos != -1]
                    
                    if end_positions:
                        end_idx = min(end_positions)
                    else:
                        end_idx = len(response)
                    
                    search_query = response[start_idx:end_idx].strip()
                    
                    if search_query:
                        tool_requests.append({
                            "tool_name": "web_search",
                            "parameters": {"query": search_query}
                        })
                        logger.info(f"Extracted implied search query: {search_query}")
                        break
        
        # If we still don't have tool requests but the user is clearly asking for information
        # about a specific topic, use the exact phrase from the user's message
        if not tool_requests and self.conversation_history:
            last_user_message = None
            for message in reversed(self.conversation_history):
                if message["role"] == "user":
                    last_user_message = message["parts"][0]["text"]
                    break
            
            if last_user_message:
                # Check if this is an information request
                info_phrases = ["about", "information on", "tell me about", "what is", "who is", "wanna know"]
                has_info_phrase = False
                matched_phrase = ""
                
                for phrase in info_phrases:
                    if phrase in last_user_message.lower():
                        has_info_phrase = True
                        matched_phrase = phrase
                        break
                
                if has_info_phrase:
                    # Try to extract the exact topic of interest
                    phrase_pos = last_user_message.lower().find(matched_phrase)
                    start_pos = phrase_pos + len(matched_phrase)
                    
                    # Get the rest of the message as the search query, preserving case
                    search_query = last_user_message[start_pos:].strip()
                    
                    if search_query:
                        # Check if it contains "Claude Sonnet 3.7" and use exactly that if found
                        if "claude sonnet 3.7" in search_query.lower():
                            # Preserve case but ensure the search is for the exact model name
                            lower_query = search_query.lower()
                            start_idx = lower_query.find("claude sonnet 3.7")
                            end_idx = start_idx + len("claude sonnet 3.7")
                            
                            # Get the phrase with its original capitalization
                            exact_phrase = search_query[start_idx:end_idx]
                            
                            # Use this exact phrase as the query
                            tool_requests.append({
                                "tool_name": "web_search",
                                "parameters": {"query": exact_phrase}
                            })
                            logger.info(f"Extracted exact model name from user message: {exact_phrase}")
                        else:
                            # Use the user's query as is
                            tool_requests.append({
                                "tool_name": "web_search",
                                "parameters": {"query": search_query}
                            })
                            logger.info(f"Extracted search query from user message: {search_query}")
                
        return tool_requests
    
    def extract_final_response(self, response: str) -> str:
        """Extract the final response, removing the thinking part and tool sections with improved detection."""
        # Save original for debugging
        original_response = response
        
        # Remove tool requests section with multiple formats
        tool_section_formats = [
            ("[TOOL_REQUESTS]", "[/TOOL_REQUESTS]"),
            ("<tool_requests>", "</tool_requests>"),
            ("I need to use the following tools:", "\n\n"),
        ]
        
        for start_marker, end_marker in tool_section_formats:
            tool_section_start = response.find(start_marker)
            
            if tool_section_start != -1:
                if end_marker == "\n\n":
                    # For free-form formats, search for double newline after the start marker
                    tool_section_end = response.find(end_marker, tool_section_start + len(start_marker))
                    if tool_section_end == -1:  # If no double newline, go to end of text
                        tool_section_end = len(response)
                else:
                    # For explicit end markers
                    tool_section_end = response.find(end_marker, tool_section_start)
                    if tool_section_end == -1:
                        continue  # Skip if no matching end marker
                
                tool_section = response[tool_section_start:tool_section_end + len(end_marker)]
                response = response.replace(tool_section, "")
        
        # Remove thinking section (with expanded patterns)
        thinking_patterns = [
            ("<thinking>", "</thinking>"),
            ("[THINKING]", "[/THINKING]"),
            ("(thinking:", ")"),
            ("Thinking:", "\n\n"),
            ("Let me think about this:", "\n\n"),
            ("let me think", "\n\n"),
            ("First, I need to", "\n\n"),
        ]
        
        for start_tag, end_tag in thinking_patterns:
            start_idx = response.lower().find(start_tag.lower())
            
            if start_idx != -1:
                if end_tag == "\n\n":
                    # For free-form thinking, find the next paragraph break
                    end_idx = response.find(end_tag, start_idx + len(start_tag))
                    if end_idx == -1:
                        end_idx = len(response)
                else:
                    # For explicit end tags
                    end_idx = response.lower().find(end_tag.lower(), start_idx + len(start_tag))
                    if end_idx == -1:
                        continue
                
                thinking_section = response[start_idx:end_idx + len(end_tag)]
                response = response.replace(thinking_section, "")
        
        # If we've removed too much, restore the original
        if len(response.strip()) < 20:
            logger.warning("Extracted response too short, using original")
            response = original_response
        
        # Clean up any extra whitespace and return
        return response.strip()
    
    def execute_tools(self, tool_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the requested tools and return the results."""
        tool_results = {}
        
        for tool_request in tool_requests:
            tool_name = tool_request.get("tool_name")
            parameters = tool_request.get("parameters", {})
            
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            
            if tool_name and self.tool_registry.has_tool(tool_name):
                tool = self.tool_registry.get_tool(tool_name)
                try:
                    result = tool.execute(**parameters)
                    tool_results[tool_name] = result
                    logger.info(f"Tool execution successful: {tool_name}")
                    
                    # For web search, if we get results, also try to visit the top result page
                    if tool_name == "web_search" and result.get("status") == "success":
                        results = result.get("results", [])
                        if results and len(results) > 0:
                            top_result = results[0]
                            top_url = top_result.get("link")
                            
                            if top_url:
                                logger.info(f"Attempting to visit top result: {top_url}")
                                web_tool = tool
                                try:
                                    page_content = web_tool.visit_and_summarize(top_url)
                                    tool_results["page_content"] = page_content
                                    logger.info(f"Successfully extracted page content from {top_url}")
                                except Exception as e:
                                    logger.error(f"Error extracting page content: {str(e)}")
                    
                except Exception as e:
                    error_msg = f"Error executing tool {tool_name}: {str(e)}"
                    logger.error(error_msg)
                    tool_results[tool_name] = {"error": error_msg}
            else:
                logger.warning(f"Tool '{tool_name}' not found")
                tool_results[tool_name] = {"error": f"Tool '{tool_name}' not found"}
        
        return tool_results
    
    def process_message(self, message: str) -> str:
        """Process a user message and return the agent's response."""
        self.add_user_message(message)
        
        try:
            # First request to identify tools needed
            if self.debug_mode:
                logger.info(f"Processing user message: {message}")
                print(f"DEBUG: Processing user message: {message}")
            else:
                logger.info(f"Processing user message: {message}")
            
            # Try to generate content with retries
            initial_response = None
            retry_count = 0
            
            while retry_count < self.max_retries:
                try:
                    initial_response = self._generate_content(with_tools=True)
                    break  # Success, exit the retry loop
                except (ServerError, APIError) as e:
                    retry_count += 1
                    logger.warning(f"API error (attempt {retry_count}/{self.max_retries}): {str(e)}")
                    if self.debug_mode:
                        print(f"DEBUG: API error (attempt {retry_count}/{self.max_retries}): {str(e)}")
                    
                    if retry_count >= self.max_retries:
                        logger.error(f"Max retries reached, falling back to direct tool use")
                        if self.debug_mode:
                            print("DEBUG: Max retries reached, falling back to direct tool use")
                        
                        # If we've exhausted retries, assume we need to search for the topic
                        # Extract search terms from the message
                        search_terms = message
                        for prefix in ["about", "information on", "tell me about", "look for"]:
                            if prefix in message.lower():
                                search_terms = message.lower().split(prefix, 1)[1].strip()
                                break
                        
                        logger.info(f"Falling back to direct web search with query: {search_terms}")
                        if self.debug_mode:
                            print(f"DEBUG: Falling back to direct web search with query: {search_terms}")
                        # Create a dummy response that suggests using web search
                        initial_response = f"I'll search for information about {search_terms}"
                    else:
                        # Wait before retrying with jitter to avoid thundering herd
                        sleep_time = self.retry_delay * (1 + random.random())
                        logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                        if self.debug_mode:
                            print(f"DEBUG: Retrying in {sleep_time:.2f} seconds...")
                        time.sleep(sleep_time)
            
            # If we still don't have a response, create a fallback
            if not initial_response:
                initial_response = f"I should search for information about {message}"
                logger.warning(f"Created fallback response for tool detection: {initial_response}")
                if self.debug_mode:
                    print(f"DEBUG: Created fallback response for tool detection: {initial_response}")
            
            # Log the initial response for debugging
            logger.info("===== Initial Model Response =====")
            logger.info(initial_response)
            logger.info("==================================")
            
            if self.debug_mode:
                print("===== DEBUG: Initial Model Response =====")
                print(initial_response)
                print("=========================================")
            
            # Try to parse tool requests
            try:
                tool_requests = self.parse_tool_requests(initial_response)
            except Exception as e:
                logger.error(f"Error parsing tool requests: {str(e)}")
                if self.debug_mode:
                    print(f"DEBUG ERROR: Error parsing tool requests: {str(e)}")
                tool_requests = []
                
                # If we can't parse tools but this seems like an information request,
                # create a default web search
                if any(term in message.lower() for term in ["about", "what is", "who is", "information on"]):
                    tool_requests = [{
                        "tool_name": "web_search",
                        "parameters": {"query": message}
                    }]
                    logger.info(f"Created default web search for information request: {message}")
                    if self.debug_mode:
                        print(f"DEBUG: Created default web search for information request: {message}")
            
            # If tools are requested, execute them and make a second request
            if tool_requests:
                logger.info(f"Found {len(tool_requests)} tool requests to execute")
                if self.debug_mode:
                    print(f"DEBUG: Found {len(tool_requests)} tool requests to execute")
                    for req in tool_requests:
                        print(f"DEBUG: Tool request: {req}")
                
                tool_results = self.execute_tools(tool_requests)
                
                # Create a new message with tool results
                tool_results_message = "Here are the results of the requested tools:\n\n"
                tool_results_message += json.dumps(tool_results, indent=2)
                
                logger.info("Adding tool results to conversation")
                if self.debug_mode:
                    print("DEBUG: Adding tool results to conversation")
                    print("DEBUG: Tool results summary:")
                    for tool_name, result in tool_results.items():
                        status = result.get("status", "unknown")
                        if tool_name == "web_search" and status == "success":
                            num_results = len(result.get("results", []))
                            print(f"DEBUG: Web search found {num_results} results")
                        elif tool_name == "page_content" and status == "success":
                            content_len = len(result.get("content", ""))
                            print(f"DEBUG: Page content extracted ({content_len} characters)")
                
                self.add_user_message(tool_results_message)
                
                # Generate the final response with retries
                retry_count = 0
                final_response = None
                
                while retry_count < self.max_retries:
                    try:
                        logger.info("Generating final response with tool results")
                        if self.debug_mode:
                            print("DEBUG: Generating final response with tool results")
                        final_response = self._generate_content(with_tools=False)
                        break
                    except (ServerError, APIError) as e:
                        retry_count += 1
                        logger.warning(f"API error during final response (attempt {retry_count}/{self.max_retries}): {str(e)}")
                        if self.debug_mode:
                            print(f"DEBUG: API error during final response (attempt {retry_count}/{self.max_retries}): {str(e)}")
                        
                        if retry_count >= self.max_retries:
                            # If we can't get a final response, create one from the tool results
                            logger.error("Max retries reached for final response, creating response from tool results")
                            if self.debug_mode:
                                print("DEBUG: Max retries reached for final response, creating response from tool results")
                            
                            # Extract useful information from tool results to craft a response
                            final_response = "I found some information for you:\n\n"
                            
                            for tool_name, result in tool_results.items():
                                if tool_name == "web_search" and result.get("status") == "success":
                                    search_results = result.get("results", [])
                                    if search_results:
                                        final_response += "From my web search:\n\n"
                                        for i, item in enumerate(search_results[:3], 1):
                                            final_response += f"{i}. {item.get('title', 'No title')}\n"
                                            final_response += f"   {item.get('snippet', 'No description')}\n\n"
                                
                                elif tool_name == "page_content" and result.get("status") == "success":
                                    content = result.get("content", "")
                                    if content:
                                        final_response += "I also found this detailed information:\n\n"
                                        final_response += content[:1000] + "...\n\n"
                            
                            final_response += "That's what I could find based on the search results."
                            break
                        else:
                            # Wait before retrying with jitter
                            sleep_time = self.retry_delay * (1 + random.random())
                            logger.info(f"Retrying final response in {sleep_time:.2f} seconds...")
                            if self.debug_mode:
                                print(f"DEBUG: Retrying final response in {sleep_time:.2f} seconds...")
                            time.sleep(sleep_time)
                
                if final_response:
                    logger.info("Raw final response: " + final_response[:200] + "...")
                    if self.debug_mode:
                        print("DEBUG: Raw final response starts with: " + final_response[:200] + "...")
                    clean_response = self.extract_final_response(final_response)
                else:
                    # Extreme fallback if everything fails
                    clean_response = "I apologize, but I encountered issues processing your request. Here's what I found from the tools I used, but I couldn't generate a complete response."
                    if self.debug_mode:
                        print("DEBUG: Using extreme fallback response due to failures")
            else:
                # No tools needed, use the initial response
                logger.info("No tools requested, using initial response")
                if self.debug_mode:
                    print("DEBUG: No tools requested, using initial response")
                clean_response = self.extract_final_response(initial_response)
            
            logger.info(f"Final clean response: {clean_response[:100]}...")
            if self.debug_mode:
                print(f"DEBUG: Final clean response starts with: {clean_response[:100]}...")
            
            self.add_assistant_message(clean_response)
            return clean_response
        except Exception as e:
            error_message = f"An error occurred while processing your message: {str(e)}"
            logger.error(error_message, exc_info=True)
            if self.debug_mode:
                print(f"DEBUG ERROR: {error_message}")
                import traceback
                print("DEBUG: Traceback:")
                traceback.print_exc()
            
            # If there's an error, try to do a web search anyway if it seems like an information request
            try:
                if any(term in message.lower() for term in ["about", "what is", "who is", "information on"]):
                    logger.info(f"Error occurred but attempting web search for: {message}")
                    if self.debug_mode:
                        print(f"DEBUG: Error occurred but attempting web search for: {message}")
                    
                    web_tool = self.tool_registry.get_tool("web_search")
                    if web_tool:
                        search_results = web_tool.execute(query=message)
                        
                        fallback_response = "I encountered an error, but I was able to search the web for you:\n\n"
                        
                        if search_results.get("status") == "success":
                            results = search_results.get("results", [])
                            for i, result in enumerate(results[:3], 1):
                                fallback_response += f"{i}. {result.get('title', 'No title')}\n"
                                fallback_response += f"   {result.get('snippet', 'No description')}\n\n"
                        
                        fallback_response += "\nI hope this information is helpful despite the technical issues."
                        return fallback_response
            except Exception as search_error:
                logger.error(f"Fallback search also failed: {str(search_error)}")
                if self.debug_mode:
                    print(f"DEBUG ERROR: Fallback search also failed: {str(search_error)}")
            
            return error_message
    
    def _generate_content(self, with_tools: bool = False) -> str:
        """Generate content from the model."""
        contents = self.format_conversation_for_api()
        
        # Configure the generation parameters
        generate_content_config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=64,
            max_output_tokens=65536,
            response_mime_type="text/plain",
        )
        
        # If we're expecting tools to be requested, add a system prompt to guide the model
        if with_tools:
            system_prompt = """
            You are an AI assistant that can use tools to help answer questions. 
            If you need to use tools to answer the user's question, respond in the following format:
            
            [TOOL_REQUESTS]
            {"tool_name": "tool_name", "parameters": {"param1": "value1", "param2": "value2"}}
            [/TOOL_REQUESTS]
            
            Then explain what tools you need and why.
            
            Available tools:
            - web_search: Search the web for information
              Parameters: {"query": "search query string"}
            
            IMPORTANT: Always use the EXACT query that the user provides. Do NOT modify, correct, or expand the user's query.
            For example, if the user asks about "Claude Sonnet 3.7", you must search for "Claude Sonnet 3.7" exactly,
            not "Claude 3.5 Sonnet" or any other variant.
            
            If you don't need to use any tools, just respond normally.
            """
            
            # Add system prompt - Fix: Use Part constructor directly
            contents.insert(0, types.Content(
                role="user", 
                parts=[types.Part(text=system_prompt)]
            ))
        
        # Generate the response
        response_text = ""
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=generate_content_config,
        ):
            response_text += chunk.text
        
        return response_text
    
    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history = []