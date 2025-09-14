import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    """Get a database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def create_table():
    """Create the riff table if it doesn't exist"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS riff (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    chatgpt_url TEXT NOT NULL UNIQUE,
                    user_name VARCHAR(255),
                    conversation_content TEXT,
                    digest TEXT,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    scraped_at TIMESTAMP,
                    shared_to_group_at TIMESTAMP,
                    metadata JSONB
                )
            """)
            conn.commit()

def insert_link(url: str, user_name: str) -> str:
    """Insert a new ChatGPT link into the database"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO riff (chatgpt_url, user_name, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT (chatgpt_url) DO NOTHING
                RETURNING id
            """, (url, user_name))
            result = cur.fetchone()
            conn.commit()
            return str(result['id']) if result else None

def update_conversation_content(url: str, content: str, digest: str = None):
    """Update the conversation content after scraping"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE riff
                SET conversation_content = %s,
                    digest = %s,
                    status = 'scraped',
                    scraped_at = NOW()
                WHERE chatgpt_url = %s
            """, (content, digest, url))
            conn.commit()

def get_distinct_users() -> List[str]:
    """Get all distinct user names who have submitted links"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT user_name
                FROM riff
                WHERE user_name IS NOT NULL
                ORDER BY user_name
            """)
            return [row['user_name'] for row in cur.fetchall()]

def get_conversations_by_date(date: Optional[str] = None) -> List[Dict]:
    """Get all conversations for a specific date"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if date:
                cur.execute("""
                    SELECT chatgpt_url, user_name, digest, conversation_content, created_at
                    FROM riff
                    WHERE DATE(created_at) = %s
                    AND status = 'scraped'
                    ORDER BY created_at DESC
                """, (date,))
            else:
                cur.execute("""
                    SELECT chatgpt_url, user_name, digest, conversation_content, created_at
                    FROM riff
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND status = 'scraped'
                    ORDER BY created_at DESC
                """)
            return cur.fetchall()

def get_user_submissions(user_name: str) -> List[Dict]:
    """Get all submissions from a specific user"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT chatgpt_url, digest, status, created_at, shared_to_group_at
                FROM riff
                WHERE user_name = %s
                ORDER BY created_at DESC
            """, (user_name,))
            return cur.fetchall()

def get_conversation_by_url(url: str) -> Dict:
    """Get full conversation details by URL"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM riff
                WHERE chatgpt_url = %s
            """, (url,))
            return cur.fetchone()

def mark_conversations_as_shared(urls: List[str]) -> int:
    """Mark multiple conversations as shared to group"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE riff
                SET shared_to_group_at = NOW()
                WHERE chatgpt_url = ANY(%s)
                AND shared_to_group_at IS NULL
            """, (urls,))
            conn.commit()
            return cur.rowcount

def mark_all_conversations_as_unshared() -> int:
    """Mark all conversations as unshared (for testing purposes)"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE riff
                SET shared_to_group_at = NULL
                WHERE shared_to_group_at IS NOT NULL
            """)
            conn.commit()
            return cur.rowcount

# Initialize table on module import
if DATABASE_URL:
    try:
        create_table()
    except Exception as e:
        print(f"Warning: Could not create table: {e}")