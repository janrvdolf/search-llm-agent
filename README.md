# 🤖 LangChain Autonomous Research Agent

An intelligent web research agent powered by LangChain, Anthropic Claude, and SearXNG that can autonomously search the web, download content, and conduct comprehensive research missions.

## ✨ Features

- **Autonomous Research**: Conducts multi-step research missions with minimal human intervention
- **Multi-modal Search**: Supports web search, Wikipedia queries, and image discovery
- **Intelligent Downloads**: Automatically downloads and organizes content with metadata
- **Conversation Memory**: Maintains context across multiple interactions
- **Privacy-Focused**: Uses SearXNG for anonymous web searching
- **Flexible LLM Support**: Multiple Claude model fallback strategy

## 📋 Prerequisites

- Python 3.8 or higher
- [SearXNG](https://github.com/searxng/searxng) instance running (default: `http://localhost:8080`)
- Anthropic API key for Claude models

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd rapidsos
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   export SEARXNG_URL="http://localhost:8080"  # Optional: defaults to localhost:8080
   ```

   Or create a `.env` file:
   ```env
   ANTHROPIC_API_KEY=your-api-key-here
   SEARXNG_URL=http://localhost:8080
   ```

## ⚙️ Configuration

### SearXNG Setup

This agent requires a running SearXNG instance. To set up SearXNG using Docker:

```bash
docker run -d -p 8080:8080 \
  -v searxng:/etc/searxng \
  -e BASE_URL=http://localhost:8080 \
  searxng/searxng:latest
```

### Model Configuration

The agent uses Claude 3.5 Sonnet by default with automatic fallback to other models:
- `claude-3-5-sonnet-20241022` (latest)
- `claude-3-5-sonnet-20240620` (previous version)
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307` (faster, cheaper)

## 🛠️ Available Tools

### 1. Search Tool
Unified search interface for web content, Wikipedia articles, and images.

**Usage patterns**:
```python
# General web search
"quantum computing, general, 10"

# Wikipedia search
"artificial intelligence, wikipedia, 5"

# Image search (prepares URLs for download)
"zebras in nature, images, 20"
```

**Parameters**:
- `query`: Search terms (required)
- `search_type`: "general", "wikipedia", or "images" (default: "general")
- `max_results`: Maximum results to return (default: 5)

### 2. Download Tool
Downloads content from URLs or batch downloads images from previous searches.

**Usage patterns**:
```python
# Download from specific URL
"https://example.com/image.jpg"

# Download all images from last search
"zebras"  # Uses topic name for file organization

# Download with automatic HTTPS
"example.com/document.pdf"
```

**Features**:
- Automatic content type detection
- Metadata JSON files for each download
- Organized file naming with timestamps
- Batch image download support
- Website content saved as JSON

## 💻 Usage

### Basic Usage

```python
from agent import SimpleLangChainAgent

# Initialize the agent
agent = SimpleLangChainAgent()

# Chat with the agent
response = agent.chat("Search for information about zebras and download some images")
print(response)

# Run a research mission
mission_result = agent.research_mission("zebras", num_images=10)
print(mission_result)

# Check conversation history
history = agent.get_conversation_history()
print(history)
```

### Interactive Mode

Run the agent in interactive chat mode:

```bash
python agent.py
```

### Example Commands

1. **Research Mission**:
   ```
   Conduct a research mission on quantum computing
   ```

2. **Wikipedia Research**:
   ```
   Search Wikipedia for articles about the Apollo program
   ```

3. **Image Collection**:
   ```
   Find and download 20 images of aurora borealis
   ```

4. **Web Content Download**:
   ```
   Download the content from https://example.com/article
   ```

## 📁 File Organization

Downloaded content is organized in the `downloads/` directory:

```
downloads/
├── zebra_01_a1b2c3d4_20241210_143022.jpg
├── zebra_01_a1b2c3d4_20241210_143022.json  # Metadata
├── website_e5f6g7h8_20241210_143025.json   # Website content
└── website_e5f6g7h8_20241210_143025_meta.json
```

Each download includes:
- **Content file**: The actual downloaded content
- **Metadata JSON**: URL, timestamp, file size, MIME type, etc.

## 🧩 Advanced Features

### Conversation Memory
The agent maintains conversation history across interactions:

```python
# Clear memory when needed
agent.clear_memory()

# Access conversation history
history = agent.get_conversation_history()
```

### Custom Model Selection
```python
agent = SimpleLangChainAgent(
    model_name="claude-3-haiku-20240307",  # Use faster model
    anthropic_api_key="your-key",
    searxng_url="http://your-searxng-instance.com"
)
```

### Error Handling
The agent includes robust error handling:
- Automatic model fallback
- Graceful search failures
- Download retry logic
- Parse error recovery

## 🔒 Privacy & Security

- **No tracking**: Uses SearXNG for anonymous searches
- **Local storage**: All downloads stored locally
- **No external dependencies**: Runs entirely on your infrastructure
- **API key security**: Keys stored in environment variables

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

[Specify your license here]

## 🙏 Acknowledgments

- [LangChain](https://www.langchain.com/) for the agent framework
- [Anthropic](https://www.anthropic.com/) for Claude AI models
- [SearXNG](https://github.com/searxng/searxng) for privacy-respecting search 