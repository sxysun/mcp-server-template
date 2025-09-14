#!/usr/bin/env python3
"""
Webhook service for async processing of ChatGPT links and periodic Poke notifications
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict
import json
from dotenv import load_dotenv

# Import our modules
from database import (
    get_conversation_by_url,
    update_conversation_content,
    get_conversations_by_date,
    mark_conversations_as_shared,
    mark_all_conversations_as_unshared,
    get_connection,
    create_table
)
from scraper import scrape_and_digest_chatgpt_conversation
from prompts import (
    GROUP_DIGEST_TEMPLATE,
    USER_SECTION_TEMPLATE,
    DIGEST_ITEM_TEMPLATE,
    NO_CONVERSATIONS_MESSAGE,
    GROUP_SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_INPUT_TEMPLATE
)

load_dotenv()

# Configuration
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", 8001))
POKE_API_KEY = os.environ.get("POKE_API_KEY")
POKE_API_URL = os.environ.get("POKE_API_URL", "https://api.poke.so/v1/messages")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
DIGEST_MODEL = os.environ.get("DIGEST_MODEL", "openai/gpt-3.5-turbo")
DIGEST_INTERVAL_MINUTES = 3  # Send digest every 10 minutes

# Store pending scrape tasks
scrape_queue = asyncio.Queue()

async def scrape_worker():
    """Worker that processes scraping tasks from the queue"""
    while True:
        try:
            url = await scrape_queue.get()
            print(f"Scraping {url}...")

            # Scrape and digest the conversation
            content, digest = scrape_and_digest_chatgpt_conversation(url)

            # Update database
            update_conversation_content(url, content, digest)

            print(f"Successfully scraped and stored {url}")

        except Exception as e:
            print(f"Error processing {url}: {e}")

        finally:
            scrape_queue.task_done()


async def send_to_poke(message: str, chat_id: str = None):
    """Send a message to Poke group chat"""
    if not POKE_API_KEY:
        print(f"Would send to Poke: {message[:100]}...")
        return

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {POKE_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "message": message,
                "chat_id": chat_id or "default_group"  # Adjust based on Poke API
            }

            async with session.post(POKE_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    print("Successfully sent message to Poke")
                else:
                    print(f"Poke API error: {response.status}")

    except Exception as e:
        print(f"Error sending to Poke: {e}")

async def periodic_digest_sender():
    """Periodically send digests to Poke group chat only if there are unshared conversations"""
    while True:
        try:
            # Wait for the interval
            await asyncio.sleep(DIGEST_INTERVAL_MINUTES * 60)

            print("Checking for unshared conversations...")

            # Get today's conversations
            all_conversations = get_conversations_by_date()

            if not all_conversations:
                print("No conversations today")
                continue

            # Check if there are any unshared conversations
            unshared_conversations = [conv for conv in all_conversations if not conv.get('shared_to_group_at')]

            # Debug: Print sharing status for each conversation
            print("Conversation sharing status:")
            for conv in all_conversations:
                shared_status = conv.get('shared_to_group_at')
                print(f"  URL: {conv['chatgpt_url'][:50]}... | Shared: {shared_status}")

            if not unshared_conversations:
                print(f"All {len(all_conversations)} conversations already shared - skipping digest")
                continue

            print(f"Found {len(unshared_conversations)} unshared conversations out of {len(all_conversations)} total")

            # Create synthesized message using ALL today's conversations (including previously shared ones)
            message = await create_group_digest(all_conversations)

            # Send to Poke
            await send_to_poke(message)

            # Mark the unshared conversations as shared
            unshared_urls = [conv['chatgpt_url'] for conv in unshared_conversations]
            if unshared_urls:
                print(f"About to mark URLs as shared: {unshared_urls}")
                marked_count = mark_conversations_as_shared(unshared_urls)
                print(f"Database says {marked_count} conversations were marked as shared")

                # Verify the marking worked by re-querying
                verification_conversations = get_conversations_by_date()
                still_unshared = [conv for conv in verification_conversations if not conv.get('shared_to_group_at')]
                print(f"Verification: {len(still_unshared)} conversations remain unshared after marking")

        except Exception as e:
            print(f"Error in periodic digest: {e}")

async def synthesize_with_openrouter(raw_summaries: str) -> str:
    """Use OpenRouter to synthesize raw summaries into engaging group message"""
    if not OPENROUTER_API_KEY:
        # Fallback if no API key
        return "Openrouter API key not found"

    print(f"🤖 Using model: {DIGEST_MODEL}")
    print(f"🔑 API Key exists: {bool(OPENROUTER_API_KEY)}")

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": DIGEST_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": GROUP_SYNTHESIS_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": SYNTHESIS_INPUT_TEMPLATE.format(raw_summaries=raw_summaries)
                    }
                ]
            }

            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    print(f"✅ Synthesis successful with {DIGEST_MODEL}")
                    print(f"📝 Generated content: {content[:100]}...")
                    return content
                else:
                    error_text = await response.text()
                    print(f"❌ OpenRouter API error: {response.status}")
                    print(f"❌ Error details: {error_text}")
                    return f"🎯 Daily ChatGPT Insights:\n\n{raw_summaries}\n\n✨ Share your own insights by submitting ChatGPT links!"

    except Exception as e:
        print(f"Error synthesizing digest: {e}")
        return f"Error synthesizing digest: {e}"

async def create_group_digest(conversations: List[Dict]) -> str:
    """Create a synthesized message from multiple conversations using LLM"""
    if not conversations:
        return NO_CONVERSATIONS_MESSAGE

    # Collect raw summaries by user
    raw_summaries = []
    by_user = {}
    for conv in conversations:
        user = conv.get('user_name', 'Anonymous')
        digest = conv.get('digest', '')
        if user not in by_user:
            by_user[user] = []
        if digest:
            by_user[user].append(digest)

    # Format raw summaries for LLM input
    for user, digests in by_user.items():
        for i, digest in enumerate(digests[:2], 1):  # Limit to 2 per user
            raw_summaries.append(f"From {user} (#{i}): {digest}")

    if not raw_summaries:
        return NO_CONVERSATIONS_MESSAGE

    raw_summaries_text = "\n\n".join(raw_summaries)

    # Use LLM to synthesize the raw summaries into an engaging message
    synthesized_content = await synthesize_with_openrouter(raw_summaries_text)

    return GROUP_DIGEST_TEMPLATE.format(synthesized_content=synthesized_content)

# Simple HTTP webhook server using aiohttp
from aiohttp import web

async def handle_new_link(request):
    """Handle webhook notification for new link submission"""
    try:
        data = await request.json()
        url = data.get('url')

        if url:
            await scrape_queue.put(url)
            return web.json_response({"status": "queued", "url": url})
        else:
            return web.json_response({"error": "No URL provided"}, status=400)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_trigger_digest(request):
    """Manually trigger a digest send"""
    try:
        conversations = get_conversations_by_date()
        message = await create_group_digest(conversations)
        await send_to_poke(message)

        return web.json_response({
            "status": "sent",
            "conversation_count": len(conversations)
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_health(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "queue_size": scrape_queue.qsize()
    })

async def handle_setup_database(request):
    """Setup database table manually"""
    try:
        create_table()

        # Test the connection and check if table exists
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_name = 'riff' AND table_schema = 'public'
                """)
                table_exists = cur.fetchone()

                cur.execute("SELECT COUNT(*) FROM riff")
                row_count = cur.fetchone()['count']

        return web.json_response({
            "status": "success",
            "table_exists": bool(table_exists),
            "table_name": table_exists['table_name'] if table_exists else None,
            "row_count": row_count,
            "message": "Database table created successfully"
        })

    except Exception as e:
        return web.json_response({
            "status": "error",
            "error": str(e),
            "message": "Failed to create database table"
        }, status=500)

async def handle_scrape_all_pending(request):
    """Scrape all pending links in the database"""
    try:
        # Get all pending links from database
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT chatgpt_url
                    FROM riff
                    WHERE status = 'pending'
                """)
                pending_links = cur.fetchall()

        if not pending_links:
            return web.json_response({
                "status": "no_pending",
                "message": "No pending links to scrape"
            })

        # Queue all pending links for scraping
        scraped_count = 0
        for link in pending_links:
            url = link['chatgpt_url']
            await scrape_queue.put(url)
            scraped_count += 1

        return web.json_response({
            "status": "queued",
            "count": scraped_count,
            "message": f"Queued {scraped_count} links for scraping"
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_test_full_flow(request):
    """Test endpoint: Mark all as unshared, scrape ALL unscraped entries, and send digest immediately"""
    try:
        # Step 0: Mark all conversations as unshared (for testing)
        unshared_count = mark_all_conversations_as_unshared()
        print(f"Marked {unshared_count} conversations as unshared for testing")

        # Step 1: Get ALL unscraped entries (pending status OR no conversation content)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT chatgpt_url, status, conversation_content
                    FROM riff
                    WHERE status = 'pending'
                       OR conversation_content IS NULL
                       OR conversation_content = ''
                       OR conversation_content LIKE '[Error]%'
                       OR conversation_content LIKE '[Placeholder]%'
                """)
                unscraped_links = cur.fetchall()

        print(f"Found {len(unscraped_links)} unscraped entries to process")

        scraped_count = 0
        failed_count = 0
        for link in unscraped_links:
            url = link['chatgpt_url']
            print(f"Scraping: {url}")

            # Scrape synchronously for testing
            content, digest = scrape_and_digest_chatgpt_conversation(url)

            if "[Error]" not in content:
                update_conversation_content(url, content, digest)
                scraped_count += 1
                print(f"  ✅ Successfully scraped and stored")
            else:
                print(f"  ❌ Scraping failed: {content[:100]}")
                failed_count += 1

        # Step 2: Get today's conversations and send digest (now includes previously shared ones)
        conversations = get_conversations_by_date()
        message = await create_group_digest(conversations)
        await send_to_poke(message)

        # Step 3: Mark as shared
        if conversations:
            urls = [conv['chatgpt_url'] for conv in conversations]  # All conversations since we unshared them
            mark_conversations_as_shared(urls)

        return web.json_response({
            "status": "complete",
            "unshared_count": unshared_count,
            "scraped_count": scraped_count,
            "failed_count": failed_count,
            "total_unscraped": len(unscraped_links),
            "conversation_count": len(conversations),
            "digest_sent": True,
            "message_preview": message[:200] + "..." if len(message) > 200 else message
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def start_background_tasks(app):
    """Start background workers"""
    app['scrape_worker'] = asyncio.create_task(scrape_worker())
    app['digest_sender'] = asyncio.create_task(periodic_digest_sender())

async def cleanup_background_tasks(app):
    """Cleanup background tasks on shutdown"""
    app['scrape_worker'].cancel()
    app['digest_sender'].cancel()
    await app['scrape_worker']
    await app['digest_sender']

def create_app():
    """Create the webhook application"""
    app = web.Application()

    # Routes
    app.router.add_post('/webhook/new-link', handle_new_link)
    app.router.add_post('/webhook/trigger-digest', handle_trigger_digest)
    app.router.add_post('/webhook/scrape-all-pending', handle_scrape_all_pending)
    app.router.add_post('/webhook/test-full-flow', handle_test_full_flow)
    app.router.add_post('/webhook/setup-database', handle_setup_database)
    app.router.add_get('/health', handle_health)

    # Background tasks
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    return app

if __name__ == "__main__":
    app = create_app()
    print(f"Starting webhook service on port {WEBHOOK_PORT}")
    print(f"Endpoints:")
    print(f"  POST /webhook/new-link - Queue a URL for scraping")
    print(f"  POST /webhook/trigger-digest - Manually trigger digest")
    print(f"  POST /webhook/scrape-all-pending - Scrape all pending links")
    print(f"  POST /webhook/test-full-flow - TEST: Scrape all + send digest immediately")
    print(f"  POST /webhook/setup-database - Create database table manually")
    print(f"  GET /health - Health check")
    print(f"\nDigest will be sent every {DIGEST_INTERVAL_MINUTES} minutes")

    web.run_app(app, host="0.0.0.0", port=WEBHOOK_PORT)