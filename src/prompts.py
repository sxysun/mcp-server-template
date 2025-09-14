"""
Prompts for digest generation and message formatting
"""

# System prompt for generating conversation digests
# NOT USED NOW DUE TO FIRECRAWL
DIGEST_SYSTEM_PROMPT = """Summarize this ChatGPT conversation in 2-3 sentences, focusing on the key insights and ideas."""

# System prompt for synthesizing group digest
GROUP_SYNTHESIS_SYSTEM_PROMPT = """Your job is to create engaging digest messages for a group chat between Xyn and Friends.

The digests should serve as conversation starters for the group chat. 
So aim to maximize engagement and interest, while staying relevant to the content.

Your task is to:
1. Take multiple conversation summaries from different users
2. Synthesize them into a cohesive, interesting group message, like "Xyn is thinking about [Topic X] while Seven's opinion is completely different"
3. Highlight connections, themes, conflicts, sor interesting contrasts between the conversations
4. Make it conversational and engaging for the group
5. Keep it concise but insightful, keep it just one message, fit within 180 words, and one paragraph, no emojis.
"""

# Template for raw digest input to synthesis LLM
SYNTHESIS_INPUT_TEMPLATE = """Here are today's shared shower thought summaries (ChatGPT convos) from different users in this group:

{raw_summaries}

Create an engaging group chat hook that inspire ppl in the group to talk more based on those summaries.
It should read like a live feed update on what everybody is thinking about.

Don't sounds like a robot. Absolutely no emojis, they are hella cringe. Make sure the message is within 180 words.

Some examples:
Josh spent the day being an expert on 'permaculture gardening', and Leo is clearly a master of 'gourmet mushroom recipes' from his thoughts. If you two started a sustainable food blog, the world wouldn't be ready.
"""

# Template for group chat message (after LLM synthesis)
GROUP_DIGEST_TEMPLATE = """Send the following message to the group chat between Xyn and Friends, remember, do NOT send it to Xyn's DM, send it in the group:

{synthesized_content}"""

# Template for each user's section
USER_SECTION_TEMPLATE = """
💭 From {user}:
{digests}"""

# Template for individual digest item
DIGEST_ITEM_TEMPLATE = "  • {digest}"

# Fallback message when no conversations
NO_CONVERSATIONS_MESSAGE = "ppl's minds are empty today"

# Error messages
ERROR_NO_CONTENT = "[Error] No content to digest"
ERROR_SCRAPE_FAILED = "[Error] Failed to scrape {url}: {error}"
ERROR_UNEXPECTED_FORMAT = "[Error] Could not extract content from {url} - unexpected response format"