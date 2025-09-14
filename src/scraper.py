
import os
import requests
from dotenv import load_dotenv
from firecrawl import Firecrawl
from prompts import (
    DIGEST_SYSTEM_PROMPT,
    ERROR_NO_CONTENT,
    ERROR_SCRAPE_FAILED,
    ERROR_UNEXPECTED_FORMAT
)

load_dotenv()

firecrawl = Firecrawl(api_key=os.environ.get("FIRECRAWL_API_KEY"))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
DIGEST_MODEL = os.environ.get("DIGEST_MODEL", "openai/gpt-3.5-turbo")

def scrape_and_digest_chatgpt_conversation(url: str) -> tuple[str, str]:
    """
    Scrapes a ChatGPT share URL and generates a digest of the conversation

    Args:
        url: ChatGPT share URL like https://chatgpt.com/share/68c3b038-316c-8008-b45e-14f96bc66c07

    Returns:
        Tuple of (full_content, digest) where:
        - full_content: The complete scraped conversation
        - digest: AI-generated summary or truncated version

    Example:
        >>> content, digest = scrape_and_digest_chatgpt_conversation("https://chatgpt.com/share/...")
        >>> print(digest)
        "This conversation discusses implementing web scrapers using Python..."
    """
    try:
        # Use Firecrawl to scrape the ChatGPT share page
        doc = firecrawl.scrape(url, formats=["markdown"])
        # doc = firecrawl.scrape(url, formats=["markdown", "summary"])
        # Extract the markdown content from the Document object
        full_content = ""
        digest = ""
        if doc and hasattr(doc, 'markdown'):
            full_content = doc.markdown
            # Use the summary from Firecrawl or generate our own
            if hasattr(doc, 'summary') and doc.summary:
                digest = doc.summary
            else:
                # Fallback to generating digest if no summary available
                digest = _generate_digest(full_content)
        else:
            return (ERROR_UNEXPECTED_FORMAT.format(url=url), ERROR_NO_CONTENT)

        return (full_content, digest)

    except Exception as e:
        error_msg = ERROR_SCRAPE_FAILED.format(url=url, error=str(e))
        return (error_msg, error_msg)

def _generate_digest(content: str) -> str:
    """Generate a digest of the conversation using OpenRouter API"""
    if not OPENROUTER_API_KEY:
        # Fallback to simple truncation if no API key
        return content[:500] + "..." if len(content) > 500 else content

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": DIGEST_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": DIGEST_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Conversation input:\n\n{content[:3000]}"  # Limit context
                }
            ]
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            print(f"OpenRouter API error: {response.status_code}")
            return content[:500] + "..."

    except Exception as e:
        print(f"Error generating digest: {e}")
        return content[:500] + "..."