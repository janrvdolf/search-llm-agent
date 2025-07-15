#!/usr/bin/env python3
"""
Simplified LangChain LLM Agent for Autonomous Web Research (Anthropic Claude)

This is a working implementation that uses LangChain tools with the SearXNG client
and Anthropic's Claude API for the language model.
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    # Core LangChain imports
    from langchain.tools import tool
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain.prompts import PromptTemplate
    from langchain_anthropic import ChatAnthropic

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LangChain not fully available: {e}")
    LANGCHAIN_AVAILABLE = False

# Import our search tools
from searxng_client import SearXNGClient, print_image_urls, download_images


class SimpleLangChainAgent:
    """Simplified LangChain agent using function decorators"""

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        searxng_url: Optional[str] = None,
        model_name: str = "claude-3-5-sonnet-20241022",
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not properly installed")

        # Set up API key
        if anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
        elif not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("Anthropic API key required")

        # Set up SearXNG URL from environment variable or parameter
        if searxng_url is None:
            searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8080")

        # Initialize SearXNG client
        self.searxng_client = SearXNGClient(searxng_url)

        # Initialize LLM with fallback models
        self.llm = self._initialize_llm(model_name)

        # Initialize image URLs storage
        self._last_image_urls = []

        # Create tools
        self.tools = self._create_tools()

        # Initialize conversation history storage
        self.conversation_history = []

        # Create agent prompt
        self.prompt = PromptTemplate.from_template(
            """
You are an autonomous research agent with access to web search and image download tools.

You have access to these tools:
{tools}

IMPORTANT WORKFLOW FOR IMAGE DOWNLOADS:
1. Use search tool with "images" type to find image URLs
2. When search finds image URLs, immediately use download tool to download them
3. The search tool will tell you exactly what to do next

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
{agent_scratchpad}
"""
        )

        # Create agent
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
        )

        print("🤖 Simplified LangChain Agent initialized")
        print(f"🔗 Connected to SearXNG: {searxng_url}")
        print(f"🛠️ Available tools: {', '.join([tool.name for tool in self.tools])}")
        print("🧠 Memory enabled for conversational context")

        # Store the URL for reference
        self.searxng_url = searxng_url

    def _initialize_llm(self, preferred_model: str):
        """Initialize LLM with fallback models"""
        fallback_models = [
            preferred_model,
            "claude-3-5-sonnet-20241022",  # Latest Claude 3.5 Sonnet
            "claude-3-5-sonnet-20240620",  # Previous Claude 3.5 Sonnet
            "claude-3-sonnet-20240229",  # Claude 3 Sonnet
            "claude-3-haiku-20240307",  # Claude 3 Haiku (faster, cheaper)
        ]

        # Remove duplicates while preserving order
        unique_models = []
        for model in fallback_models:
            if model not in unique_models:
                unique_models.append(model)

        for model_name in unique_models:
            try:
                print(f"🧪 Trying model: {model_name}")
                llm = ChatAnthropic(
                    model_name=model_name, temperature=0.1, timeout=30, stop=[]
                )

                # Test the model with a simple query
                test_response = llm.invoke("Hello")
                print(f"✅ Successfully initialized: {model_name}")
                return llm

            except Exception as e:
                print(f"❌ Failed to initialize {model_name}: {str(e)}")
                continue

        raise RuntimeError(
            "Could not initialize any Anthropic model. Please check your API key and model availability."
        )

    def _create_tools(self):
        """Create LangChain tools using decorators"""

        @tool
        def search(input_string: str) -> str:
            """
            Unified search tool using SearXNG.

            Use this tool to search for information on the web, Wikipedia, or images.

            Examples:
            - General search: search("zebra facts", "general", 5)
            - Wikipedia search: search("zebra", "wikipedia", 3)
            - Image search: search("zebra", "images", 5) - This will find image URLs and prepare them for download

            IMPORTANT: For image searches, after this tool finds image URLs, you MUST use the download tool
            to actually download the images. The workflow is: 1) search for images, 2) download the found images.

            Input format: "query", "search_type", max_results
            - query: The search query/topic (required)
            - search_type: Type of search - "general", "wikipedia", or "images" (default: "general")
            - max_results: Maximum number of results to return (default: 5)

            Returns URLs and relevant information based on search type. For images, returns URLs ready for download.
            """
            try:
                # Parse the input string
                parts = [part.strip(" \"'") for part in input_string.split(",")]

                query = parts[0] if len(parts) > 0 else ""
                search_type = parts[1] if len(parts) > 1 else "general"
                max_results = (
                    int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 5
                )

                if not query:
                    return "Error: Query cannot be empty"

                if search_type == "images":
                    # Search for images
                    search_results = self.searxng_client.search(
                        query=query,
                        categories=["images"],
                        engines=["google", "bing", "duckduckgo"],
                    )

                    if "error" in search_results:
                        return f"Image search failed: {search_results['error']}"

                    # Process image URLs without capturing stdout
                    from searxng_client import print_image_urls

                    image_urls = print_image_urls(
                        search_results,
                        max_results=max_results,
                        max_urls_to_return=max_results,
                    )

                    # Store URLs for later use
                    self._last_image_urls = image_urls

                    if len(image_urls) > 0:
                        result_text = f"✅ SUCCESS: Found {len(image_urls)} image URLs for '{query}'!\n\n"
                        result_text += f"🖼️ Image URLs ready for download:\n"
                        for i, url in enumerate(image_urls, 1):
                            result_text += f"{i}. {url}\n"
                        result_text += f"\n🔽 NEXT STEP: Use the download tool with topic name (e.g., download('zebra')) to download these {len(image_urls)} images."
                        return result_text
                    else:
                        return f"❌ No direct image URLs found for '{query}'. Try different search terms or engines."

                elif search_type == "wikipedia":
                    # Search Wikipedia articles
                    search_results = self.searxng_client.search(
                        query=f"{query} site:wikipedia.org",
                        categories=["general"],
                        engines=["google", "duckduckgo"],
                    )

                    if "error" in search_results:
                        return f"Wikipedia search failed: {search_results['error']}"

                    articles = []
                    for result in search_results.get("results", [])[:max_results]:
                        if "wikipedia.org" in result.get("url", ""):
                            articles.append(
                                {
                                    "title": result.get("title", "Unknown"),
                                    "url": result.get("url", ""),
                                    "summary": result.get("content", "")[:200] + "...",
                                }
                            )

                    if not articles:
                        return f"No Wikipedia articles found for: {query}"

                    result_text = (
                        f"Found {len(articles)} Wikipedia articles about '{query}':\n\n"
                    )
                    for i, article in enumerate(articles, 1):
                        result_text += f"{i}. {article['title']}\n"
                        result_text += f"   URL: {article['url']}\n"
                        result_text += f"   Summary: {article['summary']}\n\n"

                    return result_text

                else:  # general search
                    # General web search
                    search_results = self.searxng_client.search(
                        query=query,
                        categories=["general"],
                        engines=["google", "duckduckgo", "bing"],
                    )

                    if "error" in search_results:
                        return f"Search failed: {search_results['error']}"

                    results = search_results.get("results", [])[:max_results]
                    if not results:
                        return f"No results found for: {query}"

                    result_text = f"Web search results for '{query}':\n\n"
                    for i, result in enumerate(results, 1):
                        result_text += f"{i}. {result.get('title', 'No Title')}\n"
                        result_text += f"   URL: {result.get('url', 'No URL')}\n"
                        content = result.get("content", "No description")[:150]
                        result_text += f"   Description: {content}...\n\n"

                    return result_text

            except Exception as e:
                return f"Error performing search: {str(e)}"

        @tool
        def download(url_or_topic: str) -> str:
            """
            Download content from URLs or download last searched images.

            Usage:
            - To download from URL: download("https://example.com")
            - To download last searched images: download("images") or download("topic_name")

            For URLs: Downloads content based on mime type (images saved as files, websites as JSON)
            For images: Downloads last searched images to downloads directory
            All downloads go to 'downloads' directory with accompanying JSON metadata files.
            """
            try:
                import requests
                from urllib.parse import urlparse
                import hashlib

                # Create downloads directory
                downloads_dir = "downloads"
                os.makedirs(downloads_dir, exist_ok=True)

                # Check if input is a URL or topic for image download
                if url_or_topic.startswith(("http://", "https://")) or (
                    not url_or_topic.startswith("http")
                    and "." in url_or_topic
                    and not " " in url_or_topic
                ):
                    # Handle URL download
                    url = url_or_topic.strip()  # Remove whitespace
                    if not url.startswith(("http://", "https://")):
                        url = "https://" + url

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }

                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()

                    # Get mime type
                    mime_type = response.headers.get("content-type", "text/plain")
                    if ";" in mime_type:
                        mime_type = mime_type.split(";")[0].strip()

                    # Generate filename based on URL
                    parsed_url = urlparse(url)
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    if mime_type.startswith("image/"):
                        # Handle image download
                        extension = mime_type.split("/")[1]
                        if extension == "jpeg":
                            extension = "jpg"
                        filename = f"image_{url_hash}_{timestamp}.{extension}"
                        filepath = os.path.join(downloads_dir, filename)

                        # Save image file
                        with open(filepath, "wb") as f:
                            f.write(response.content)

                        # Create metadata JSON
                        metadata = {
                            "filename": filename,
                            "url": url.strip(),
                            "mime_type": mime_type.strip(),
                            "file_size": len(response.content),
                            "download_timestamp": timestamp,
                            "type": "image",
                        }

                        json_filename = f"image_{url_hash}_{timestamp}.json"
                        json_filepath = os.path.join(downloads_dir, json_filename)

                        with open(json_filepath, "w") as f:
                            json.dump(metadata, f, indent=2)

                        return f"Image downloaded successfully!\nFile: {filepath}\nMetadata: {json_filepath}\nSize: {len(response.content)} bytes\nMime type: {mime_type}"

                    else:
                        # Handle website/text content download
                        filename = f"website_{url_hash}_{timestamp}.json"
                        filepath = os.path.join(downloads_dir, filename)

                        # Save website content as JSON
                        content_data = {
                            "url": url.strip(),
                            "content": response.text,
                            "mime_type": mime_type.strip(),
                            "status_code": response.status_code,
                            "content_length": len(response.text),
                            "download_timestamp": timestamp,
                            "type": "website",
                        }

                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(content_data, f, indent=2, ensure_ascii=False)

                        # Create metadata JSON
                        metadata = {
                            "filename": filename,
                            "url": url.strip(),
                            "mime_type": mime_type.strip(),
                            "file_size": len(response.text),
                            "download_timestamp": timestamp,
                            "type": "website",
                        }

                        json_filename = f"website_{url_hash}_{timestamp}_meta.json"
                        json_filepath = os.path.join(downloads_dir, json_filename)

                        with open(json_filepath, "w") as f:
                            json.dump(metadata, f, indent=2)

                        return f"Website content downloaded successfully!\nFile: {filepath}\nMetadata: {json_filepath}\nSize: {len(response.text)} bytes\nMime type: {mime_type}"

                else:
                    # Handle image download from last search
                    if (
                        not hasattr(self, "_last_image_urls")
                        or not self._last_image_urls
                    ):
                        return "No image URLs available. Please search for images first using the search tool."

                    downloaded_files = []
                    failed_downloads = []

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }

                    for i, img_url in enumerate(self._last_image_urls):
                        try:
                            # Clean the image URL
                            clean_img_url = img_url.strip()

                            response = requests.get(
                                clean_img_url, headers=headers, timeout=30
                            )
                            response.raise_for_status()

                            # Get mime type
                            mime_type = response.headers.get(
                                "content-type", "image/jpeg"
                            )
                            if ";" in mime_type:
                                mime_type = mime_type.split(";")[0].strip()

                            # Generate filename
                            url_hash = hashlib.md5(clean_img_url.encode()).hexdigest()[
                                :8
                            ]
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                            if mime_type.startswith("image/"):
                                extension = mime_type.split("/")[1]
                                if extension == "jpeg":
                                    extension = "jpg"
                            else:
                                extension = "jpg"  # fallback

                            filename = f"{url_or_topic}_{i+1:02d}_{url_hash}_{timestamp}.{extension}"
                            filepath = os.path.join(downloads_dir, filename)

                            # Save image
                            with open(filepath, "wb") as f:
                                f.write(response.content)

                            # Create metadata JSON
                            metadata = {
                                "filename": filename,
                                "url": clean_img_url,
                                "mime_type": mime_type.strip(),
                                "file_size": len(response.content),
                                "download_timestamp": timestamp,
                                "type": "image",
                                "search_topic": url_or_topic.strip(),
                            }

                            json_filename = (
                                f"{url_or_topic}_{i+1:02d}_{url_hash}_{timestamp}.json"
                            )
                            json_filepath = os.path.join(downloads_dir, json_filename)

                            with open(json_filepath, "w") as f:
                                json.dump(metadata, f, indent=2)

                            downloaded_files.append(filepath)

                        except Exception as e:
                            failed_downloads.append(f"{clean_img_url}: {str(e)}")

                    result = f"Downloaded {len(downloaded_files)} out of {len(self._last_image_urls)} images to downloads directory.\n\n"
                    if downloaded_files:
                        result += "Successfully downloaded:\n"
                        for file in downloaded_files:
                            result += f"  - {file}\n"

                    if failed_downloads:
                        result += f"\nFailed downloads ({len(failed_downloads)}):\n"
                        for failure in failed_downloads:
                            result += f"  - {failure}\n"

                    result += f"\nFiles saved in: {os.path.abspath(downloads_dir)}"
                    return result

            except requests.exceptions.RequestException as e:
                return f"Download failed: {str(e)}"
            except Exception as e:
                return f"Error during download: {str(e)}"

        return [
            search,
            download,
        ]

    def research_mission(self, topic: str, num_images: int = 5) -> str:
        """Conduct an autonomous research mission"""
        mission_prompt = f"""
Conduct a comprehensive research mission on the topic: "{topic}"

Your objectives:
1. Search Wikipedia for articles about {topic} to understand the topic thoroughly
2. Search for {num_images} high-quality images related to {topic}
3. Download the found images to a local directory
4. Provide a comprehensive summary of your findings

Execute this mission step by step and provide a detailed report of what you learned and accomplished.
"""

        print(f"\n🚀 Starting research mission: {topic}")
        print("=" * 60)

        try:
            result = self.agent_executor.invoke({"input": mission_prompt})
            return result["output"]
        except Exception as e:
            return f"Mission failed: {str(e)}"

    def chat(self, message: str) -> str:
        """Chat with the agent - now with conversation history!"""
        try:
            result = self.agent_executor.invoke({"input": message})

            # Store the conversation in history
            self.conversation_history.append(
                {"input": message, "output": result["output"]}
            )

            return result["output"]
        except Exception as e:
            return f"Error: {str(e)}"

    def get_conversation_history(self) -> str:
        """Get the current conversation history"""
        if not self.conversation_history:
            return "No conversation history yet."

        history_str = "Conversation History:\n"
        for i, entry in enumerate(self.conversation_history, 1):
            history_str += f"{i}. You: {entry['input']}\n"
            history_str += f"   Agent: {entry['output']}\n\n"

        return history_str

    def clear_memory(self):
        """Clear the conversation memory"""
        self.conversation_history = []
        print("🧹 Conversation memory cleared")


def main():
    """Demo the simplified LangChain agent"""
    print("🤖 Simplified LangChain Agent Demo")
    print("=" * 50)

    try:
        # Initialize agent
        agent = SimpleLangChainAgent()

        # Interactive mode
        print("\n💬 Chat with the agent (type 'quit' to exit):")
        print("💡 You can ask me to:")

        # Dynamically list available tools
        for tool in agent.tools:
            tool_name = tool.name
            if tool_name == "search":
                print("   - Search Wikipedia: 'Search Wikipedia for zebras'")
                print("   - Search images: 'Search for images of zebras'")
                print("   - General search: 'Search the web for zebra facts'")
            elif tool_name == "download":
                print("   - Download from URL: 'Download https://example.com'")
                print("   - Download images: 'Download images'")
                print("   - Download with topic: 'Download zebra_photos'")

        print("   - Research mission: 'Conduct a research mission on zebras'")

        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit"]:
                break

            response = agent.chat(user_input)
            print(f"\nAgent: {response}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
