#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from typing import List, Dict, Optional
from datetime import datetime

# Import our modules
from database import (
    insert_link,
    update_conversation_content,
    get_distinct_users,
    get_conversations_by_date,
    get_user_submissions,
    get_conversation_by_url,
    mark_conversations_as_shared
)

mcp = FastMCP("ChatGPT Riff Server")

@mcp.tool(description="Submit a ChatGPT conversation link for processing and storage")
def submit_chatgpt_link(url: str, user_name: str) -> dict:
    """
    Submit a ChatGPT share URL to be scraped and stored in the database.
    The link will be queued for async scraping via webhook.

    Args:
        url: ChatGPT share URL (e.g., https://chatgpt.com/share/...)
        user_name: Name of the user submitting (e.g., "xyn", "seven")

    Returns:
        Status of the submission and link ID
    """
    import requests

    # Validate URL format
    if not url.startswith("https://chatgpt.com/share/"):
        return {"error": "Invalid ChatGPT share URL format"}

    # Insert link into database with 'pending' status
    link_id = insert_link(url, user_name)

    if not link_id:
        return {"status": "already_exists", "url": url, "user": user_name}

    # Trigger webhook for async scraping
    try:
        webhook_url = f"http://localhost:{os.environ.get('WEBHOOK_PORT', 8001)}/webhook/new-link"
        response = requests.post(webhook_url, json={"url": url}, timeout=5)

        if response.status_code == 200:
            return {
                "status": "queued",
                "id": link_id,
                "user": user_name,
                "url": url,
                "message": "Link queued for processing. Check back later for results."
            }
        else:
            return {
                "status": "queued_webhook_failed",
                "id": link_id,
                "user": user_name,
                "url": url,
                "message": "Link stored but webhook notification failed. Will be processed later."
            }

    except Exception as e:
        # Even if webhook fails, the link is stored
        return {
            "status": "queued_webhook_error",
            "id": link_id,
            "user": user_name,
            "url": url,
            "message": f"Link stored but webhook error: {str(e)}"
        }

@mcp.tool(description="Get list of all users who have submitted ChatGPT links")
def get_known_users() -> List[str]:
    """
    Returns a list of all users who have submitted links to the system.

    Returns:
        List of user names (e.g., ["xyn", "seven", "other_user"])
    """
    return get_distinct_users()

@mcp.tool(description="Get all ChatGPT conversations for a specific day for synthesis")
def get_daily_conversations(date: Optional[str] = None) -> List[Dict]:
    """
    Retrieve all scraped conversations for a specific date.

    Args:
        date: Date in YYYY-MM-DD format (defaults to today if not provided)

    Returns:
        List of conversation summaries with user info and digests
    """
    conversations = get_conversations_by_date(date)

    # Format for easier consumption
    return [
        {
            "user": conv['user_name'],
            "url": conv['chatgpt_url'],
            "digest": conv['digest'],
            "timestamp": conv['created_at'].isoformat() if conv['created_at'] else None
        }
        for conv in conversations
    ]

@mcp.tool(description="Get all ChatGPT link submissions from a specific user")
def get_user_submissions(user_name: str) -> List[Dict]:
    """
    Get all ChatGPT links submitted by a specific user.

    Args:
        user_name: Name of the user (e.g., "xyn")

    Returns:
        List of submissions with status and timestamps
    """
    from database import get_user_submissions as get_user_submissions_db
    submissions = get_user_submissions_db(user_name)

    return [
        {
            "url": sub['chatgpt_url'],
            "digest": sub['digest'],
            "status": sub['status'],
            "submitted_at": sub['created_at'].isoformat() if sub['created_at'] else None,
            "shared_to_group": sub['shared_to_group_at'].isoformat() if sub['shared_to_group_at'] else None
        }
        for sub in submissions
    ]

@mcp.tool(description="Get full conversation content and details for a specific ChatGPT URL")
def get_conversation_details(url: str) -> Dict:
    """
    Fetch the full conversation content and metadata for a specific URL.

    Args:
        url: ChatGPT share URL

    Returns:
        Full conversation details including content and metadata
    """
    conversation = get_conversation_by_url(url)

    if not conversation:
        return {"error": "Conversation not found"}

    return {
        "url": conversation['chatgpt_url'],
        "user": conversation['user_name'],
        "content": conversation['conversation_content'],
        "digest": conversation['digest'],
        "status": conversation['status'],
        "created_at": conversation['created_at'].isoformat() if conversation['created_at'] else None,
        "scraped_at": conversation['scraped_at'].isoformat() if conversation['scraped_at'] else None,
        "shared_at": conversation['shared_to_group_at'].isoformat() if conversation['shared_to_group_at'] else None
    }

@mcp.tool(description="Mark conversations as shared to the group chat")
def mark_as_shared(urls: List[str]) -> Dict:
    """
    Mark one or more conversations as having been shared to the group.

    Args:
        urls: List of ChatGPT share URLs to mark as shared

    Returns:
        Count of conversations marked as shared
    """
    count = mark_conversations_as_shared(urls)

    return {
        "status": "success",
        "marked_count": count,
        "urls": urls
    }

@mcp.tool(description="Get comprehensive server information, UX flows, and Poke integration instructions")
def get_server_info() -> dict:
    return {
        "server_name": "ChatGPT Riff Server",
        "version": "1.0.0",
        "description": "A system that allows users to privately share ChatGPT conversations with Poke, which processes and periodically shares synthesized insights to group chats",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": os.sys.version.split()[0],

        "poke_role_and_responsibilities": {
            "overview": "Poke acts as a bridge between private user submissions and group conversation starters",
            "user_dm_interactions": {
                "automatic_chatgpt_link_detection": {
                    "trigger": "ALWAYS when you detect ANY ChatGPT share link (https://chatgpt.com/share/...) in user messages",
                    "action": "IMMEDIATELY call submit_chatgpt_link function to submit the link to the server",
                    "response": "Confirm receipt to the user in their DM",
                    "note": "This should happen automatically - user doesn't need to ask"
                },
                "explicit_riff_requests": {
                    "trigger": "When users say 'riff it', 'riff this', or similar phrases with a ChatGPT link",
                    "action": "IMMEDIATELY call submit_chatgpt_link function to submit the link to the server",
                    "response": "Confirm that you're processing their ChatGPT conversation for the group riff",
                    "note": "Users can explicitly request riffing of their shared thoughts"
                },
                "general_rule": "ANY TIME you see a ChatGPT share URL, automatically submit it using submit_chatgpt_link - no exceptions"
            },
            "group_chat_interactions": {
                "intelligent_sharing": {
                    "trigger": "Webhook messages with synthesized digests",
                    "decision_making": "YOU decide whether the digest is worth sharing based on group context, recent conversations, and content quality",
                    "criteria_for_sharing": [
                        "Content is genuinely interesting or thought-provoking",
                        "Would spark good discussion in the group",
                        "Not repetitive of recent group topics",
                        "Timing feels right based on group activity"
                    ],
                    "if_worth_sharing": "Send to GROUP CHAT between Xyn and Friends (NOT individual DMs)",
                    "if_not_worth_sharing": "Simply acknowledge receipt privately, don't forward to group",
                    "follow_up": "Use mark_as_shared to update which conversations have been shared (only if you shared them)"
                },
                "quality_over_frequency": {
                    "principle": "Only share digests that are actually worth the group's attention",
                    "note": "The group should not be spammed with every digest - use your judgment"
                }
            },
            "user_inquiry_responses": {
                "submission_history": "Use get_user_submissions to show users what they've shared",
                "conversation_details": "Use get_conversation_details for specific information about shared conversations",
                "user_list": "Use get_known_users to see who has been participating"
            }
        },

        "ux_flow": {
            "automatic_flow": {
                "step_1": "User shares ChatGPT link with Poke (via DM or mentions)",
                "step_2": "Poke AUTOMATICALLY detects ChatGPT link and calls submit_chatgpt_link",
                "step_3": "Server scrapes conversation and generates digest asynchronously",
                "step_4": "Webhook sends synthesized group message to Poke",
                "step_5": "Poke shares the synthesized insights in the GROUP CHAT (not DMs)",
                "note": "This happens automatically when Poke sees any ChatGPT share link"
            },
            "explicit_flow": {
                "step_1": "User shares thoughts/content and says 'riff it' or 'riff this'",
                "step_2": "If there's a ChatGPT link, Poke calls submit_chatgpt_link immediately",
                "step_3": "Same processing and group sharing flow as above",
                "note": "Users can explicitly request riffing of their shared content"
            },
            "result": "Private thoughts become engaging conversation starters for the group while maintaining sharer privacy"
        },

        "mcp_functions": {
            "submit_chatgpt_link": {
                "purpose": "Submit a ChatGPT share URL for processing",
                "params": ["url", "user_name"],
                "use_case": "When users share ChatGPT links in DMs"
            },
            "get_daily_conversations": {
                "purpose": "Retrieve all processed conversations for synthesis",
                "params": ["date (optional)"],
                "use_case": "For creating group digest messages"
            },
            "get_user_submissions": {
                "purpose": "Get submission history for specific user",
                "params": ["user_name"],
                "use_case": "When users ask about their sharing history"
            },
            "get_conversation_details": {
                "purpose": "Get full details of a specific conversation",
                "params": ["url"],
                "use_case": "For detailed conversation lookups"
            },
            "mark_as_shared": {
                "purpose": "Mark conversations as shared to prevent duplicates",
                "params": ["urls"],
                "use_case": "After successfully sharing to group chat"
            },
            "get_known_users": {
                "purpose": "Get list of all users who have shared conversations",
                "params": [],
                "use_case": "For user management and statistics"
            }
        },

        "technical_details": {
            "features": [
                "chatgpt_link_submission",
                "firecrawl_scraping",
                "openrouter_digest_generation",
                "async_webhook_processing",
                "user_tracking",
                "daily_digest_compilation",
                "poke_integration",
                "postgresql_storage"
            ],
            "webhook_service": f"http://localhost:{os.environ.get('WEBHOOK_PORT', 8001)}",
            "database": "PostgreSQL via DATABASE_URL"
        },

        "critical_reminders_for_poke": [
            "AUTOMATICALLY submit ANY ChatGPT link you see using submit_chatgpt_link - no exceptions",
            "Users don't need to ask - just seeing a ChatGPT link should trigger submission",
            "When users say 'riff it' with a link, that's an explicit request to process it",
            "NEVER send webhook messages to individual user DMs",
            "ALWAYS send synthesized insights to the GROUP CHAT",
            "Webhook messages are pre-formatted and ready for group sharing",
            "Mark conversations as shared after successful group delivery",
            "Individual user submissions should be private until synthesized for group"
        ]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"

    print(f"Starting ChatGPT Riff MCP server on {host}:{port}")

    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )
