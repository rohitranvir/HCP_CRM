"""
interactions/agent_router.py
AI-First CRM HCP Module — Agent Router

Lightweight gateway that:
    1. Accepts a user message + optional interaction_id / hcp_name
    2. Detects intent via LLM (ChatGroq gemma2-9b-it)
    3. Calls the appropriate LangGraph agent tool
    4. Returns { tool_name, intent, result, error } as a structured dict

Can be used:
    - Directly as a Python module
    - Via the Django REST API endpoint (interactions/views.py → AgentView)
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

# ─── Intent → human-readable label map ───────────────────────────────────────

INTENT_LABELS: dict[str, str] = {
    "log_interaction":   "Log New Interaction",
    "edit_interaction":  "Edit Existing Interaction",
    "suggest_followup":  "Suggest Follow-up Actions",
    "search_hcp":        "Search HCP Records",
    "summarize_history": "Summarize HCP History",
    "unknown":           "Unknown Request",
}

VALID_INTENTS = set(INTENT_LABELS.keys())

# ─── Example phrases shown to the LLM for few-shot guidance ──────────────────

INTENT_EXAMPLES = """
Examples:
- "Logged a visit with Dr. Sharma on Monday..." → log_interaction
- "Change the sentiment of interaction 12 to positive" → edit_interaction
- "Update the date for interaction 7 to tomorrow" → edit_interaction
- "What should I do next for interaction 5?" → suggest_followup
- "Give me follow-up ideas for my last call with Dr. Rao" → suggest_followup
- "Find Dr. Mehra's profile" → search_hcp
- "Look up all cardiologists named Patel" → search_hcp
- "Summarise all interactions with Dr. Kapoor" → summarize_history
- "Give me a history of my engagement with Dr. Joshi" → summarize_history
"""


def _get_llm() -> ChatOpenAI:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set.")
    return ChatOpenAI(
        model="openai/gpt-oss-120b",
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.0,
        max_tokens=50,  # Intent classifier only returns 1-3 words
    )



# ─── Keyword-based fallback intent detector ───────────────────────────────────

_KEYWORD_MAP: list[tuple[list[str], str]] = [
    # log_interaction — phrases about recording/logging a new visit
    (["met ", "visited ", "had a meeting", "in-person visit", "called on", "spoke with",
      "today i ", "yesterday i ", "discussed with dr", "interaction with dr",
      "log this", "log interaction", "record this", "record interaction"], "log_interaction"),
    # edit_interaction — modifying an existing record
    (["change the", "update the", "correct the", "edit interaction", "modify interaction",
      "change sentiment", "update sentiment", "update outcome", "change outcome",
      "update date", "change date", "update field", "edit record"], "edit_interaction"),
    # suggest_followup — follow-up recommendations
    (["suggest follow", "follow-up", "followup", "next steps for interaction",
      "what should i do next", "recommend next", "follow up actions"], "suggest_followup"),
    # summarize_history — history summary
    (["summarize", "summarise", "summary of", "history of", "engagement history",
      "past interactions", "interaction history", "all interactions with"], "summarize_history"),
    # search_hcp — lookup (lowest priority, kept last)
    (["find ", "search for", "look up", "lookup", "show me", "get hcp", "find hcp",
      "find dr", "search dr"], "search_hcp"),
]


def _keyword_intent(user_message: str) -> str | None:
    """Return intent by keyword matching, or None if no match."""
    msg = user_message.lower()
    for keywords, intent in _KEYWORD_MAP:
        if any(kw in msg for kw in keywords):
            return intent
    return None


# ─── Step 1: Fast intent detection (standalone, no full graph overhead) ───────

def detect_intent(user_message: str) -> str:
    """
    Classify user intent using a 3-layer approach:
      1. LLM exact match
      2. Regex scan inside verbose LLM output
      3. Keyword fallback

    Returns:
        str: one of the VALID_INTENTS keys
    """
    import re

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are an intent classifier for a pharmaceutical CRM AI assistant.

Classify the user's message into EXACTLY ONE of these intents:
- log_interaction      : recording/logging a new HCP interaction
- edit_interaction     : modifying/correcting an existing interaction record
- suggest_followup     : generating follow-up action recommendations
- search_hcp           : finding or looking up an HCP record
- summarize_history    : summarising past interaction history for an HCP
- unknown              : off-topic, gibberish, or unrelated input

{INTENT_EXAMPLES}
- "asdfjkl" → unknown
- "tell me a joke" → unknown

Respond with ONLY the intent name (snake_case). No punctuation. No explanation.
Example responses: log_interaction  /  search_hcp  /  unknown"""),
        ("human", "{message}"),
    ])

    try:
        chain    = prompt | _get_llm()
        response = chain.invoke({"message": user_message})
        raw      = response.content.strip().lower()

        # ── Layer 1: exact match ───────────────────────────────────────────
        cleaned = raw.replace("-", "_").replace(" ", "_").split("\n")[0].strip(".:,'\"")
        if cleaned in VALID_INTENTS:
            return cleaned

        # ── Layer 2: regex scan — find any valid intent inside verbose output
        for intent in VALID_INTENTS:
            if re.search(rf"\b{re.escape(intent)}\b", raw):
                logger.info("Intent extracted via regex from verbose output: '%s'", intent)
                return intent

        # ── Layer 3: keyword fallback ─────────────────────────────────────
        kw_intent = _keyword_intent(user_message)
        if kw_intent:
            logger.info("Intent determined via keyword fallback: '%s'", kw_intent)
            return kw_intent

        logger.warning("All intent layers failed for: '%s' — defaulting to unknown", raw)
        return "unknown"

    except Exception as exc:
        logger.exception("Intent detection failed: %s", exc)
        # Even on exception, try keyword fallback before giving up
        return _keyword_intent(user_message) or "unknown"



# ─── Step 2: Route to agent ───────────────────────────────────────────────────

def route(
    user_message:   str,
    interaction_id: Optional[int] = None,
    hcp_name:       Optional[str] = None,
) -> dict:
    """
    Full router pipeline:
        detect intent → invoke agent → return structured result

    Args:
        user_message:   Natural language string from the user / frontend.
        interaction_id: Required for edit_interaction and suggest_followup.
        hcp_name:       Optional hint for search_hcp and summarize_history.

    Returns:
        {
            "tool":         str,          # e.g. "log_interaction_tool"
            "tool_label":   str,          # Human readable label
            "intent":       str,          # Raw intent key
            "result":       dict,         # Tool output
            "error":        str,          # Empty string if no error
            "input": {
                "message":        str,
                "interaction_id": int | None,
                "hcp_name":       str | None,
            }
        }
    """
    # ── Validate inputs ───────────────────────────────────────────────────
    if not user_message or not user_message.strip():
        return _error_response(
            "user_message is required and cannot be empty.",
            user_message, interaction_id, hcp_name,
        )

    # ── Detect intent ─────────────────────────────────────────────────────
    intent = detect_intent(user_message)
    logger.info("Router detected intent: '%s' for message: '%s'", intent, user_message[:80])

    if intent == "unknown":
        return {
            "tool":       "unknown",
            "tool_label": "Unknown Request",
            "intent":     "unknown",
            "result":     {
                "message": "👋 I'm your CRM assistant! I didn't quite catch that. I can help you with the following tasks. What would you like to do?",
                "options": [
                    "Log a New Interaction",
                    "Search for an HCP",
                    "Summarize HCP History",
                    "Suggest Follow-up Actions"
                ]
            },
            "error":      "",
            "input": {
                "message":        user_message,
                "interaction_id": interaction_id,
                "hcp_name":       hcp_name,
            },
        }

    # ── Guard: edit / suggest require interaction_id ──────────────────────
    if intent in ("edit_interaction", "suggest_followup") and not interaction_id:
        # Attempt to parse from message
        import re
        match = re.search(r"\b(\d+)\b", user_message)
        if match:
            interaction_id = int(match.group(1))
            logger.info("Router auto-extracted interaction_id=%s from message", interaction_id)
        else:
            return {
                "tool":       intent + "_tool",
                "tool_label": INTENT_LABELS.get(intent, intent),
                "intent":     intent,
                "result":     {},
                "error":      (
                    f"'{intent}' requires an interaction_id. "
                    "Please provide the interaction ID."
                ),
                "input": {
                    "message":        user_message,
                    "interaction_id": None,
                    "hcp_name":       hcp_name,
                },
            }

    # ── Invoke LangGraph agent ────────────────────────────────────────────
    try:
        from interactions.agent import run_agent
        agent_response = run_agent(
            user_message=user_message,
            interaction_id=interaction_id,
            hcp_name=hcp_name,
        )
    except Exception as exc:
        logger.exception("Agent invocation failed: %s", exc)
        return _error_response(
            f"Agent execution error: {exc}",
            user_message, interaction_id, hcp_name,
        )

    return {
        "tool":       agent_response.get("tool",   intent + "_tool"),
        "tool_label": INTENT_LABELS.get(intent, intent),
        "intent":     agent_response.get("intent", intent),
        "result":     agent_response.get("result", {}),
        "error":      agent_response.get("error",  ""),
        "input": {
            "message":        user_message,
            "interaction_id": interaction_id,
            "hcp_name":       hcp_name,
        },
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _error_response(
    error:          str,
    user_message:   str,
    interaction_id: Optional[int],
    hcp_name:       Optional[str],
) -> dict:
    return {
        "tool":       "unknown",
        "tool_label": "Unknown",
        "intent":     "unknown",
        "result":     {},
        "error":      error,
        "input": {
            "message":        user_message,
            "interaction_id": interaction_id,
            "hcp_name":       hcp_name,
        },
    }


# ─── Convenience wrapper ──────────────────────────────────────────────────────

class AgentRouter:
    """
    Class-based wrapper for use in Django views and tests.

    Usage:
        router = AgentRouter()
        response = router.process("Log a call with Dr. Kapoor today.")
    """

    def process(
        self,
        user_message:   str,
        interaction_id: Optional[int] = None,
        hcp_name:       Optional[str] = None,
    ) -> dict:
        return route(
            user_message=user_message,
            interaction_id=interaction_id,
            hcp_name=hcp_name,
        )

    def detect(self, user_message: str) -> dict:
        """Only detect intent — no tool invocation."""
        intent = detect_intent(user_message)
        return {
            "intent":     intent,
            "tool_label": INTENT_LABELS.get(intent, intent),
        }
