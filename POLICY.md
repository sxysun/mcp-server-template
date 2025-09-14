  📤 Current Sharing Policy:

  1. Frequency: Every 10 minutes (configured by DIGEST_INTERVAL_MINUTES = 10)
  2. What gets shared:
    - Only conversations that have status = 'scraped'
    - Only today's conversations (by default)
    - Only conversations NOT already marked as shared (shared_to_group_at is NULL)
  3. Sharing logic (in periodic_digest_sender):
  # Lines 130-158 in webhook.py
  - Runs every 10 minutes
  - Gets all today's scraped conversations
  - Creates a digest with up to 2 summaries per user
  - Sends to Poke group chat
  - Marks shared URLs with timestamp so they won't be shared again
  4. Format sent to group:
  🎯 Daily ChatGPT Insights:

  💭 From xyn:
    • [First 150 chars of digest]...
    • [Second digest if exists]...

  💭 From seven:
    • [Their digests]...

  ✨ Share your own insights by submitting ChatGPT links!

