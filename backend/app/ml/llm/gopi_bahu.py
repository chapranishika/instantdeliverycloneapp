"""
Gopi Bahu LLM Assistant
Claude-powered grocery assistant — recipes, returns, and smart re-ranking.
"""
import logging
import os
from typing import AsyncGenerator, List, Optional

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-20250514"
API_URL           = "https://api.anthropic.com/v1/messages"

GOPI_BAHU_SYSTEM = """You are Gopi Bahu, the friendly AI grocery assistant for Zepto — India's fastest 10-minute delivery app.

Your personality:
- Warm, helpful, and enthusiastic about food and cooking
- Knowledgeable about Indian and international cuisines
- Concise but informative — users are on mobile, keep it punchy
- Always try to suggest relevant products the user can add to their cart

Your capabilities:
1. RECIPE ASSISTANT — suggest recipes based on ingredients or cravings, list required items
2. RETURN/REFUND HELP — guide users through the return process for damaged or expired items
3. SHOPPING HELP — recommend products, compare options, suggest alternatives
4. NUTRITION INFO — provide basic nutritional guidance

When suggesting recipes, always:
- List ingredients clearly with quantities
- Mention which ingredients can be ordered from Zepto
- Keep instructions simple and doable

When helping with returns:
- Be empathetic and solution-focused
- Explain the 48-hour return window for fresh items
- Guide them to the order history → refund flow

Format responses in clean markdown. Keep replies under 200 words unless a recipe requires more detail.
"""


class GopiBahuAssistant:
    """Wrapper around the Anthropic API for streaming and non-streaming responses."""

    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }

    # ------------------------------------------------------------------
    # Non-streaming (standard chat)
    # ------------------------------------------------------------------
    async def chat(
        self,
        messages: List[dict],
        user_context: Optional[dict] = None,
    ) -> str:
        """Single-turn or multi-turn chat, returns full response string."""
        system = GOPI_BAHU_SYSTEM
        if user_context:
            system += f"\n\nUser context: {user_context}"

        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "system": system,
            "messages": messages,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(API_URL, headers=self.headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    # ------------------------------------------------------------------
    # Streaming (for real-time chat UX)
    # ------------------------------------------------------------------
    async def chat_stream(
        self,
        messages: List[dict],
        user_context: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """Yield text chunks as they arrive (SSE → client)."""
        system = GOPI_BAHU_SYSTEM
        if user_context:
            system += f"\n\nUser context: {user_context}"

        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "stream": True,
            "system": system,
            "messages": messages,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST", API_URL, headers=self.headers, json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    import json
                    try:
                        chunk = json.loads(raw)
                        if chunk.get("type") == "content_block_delta":
                            text = chunk["delta"].get("text", "")
                            if text:
                                yield text
                    except Exception:
                        continue

    # ------------------------------------------------------------------
    # LLM-powered query expansion for search
    # ------------------------------------------------------------------
    async def expand_search_query(self, query: str) -> List[str]:
        """
        Turn a natural language search into multiple keyword variants.
        e.g. "something for pasta tonight" → ["pasta", "penne", "spaghetti", "marinara sauce"]
        """
        prompt = (
            f"A user typed this grocery search query: '{query}'\n\n"
            "Return 3-5 alternative search terms as a JSON array of strings. "
            "Only JSON, no explanation."
        )
        try:
            result = await self.chat([{"role": "user", "content": prompt}])
            import json, re
            match = re.search(r"\[.*?\]", result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as exc:
            logger.warning(f"Query expansion failed: {exc}")
        return [query]

    # ------------------------------------------------------------------
    # LLM re-ranking: explain why products match intent
    # ------------------------------------------------------------------
    async def rerank_with_intent(
        self, query: str, products: List[dict], top_k: int = 5
    ) -> List[dict]:
        """
        Given a user's natural-language intent and a list of candidate products,
        ask Claude to re-rank and return the best matches.
        Used in semantic search to go beyond vector similarity.
        """
        if not products:
            return []

        product_list = "\n".join(
            f"{i+1}. {p.get('product_name','?')} ({p.get('department','?')})"
            for i, p in enumerate(products[:15])
        )
        prompt = (
            f"User intent: '{query}'\n\n"
            f"Candidate products:\n{product_list}\n\n"
            f"Return the indices (1-based) of the top {top_k} most relevant products "
            "as a JSON array of integers. Only JSON."
        )
        try:
            result = await self.chat([{"role": "user", "content": prompt}])
            import json, re
            match = re.search(r"\[.*?\]", result, re.DOTALL)
            if match:
                indices = json.loads(match.group())
                reranked = []
                for idx in indices:
                    if 1 <= idx <= len(products):
                        reranked.append(products[idx - 1])
                return reranked
        except Exception as exc:
            logger.warning(f"LLM re-rank failed: {exc}")
        return products[:top_k]


_assistant: Optional[GopiBahuAssistant] = None


def get_assistant() -> GopiBahuAssistant:
    global _assistant
    if _assistant is None:
        _assistant = GopiBahuAssistant()
    return _assistant
