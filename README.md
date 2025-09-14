# ChatGPT Riff Server

An intelligent MCP server that enables users to privately share ChatGPT conversations with Poke, which then processes and intelligently shares synthesized insights to group chats. Built with [FastMCP](https://github.com/jlowin/fastmcp) and designed to transform private thoughts into engaging conversation starters.

## 🎯 What It Does

This system creates a "riff" experience where:
1. Users privately share ChatGPT conversations with Poke
2. The server scrapes and digests conversations using Firecrawl + OpenRouter
3. Poke intelligently decides when to share synthesized insights with the group
4. Private thoughts become conversation starters while maintaining user privacy

## 🏗️ Architecture

- **MCP Server** (`src/server.py`): Handles link submission and data queries
- **Webhook Service** (`src/webhook.py`): Async processing and digest generation
- **Scraper** (`src/scraper.py`): Firecrawl integration for ChatGPT conversation extraction
- **Database** (`src/database.py`): PostgreSQL storage for conversations and metadata
- **Prompts** (`src/prompts.py`): LLM prompts for synthesis and formatting

## 📦 Local Development

### Setup

```bash
git clone https://github.com/sxysun/mcp-server-template.git
cd mcp-server-template
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```bash
# Required
DATABASE_URL=postgres://user:pass@host:5432/dbname
FIRECRAWL_API_KEY=fc-your-api-key
OPENROUTER_API_KEY=sk-or-v1-your-key
POKE_API_KEY=pk_your-poke-key
POKE_API_URL=https://poke.com/api/v1/inbound-sms/webhook

# Optional
DIGEST_MODEL=nousresearch/hermes-4-405b  # Default: openai/gpt-3.5-turbo
WEBHOOK_PORT=8001                        # Default: 8001
ENVIRONMENT=development                  # Default: development
```

### Run Locally

```bash
# Terminal 1 - MCP Server
python src/server.py

# Terminal 2 - Webhook Service
python src/webhook.py

# Terminal 3 - Ngrok (for Poke integration)
ngrok http 8000
```

### Database Setup

The PostgreSQL `riff` table is created automatically on first run. To manually create:

```bash
curl -X POST http://localhost:8001/webhook/setup-database
```

## 🧪 Testing

### Test Individual Components

```bash
# Test scraping
python test_scraper.py

# Check webhook health
curl http://localhost:8001/health

# Queue a link for processing
curl -X POST http://localhost:8001/webhook/new-link \
  -H "Content-Type: application/json" \
  -d '{"url": "https://chatgpt.com/share/..."}'
```

### Test Full Pipeline

```bash
# Process all pending + send digest immediately
curl -X POST http://localhost:8001/webhook/test-full-flow
```

This will:
1. Mark all conversations as unshared (for testing)
2. Scrape all pending ChatGPT links
3. Generate group digest using OpenRouter
4. Send to Poke for group sharing

## 🤖 Poke Integration

Connect to Poke at [poke.com/settings/connections](https://poke.com/settings/connections) using your ngrok URL:
```
https://your-ngrok-url.ngrok.io
```

### How Poke Should Behave

**Automatic Link Processing:**
- When Poke sees ANY ChatGPT share link → automatically calls `submit_chatgpt_link`
- When users say "riff it" with content → processes via MCP functions

**Intelligent Group Sharing:**
- Webhook sends digest to Poke
- Poke decides whether content is worth sharing based on group context
- Only interesting, discussion-worthy content reaches the group
- Quality over frequency - no spam

### Available MCP Functions

- `submit_chatgpt_link(url, user_name)` - Submit ChatGPT link for processing
- `get_daily_conversations(date?)` - Get processed conversations for synthesis
- `get_user_submissions(user_name)` - View user's submission history
- `get_conversation_details(url)` - Get full conversation details
- `mark_as_shared(urls)` - Mark conversations as shared to group
- `get_known_users()` - List all participating users
- `get_server_info()` - Comprehensive system documentation

## 🎨 Customization

### Change Digest Model

Update `.env`:
```bash
DIGEST_MODEL=anthropic/claude-3-haiku
```

### Modify Prompts

Edit `src/prompts.py` to change:
- Individual conversation digest prompts
- Group synthesis personality and style
- Decision criteria for sharing

### Adjust Sharing Behavior

The system uses intelligent sharing based on content quality. Modify the criteria in `GROUP_DIGEST_TEMPLATE` within `src/prompts.py`.

## 🔒 Privacy & Security

- Individual ChatGPT submissions are private until synthesized for group
- Users maintain control over their shared content
- Group only sees synthesized insights, not raw conversations
- All API keys should be kept secure in environment variables

## 📊 Features

- ✅ **Automatic ChatGPT link detection**
- ✅ **Firecrawl-powered conversation scraping**
- ✅ **OpenRouter digest generation**
- ✅ **Async webhook processing**
- ✅ **Intelligent group sharing decisions**
- ✅ **PostgreSQL conversation storage**
- ✅ **User privacy preservation**
- ✅ **Configurable LLM models**
- ✅ **Comprehensive testing endpoints**

## 🤝 Contributing

This server is designed to be extended. Add more tools by decorating functions with `@mcp.tool`:

```python
@mcp.tool
def your_custom_function(param: str) -> str:
    """Description of what your function does."""
    return f"Processed: {param}"
```
