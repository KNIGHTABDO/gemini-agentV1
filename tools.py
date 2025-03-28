from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import os
import json
import time
import logging
import urllib.parse
import random
from datetime import datetime
import re

# Configure logging - only log to file by default, not to console
file_handler = logging.FileHandler("agent_debug.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Set up the root logger with just the file handler
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler]
)
logger = logging.getLogger("tools")

# Try to import Playwright (but we'll have an alternative)
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not installed. Will use requests-based search instead.")
    PlaywrightTimeoutError = Exception  # Fallback definition if Playwright is not installed
    PLAYWRIGHT_AVAILABLE = False

# Import for the alternative search solution
try:
    import requests
    from bs4 import BeautifulSoup
    import html
    REQUESTS_AVAILABLE = True
except ImportError:
    logger.warning("Requests or BeautifulSoup not installed. Install with 'pip install requests beautifulsoup4'")
    REQUESTS_AVAILABLE = False

# List of common user agents for browser fingerprinting protection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
]

# Search engines to try
SEARCH_ENGINES = [
    {
        "name": "Google",
        "url": "https://www.google.com/search?q={query}",
        "results_selector": [".g", "[data-hveid]", ".MjjYud", "div[data-sokoban-container]"],
        "title_selector": ["h3", ".LC20lb", "[role='heading']"],
        "link_selector": ["a"],
        "snippet_selector": [".VwiC3b", ".s3v9rd", ".lEBKkf", ".s8bAkb"],
    },
    {
        "name": "Bing",
        "url": "https://www.bing.com/search?q={query}",
        "results_selector": [".b_algo"],
        "title_selector": ["h2"],
        "link_selector": ["a"],
        "snippet_selector": [".b_caption p"],
    },
    {
        "name": "DuckDuckGo",
        "url": "https://duckduckgo.com/?q={query}",
        "results_selector": [".result", ".result__body"],
        "title_selector": [".result__title", ".result__a"],
        "link_selector": [".result__a"],
        "snippet_selector": [".result__snippet"],
    }
]


class Tool(ABC):
    """Base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool, used for identifying it in requests."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool with the given parameters."""
        pass


class PlaywrightScreenshotTool:
    """Helper class to take screenshots with Playwright."""
    
    @staticmethod
    def take_screenshot(url: str, output_path: str, full_page: bool = True, timeout: int = 30000) -> bool:
        """Take a screenshot of a webpage using Playwright."""
        logger.info(f"Taking screenshot of {url} with Playwright")
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available for taking screenshots")
            return False
        
        try:
            with sync_playwright() as p:
                # Launch a browser with a random user agent
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=random.choice(USER_AGENTS)
                )
                
                # Create a new page and navigate to the URL
                page = context.new_page()
                page.set_default_timeout(timeout)
                
                try:
                    page.goto(url, wait_until="networkidle")
                except PlaywrightTimeoutError:
                    logger.warning(f"Timeout waiting for networkidle, continuing anyway")
                    # Try to wait a bit more
                    time.sleep(2)
                
                # Make sure the directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Take the screenshot
                page.screenshot(path=output_path, full_page=full_page)
                logger.info(f"Screenshot saved to {output_path}")
                
                # Close the browser
                browser.close()
                return True
                
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return False


class RequestsWebSearchTool(Tool):
    """Tool for searching the web using requests and BeautifulSoup - no browser automation needed."""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for information on a given query."
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Execute a web search using requests and BeautifulSoup."""
        logger.info(f"Starting requests-based web search for query: {query}")
        screenshots_dir = "search_screenshots"
        
        # Create screenshots directory if it doesn't exist
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
            
        try:
            # Check if requests and BeautifulSoup are available
            if not REQUESTS_AVAILABLE:
                logger.error("Requests or BeautifulSoup not installed")
                return {
                    "status": "error",
                    "message": "Requests or BeautifulSoup not installed. Install with 'pip install requests beautifulsoup4'"
                }
            
            all_results = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Try search with Google
            google_results = self._search_google(query, screenshots_dir, timestamp)
            all_results.extend(google_results)
            
            # Try search with Bing if we don't have enough results
            if len(all_results) < 5:
                bing_results = self._search_bing(query, screenshots_dir, timestamp)
                all_results.extend(bing_results)
            
            # Try a news search if we're looking for recent information
            ddg_results = self._search_duckduckgo(query, screenshots_dir, timestamp)
            all_results.extend(ddg_results)
                
            # Filter out any duplicates
            unique_results = []
            seen_links = set()
            
            for result in all_results:
                if result["link"] not in seen_links:
                    seen_links.add(result["link"])
                    unique_results.append(result)
            
            logger.info(f"Web search completed with {len(unique_results)} unique results")
            
            # Create screenshots with Playwright if available
            if PLAYWRIGHT_AVAILABLE:
                search_urls = {
                    "google": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
                    "bing": f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
                    "ddg": f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
                }
                
                for engine, url in search_urls.items():
                    screenshot_path = os.path.join(screenshots_dir, f"{engine}_search_{timestamp}.png")
                    PlaywrightScreenshotTool.take_screenshot(url, screenshot_path)
            
            return {
                "status": "success",
                "results": unique_results,
                "query": query,
                "screenshots_dir": screenshots_dir
            }
            
        except Exception as e:
            error_msg = f"Error during web search: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "query": query
            }
    
    def _get_random_user_agent(self):
        """Get a random user agent to avoid detection."""
        return random.choice(USER_AGENTS)
    
    def _search_google(self, query: str, screenshots_dir: str, timestamp: str) -> List[Dict[str, Any]]:
        """Search Google using requests and BeautifulSoup."""
        results = []
        
        try:
            # Format the search URL
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            logger.info(f"Searching Google for: {query}")
            
            # Make the request with a random user agent
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/"
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find search result elements (this may need adjustment based on Google's layout)
            search_results = soup.select(".g")
            
            if not search_results:
                search_results = soup.select("[data-hveid]")
            
            if not search_results:
                search_results = soup.select(".MjjYud")
            
            logger.info(f"Found {len(search_results)} Google search results")
            
            # Process each result
            for result in search_results[:10]:  # Limit to 10 results
                # Find title
                title_elem = result.select_one("h3")
                
                # Find link
                link_elem = result.select_one("a")
                
                # Find snippet
                snippet_elem = result.select_one(".VwiC3b") or result.select_one(".s3v9rd")
                
                if title_elem and link_elem and "href" in link_elem.attrs:
                    title = title_elem.get_text().strip()
                    link = link_elem["href"]
                    
                    # Google prepends results with /url?q=
                    if link.startswith("/url?q="):
                        link = link.split("/url?q=")[1].split("&")[0]
                        link = urllib.parse.unquote(link)
                    
                    # Make sure it's a valid URL
                    if link.startswith("http"):
                        snippet = snippet_elem.get_text().strip() if snippet_elem else "No description available"
                        
                        results.append({
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "Google"
                        })
                        logger.info(f"Extracted Google result: {title}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error during Google search: {str(e)}")
            return []
    
    def _search_bing(self, query: str, screenshots_dir: str, timestamp: str) -> List[Dict[str, Any]]:
        """Search Bing using requests and BeautifulSoup."""
        results = []
        
        try:
            # Format the search URL
            search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            logger.info(f"Searching Bing for: {query}")
            
            # Make the request with a random user agent
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find search result elements
            search_results = soup.select(".b_algo")
            logger.info(f"Found {len(search_results)} Bing search results")
            
            # Process each result
            for result in search_results[:5]:  # Limit to 5 results
                # Find title
                title_elem = result.select_one("h2")
                
                # Find link
                link_elem = result.select_one("a")
                
                # Find snippet
                snippet_elem = result.select_one(".b_caption p")
                
                if title_elem and link_elem and "href" in link_elem.attrs:
                    title = title_elem.get_text().strip()
                    link = link_elem["href"]
                    
                    # Make sure it's a valid URL
                    if link.startswith("http"):
                        snippet = snippet_elem.get_text().strip() if snippet_elem else "No description available"
                        
                        results.append({
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "Bing"
                        })
                        logger.info(f"Extracted Bing result: {title}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error during Bing search: {str(e)}")
            return []
    
    def _search_duckduckgo(self, query: str, screenshots_dir: str, timestamp: str) -> List[Dict[str, Any]]:
        """Search DuckDuckGo using requests and BeautifulSoup."""
        results = []
        
        try:
            # DuckDuckGo's search API
            search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            logger.info(f"Searching DuckDuckGo for: {query}")
            
            # Make the request with a random user agent
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find search result elements
            search_results = soup.select(".result")
            logger.info(f"Found {len(search_results)} DuckDuckGo search results")
            
            # Process each result
            for result in search_results[:5]:  # Limit to 5 results
                # Find title and link
                title_elem = result.select_one(".result__title")
                link_elem = result.select_one(".result__url")
                
                # Find snippet
                snippet_elem = result.select_one(".result__snippet")
                
                if title_elem:
                    title_a = title_elem.select_one("a")
                    if title_a:
                        title = title_a.get_text().strip()
                        
                        # For DuckDuckGo, we need to extract the real URL
                        link = ""
                        if link_elem:
                            link = "https://" + link_elem.get_text().strip()
                        elif "href" in title_a.attrs:
                            href = title_a["href"]
                            if href.startswith("/"):
                                # Extract destination URL from DuckDuckGo redirect
                                redirect_match = re.search(r'uddg=([^&]+)', href)
                                if redirect_match:
                                    link = urllib.parse.unquote(redirect_match.group(1))
                        
                        if link and link.startswith("http"):
                            snippet = snippet_elem.get_text().strip() if snippet_elem else "No description available"
                            
                            results.append({
                                "title": title,
                                "link": link,
                                "snippet": snippet,
                                "source": "DuckDuckGo"
                            })
                            logger.info(f"Extracted DuckDuckGo result: {title}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error during DuckDuckGo search: {str(e)}")
            return []
    
    def visit_and_summarize(self, url: str) -> Dict[str, Any]:
        """Visit a specific URL and extract content using requests and BeautifulSoup."""
        logger.info(f"Visiting and summarizing URL: {url}")
        screenshots_dir = "page_screenshots"
        
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            if not REQUESTS_AVAILABLE:
                return {"status": "error", "message": "Requests or BeautifulSoup not installed"}
            
            # Make the request with a random user agent
            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            # Take a screenshot using Playwright if available
            screenshot_path = os.path.join(screenshots_dir, f"page_{timestamp}.png")
            screenshot_taken = False
            
            if PLAYWRIGHT_AVAILABLE:
                screenshot_taken = PlaywrightScreenshotTool.take_screenshot(url, screenshot_path)
                logger.info(f"Screenshot saved to {screenshot_path}" if screenshot_taken else "Failed to take screenshot")
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract page title
            title = soup.title.get_text().strip() if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            # Try to get main content using various content selectors
            main_content = ""
            content_selectors = [
                "main", "article", "#content", ".content", 
                "[role='main']", ".main-content", ".post-content",
                "#main", ".article-content", ".entry-content", 
                "[itemprop='articleBody']", ".body", "#article-body"
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content_text = content_elem.get_text()
                    if len(content_text) > 100:  # Only use if substantial content
                        main_content = content_text
                        logger.info(f"Found content with selector: {selector}")
                        break
            
            # If no main content found, try to extract paragraphs
            if not main_content:
                logger.info("No main content found with selectors, extracting paragraphs")
                paragraphs = soup.select("p")
                paragraph_texts = []
                
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > 40:  # Only include substantial paragraphs
                        paragraph_texts.append(text)
                
                main_content = "\n\n".join(paragraph_texts)
            
            # If still no content, get body text
            if not main_content:
                logger.info("Falling back to body text")
                body = soup.body
                if body:
                    main_content = body.get_text()
                else:
                    main_content = "Failed to extract content from page."
            
            # Try to extract metadata
            metadata = {}
            
            # Publication date
            date_selectors = [
                "time", "[itemprop='datePublished']", ".date", ".published", 
                "[datetime]", ".post-date", ".article-date"
            ]
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text().strip()
                    if date_text:
                        metadata["publication_date"] = date_text
                        break
            
            # Author
            author_selectors = [
                "[itemprop='author']", ".author", ".byline", 
                "[rel='author']", ".article-author"
            ]
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author_text = author_elem.get_text().strip()
                    if author_text:
                        metadata["author"] = author_text
                        break
            
            # Clean and truncate content
            cleaned_content = self._clean_content(main_content)
            truncated_content = cleaned_content[:5000]  # Increased limit to 5000 chars
            
            result = {
                "status": "success",
                "title": title,
                "content": truncated_content,
                "metadata": metadata,
                "url": url
            }
            
            if screenshot_taken:
                result["screenshot"] = screenshot_path
                
            return result
                
        except Exception as e:
            error_msg = f"Error visiting URL: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "url": url
            }
    
    def _clean_content(self, content: str) -> str:
        """Clean extracted content by removing excess whitespace and common boilerplate."""
        if not content:
            return ""
        
        # Replace multiple newlines with just two
        content = "\n".join(line for line in content.splitlines() if line.strip())
        
        # Replace multiple spaces with single space
        content = " ".join(content.split())
        
        # Common phrases to remove (like cookie notices, navigation instructions)
        boilerplate = [
            "accept cookies", "cookie policy", "use cookies", 
            "privacy policy", "terms of service", "all rights reserved",
            "navigation menu", "skip to content", "search", "sign in",
            "subscribe to our newsletter", "subscribe now", "sign up",
            "we've updated our privacy policy"
        ]
        
        # Create a list of lines, filtering out boilerplate
        lines = content.splitlines()
        filtered_lines = []
        
        for line in lines:
            if line and not any(phrase in line.lower() for phrase in boilerplate):
                filtered_lines.append(line)
        
        return "\n".join(filtered_lines)

# Existing WebSearchTool class remains for compatibility, but we won't use it

class ToolRegistry:
    """Registry for tools that can be used by the agent."""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the registry."""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Tool:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool exists in the registry."""
        return name in self.tools
    
    def list_tools(self) -> Dict[str, str]:
        """List all available tools with their descriptions."""
        return {name: tool.description for name, tool in self.tools.items()}