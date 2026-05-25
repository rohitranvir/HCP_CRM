"""
interactions/agent.py
AI-First CRM HCP Module — LangGraph Agent

StateGraph with 5 tools powered by GPT-OSS 120B via Groq OpenAI-compatible API:
    1. log_interaction_tool     — NL → extract fields → save to DB
    2. edit_interaction_tool    — NL correction → patch specific fields
    3. suggest_followup_tool    — interaction_id → 3 LLM suggestions
    4. search_hcp_tool          — name string → matching HCP records
    5. summarize_history_tool   — hcp_name → AI paragraph summary

Flow:
    user_message → [intent_node] → [tool_router] → [tool_node] → [format_node] → END
"""

from __future__ import annotations

import os
import json
import logging
from datetime import date, datetime
from typing import TypedDict, Optional, Any

import django
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# ─── Ensure Django is ready (for standalone / test use) ──────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hcp_crm.settings")
try:
    django.setup()
except RuntimeError:
    pass  # Already set up inside a running Django process


# ─── LLM Factory ─────────────────────────────────────────────────────────────

def _llm(temperature: float = 0.1) -> ChatOpenAI:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY environment variable is not set.")
    return ChatOpenAI(
        model="openai/gpt-oss-120b",
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=temperature,
        max_tokens=1024,  # Sufficient for JSON extraction & summaries; fits Groq free TPM limit
    )


# ─── State Schema ─────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    user_message:   str
    interaction_id: Optional[int]
    hcp_name:       Optional[str]

    # Routing
    intent:         str           # one of the 5 tool names

    # Tool output
    tool_name:      str
    tool_result:    dict          # always a structured dict
    error:          str

    # Final
    final_response: dict


# ─── Intent Constants ─────────────────────────────────────────────────────────

INTENTS = {
    "log_interaction":    "log_interaction_tool",
    "edit_interaction":   "edit_interaction_tool",
    "suggest_followup":   "suggest_followup_tool",
    "search_hcp":         "search_hcp_tool",
    "summarize_history":  "summarize_history_tool",
}


# ═════════════════════════════════════════════════════════════════════════════
#  NODE 1 — Intent Classifier
# ═════════════════════════════════════════════════════════════════════════════

def intent_node(state: AgentState) -> AgentState:
    """
    Classify user message into one of 5 intents using the LLM.
    Writes: state['intent']
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an intent classifier for a pharmaceutical CRM system.

Classify the user's message into EXACTLY ONE of these intents:
- log_interaction      : User wants to log / record a new HCP interaction
- edit_interaction     : User wants to modify / correct an existing interaction
- suggest_followup     : User wants follow-up action suggestions for an interaction
- search_hcp           : User wants to find / look up an HCP record
- summarize_history    : User wants a summary of all past interactions with an HCP

Respond with ONLY the intent name, nothing else. No punctuation, no explanation."""),
        ("human", "{message}"),
    ])

    try:
        chain    = prompt | _llm()
        response = chain.invoke({"message": state["user_message"]})
        intent   = response.content.strip().lower().replace("-", "_")

        if intent not in INTENTS:
            logger.warning("Unknown intent '%s' — defaulting to search_hcp", intent)
            intent = "search_hcp"

        state["intent"] = intent
        state["error"]  = ""

    except Exception as exc:
        logger.exception("Intent classification failed: %s", exc)
        state["intent"] = "search_hcp"
        state["error"]  = f"Intent classification error: {exc}"

    return state


# ═════════════════════════════════════════════════════════════════════════════
#  NODE 2 — Tool Router (conditional edge resolver)
# ═════════════════════════════════════════════════════════════════════════════

def route_intent(state: AgentState) -> str:
    """Maps intent → next node name for LangGraph conditional edge."""
    return state.get("intent", "search_hcp")


# ═════════════════════════════════════════════════════════════════════════════
#  TOOL 1 — log_interaction_tool
# ═════════════════════════════════════════════════════════════════════════════

def log_interaction_tool(state: AgentState) -> AgentState:
    """
    Parse natural language → extract structured fields → save Interaction to DB.
    """
    from interactions.models import HCP, Interaction

    today = date.today().isoformat()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a CRM data-extraction assistant.
Today's date is {today}.

Extract interaction details from the user's message and return a JSON object with ONLY these keys:
{{
  "hcp_name":           "<string — full name of the doctor/HCP>",
  "interaction_type":   "<one of: in_person|virtual|phone|email|conference|webinar|other>",
  "date":               "<YYYY-MM-DD>",
  "time":               "<HH:MM:SS or null>",
  "attendees":          ["<name>", ...],
  "topics_discussed":   "<string>",
  "materials_shared":   ["<item>", ...],
  "samples_distributed":["<item>", ...],
  "sentiment":          "<one of: very_positive|positive|neutral|negative|very_negative|unknown>",
  "outcomes":           "<string>"
}}

Rules:
- If a field is not mentioned, use null for strings or [] for arrays.
- For date, infer from context (e.g. "today", "yesterday") relative to {today}.
- Return ONLY valid JSON. No markdown, no explanation."""),
        ("human", "{message}"),
    ])

    try:
        chain    = prompt | _llm(temperature=0.0)
        response = chain.invoke({"message": state["user_message"], "today": today})

        raw      = response.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        fields: dict = json.loads(raw)

    except (json.JSONDecodeError, Exception) as exc:
        logger.exception("log_interaction_tool LLM extraction failed: %s", exc)
        state["tool_name"]   = "log_interaction_tool"
        state["tool_result"] = {}
        state["error"]       = f"Field extraction failed: {exc}"
        return state

    # ── Resolve HCP ───────────────────────────────────────────────────────
    hcp_name = fields.get("hcp_name", "")
    hcp = None
    if hcp_name:
        hcp_qs = HCP.objects.filter(name__icontains=hcp_name, is_active=True)
        hcp    = hcp_qs.first()

    if not hcp:
        logger.warning("HCP '%s' not found — skipping DB save.", hcp_name)
        state["tool_name"]   = "log_interaction_tool"
        state["tool_result"] = {
            "status":          "hcp_not_found",
            "extracted_fields": fields,
            "message":         f"No active HCP found matching '{hcp_name}'. "
                               "Create the HCP record first.",
        }
        state["error"] = ""
        return state

    # ── Build Interaction ─────────────────────────────────────────────────
    try:
        raw_date = fields.get("date") or today
        raw_time = fields.get("time")

        interaction = Interaction(
            hcp               = hcp,
            interaction_type  = fields.get("interaction_type", "other"),
            date              = datetime.strptime(raw_date, "%Y-%m-%d").date(),
            time              = (
                datetime.strptime(raw_time, "%H:%M:%S").time() if raw_time else None
            ),
            attendees          = fields.get("attendees")         or [],
            topics_discussed   = fields.get("topics_discussed")  or "",
            materials_shared   = fields.get("materials_shared")  or [],
            samples_distributed= fields.get("samples_distributed") or [],
            sentiment          = fields.get("sentiment",  "unknown"),
            outcomes           = fields.get("outcomes")   or "",
            ai_processed       = True,
        )
        interaction.full_clean()
        interaction.save()

        state["tool_result"] = {
            "status":         "created",
            "interaction_id": interaction.pk,
            "hcp_id":         hcp.pk,
            "hcp_name":       hcp.name,
            "extracted_fields": fields,
        }
        state["error"] = ""

    except Exception as exc:
        logger.exception("Interaction DB save failed: %s", exc)
        state["tool_result"] = {"status": "db_error", "extracted_fields": fields}
        state["error"]       = f"DB save error: {exc}"

    state["tool_name"] = "log_interaction_tool"
    return state


# ═════════════════════════════════════════════════════════════════════════════
#  TOOL 2 — edit_interaction_tool
# ═════════════════════════════════════════════════════════════════════════════

def edit_interaction_tool(state: AgentState) -> AgentState:
    """
    Identify ONLY the fields that need changing from NL correction text,
    then patch those fields on the Interaction record.
    """
    from interactions.models import Interaction

    interaction_id = state.get("interaction_id")
    if not interaction_id:
        state["tool_name"]   = "edit_interaction_tool"
        state["tool_result"] = {"status": "error"}
        state["error"]       = "interaction_id is required for edit_interaction_tool."
        return state

    try:
        interaction = Interaction.objects.select_related("hcp").get(pk=interaction_id)
    except Interaction.DoesNotExist:
        state["tool_name"]   = "edit_interaction_tool"
        state["tool_result"] = {"status": "not_found"}
        state["error"]       = f"Interaction {interaction_id} not found."
        return state

    # ── Build current snapshot for LLM context ────────────────────────────
    current = {
        "interaction_type":   interaction.interaction_type,
        "date":               str(interaction.date),
        "time":               str(interaction.time) if interaction.time else None,
        "attendees":          interaction.attendees,
        "topics_discussed":   interaction.topics_discussed,
        "materials_shared":   interaction.materials_shared,
        "samples_distributed":interaction.samples_distributed,
        "sentiment":          interaction.sentiment,
        "outcomes":           interaction.outcomes,
        "follow_up_actions":  interaction.follow_up_actions,
        "rep_notes":          interaction.rep_notes,
    }

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a CRM edit assistant.

The user wants to correct an existing HCP interaction record.
Current record:
{current_json}

From the user's correction message, identify ONLY the fields that should change.
Return a JSON object with ONLY the changed fields (do NOT include unchanged fields).
Use the same field names and value formats as the current record.
Return ONLY valid JSON. No markdown, no explanation."""),
        ("human", "{message}"),
    ])

    try:
        chain    = prompt | _llm(temperature=0.0)
        response = chain.invoke({
            "current_json": json.dumps(current, indent=2),
            "message":      state["user_message"],
        })
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        changes: dict = json.loads(raw)

    except (json.JSONDecodeError, Exception) as exc:
        logger.exception("edit_interaction_tool LLM extraction failed: %s", exc)
        state["tool_name"]   = "edit_interaction_tool"
        state["tool_result"] = {}
        state["error"]       = f"Field extraction failed: {exc}"
        return state

    # ── Apply only changed fields ─────────────────────────────────────────
    ALLOWED_FIELDS = {
        "interaction_type", "date", "time", "attendees",
        "topics_discussed", "materials_shared", "samples_distributed",
        "sentiment", "outcomes", "follow_up_actions", "rep_notes",
    }

    updated_fields = []
    try:
        for field, value in changes.items():
            if field not in ALLOWED_FIELDS:
                continue
            if field == "date" and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            if field == "time" and value:
                try:
                    value = datetime.strptime(value, "%H:%M:%S").time()
                except ValueError:
                    value = None
            setattr(interaction, field, value)
            updated_fields.append(field)

        if updated_fields:
            updated_fields.append("updated_at")
            interaction.save(update_fields=updated_fields)

        state["tool_result"] = {
            "status":         "updated",
            "interaction_id": interaction.pk,
            "changed_fields": {f: changes[f] for f in changes if f in ALLOWED_FIELDS},
        }
        state["error"] = ""

    except Exception as exc:
        logger.exception("Interaction update failed: %s", exc)
        state["tool_result"] = {"status": "db_error"}
        state["error"]       = f"DB update error: {exc}"

    state["tool_name"] = "edit_interaction_tool"
    return state


# ═════════════════════════════════════════════════════════════════════════════
#  TOOL 3 — suggest_followup_tool
# ═════════════════════════════════════════════════════════════════════════════

def suggest_followup_tool(state: AgentState) -> AgentState:
    """
    Fetch interaction data and generate 3 concrete follow-up suggestions.
    """
    from interactions.models import Interaction

    interaction_id = state.get("interaction_id")
    if not interaction_id:
        # Try to parse ID from user message
        import re
        match = re.search(r"\b(\d+)\b", state.get("user_message", ""))
        if match:
            interaction_id = int(match.group(1))

    if not interaction_id:
        state["tool_name"]   = "suggest_followup_tool"
        state["tool_result"] = {"status": "error", "suggestions": []}
        state["error"]       = "Please provide an interaction_id."
        return state

    try:
        interaction = Interaction.objects.select_related("hcp").get(pk=interaction_id)
    except Interaction.DoesNotExist:
        state["tool_name"]   = "suggest_followup_tool"
        state["tool_result"] = {"status": "not_found", "suggestions": []}
        state["error"]       = f"Interaction {interaction_id} not found."
        return state

    context = (
        f"HCP: {interaction.hcp.name} ({interaction.hcp.get_specialty_display()})\n"
        f"Type: {interaction.get_interaction_type_display()}\n"
        f"Date: {interaction.date}\n"
        f"Topics: {interaction.topics_discussed}\n"
        f"Outcomes: {interaction.outcomes}\n"
        f"Sentiment: {interaction.get_sentiment_display()}\n"
        f"Materials shared: {json.dumps(interaction.materials_shared)}\n"
        f"Samples distributed: {json.dumps(interaction.samples_distributed)}\n"
        f"Rep notes: {interaction.rep_notes}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a pharmaceutical Key Account Manager AI.
Based on the interaction details provided, suggest exactly 3 specific, actionable follow-up actions.
Each suggestion should be concise (1-2 sentences) and directly relevant to the interaction context.

Return ONLY a JSON array of 3 strings:
["suggestion 1", "suggestion 2", "suggestion 3"]

No markdown, no explanation, only valid JSON."""),
        ("human", "{context}"),
    ])

    try:
        chain    = prompt | _llm(temperature=0.4)
        response = chain.invoke({"context": context})
        raw      = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        suggestions: list = json.loads(raw)
        if not isinstance(suggestions, list):
            suggestions = [str(suggestions)]

    except (json.JSONDecodeError, Exception) as exc:
        logger.exception("suggest_followup_tool failed: %s", exc)
        suggestions = []
        state["error"] = f"Suggestion generation failed: {exc}"

    state["tool_name"]   = "suggest_followup_tool"
    state["tool_result"] = {
        "status":         "ok",
        "interaction_id": interaction_id,
        "hcp_name":       interaction.hcp.name,
        "suggestions":    suggestions,
    }
    return state


# ═════════════════════════════════════════════════════════════════════════════
#  TOOL 4 — search_hcp_tool
# ═════════════════════════════════════════════════════════════════════════════

def search_hcp_tool(state: AgentState) -> AgentState:
    """
    Case-insensitive HCP name search — returns matching records from PostgreSQL.
    """
    from interactions.models import HCP

    # Try explicit hcp_name field first, fallback to parsing message
    query = state.get("hcp_name") or state.get("user_message", "")

    # Strip common phrases so plain names work
    for phrase in [
        "search for", "find", "look up", "lookup", "show me",
        "get", "hcp", "doctor", "dr.", "dr ",
    ]:
        query = query.lower().replace(phrase, "").strip()

    if not query:
        state["tool_name"]   = "search_hcp_tool"
        state["tool_result"] = {"status": "error", "results": []}
        state["error"]       = "No search query provided."
        return state

    qs = HCP.objects.filter(name__icontains=query)

    results = []
    for hcp in qs:
        results.append({
            "id":           hcp.pk,
            "name":         hcp.name,
            "specialty":    hcp.specialty,
            "specialty_display": hcp.get_specialty_display(),
            "email":        hcp.email,
            "phone":        hcp.phone,
            "hospital":     hcp.hospital,
            "city":         hcp.city,
            "is_active":    hcp.is_active,
            "total_interactions": hcp.interactions.count(),
        })

    state["tool_name"]   = "search_hcp_tool"
    state["tool_result"] = {
        "status":  "ok",
        "query":   query,
        "count":   len(results),
        "results": results,
    }
    state["error"] = ""
    return state


# ═════════════════════════════════════════════════════════════════════════════
#  TOOL 5 — summarize_history_tool
# ═════════════════════════════════════════════════════════════════════════════

def summarize_history_tool(state: AgentState) -> AgentState:
    """
    Fetch all past interactions for an HCP and generate an LLM narrative summary.
    """
    from interactions.models import HCP, Interaction

    hcp_name = state.get("hcp_name") or ""
    if not hcp_name:
        # Extract name from user message
        words = state.get("user_message", "").split()
        hcp_name = " ".join(words[-3:]) if len(words) >= 3 else state.get("user_message", "")

    hcp_qs = HCP.objects.filter(name__icontains=hcp_name.strip())
    hcp    = hcp_qs.first()

    if not hcp:
        state["tool_name"]   = "summarize_history_tool"
        state["tool_result"] = {"status": "hcp_not_found", "summary": ""}
        state["error"]       = f"No HCP found matching '{hcp_name}'."
        return state

    interactions = Interaction.objects.filter(hcp=hcp).order_by("-date")[:25]

    if not interactions.exists():
        state["tool_name"]   = "summarize_history_tool"
        state["tool_result"] = {
            "status":  "no_interactions",
            "hcp_id":  hcp.pk,
            "hcp_name": hcp.name,
            "summary": "No interaction history found for this HCP.",
        }
        state["error"] = ""
        return state

    history_text = "\n\n".join(
        f"[{i.date}] {i.get_interaction_type_display()} | "
        f"Sentiment: {i.get_sentiment_display()}\n"
        f"Topics: {i.topics_discussed}\n"
        f"Outcomes: {i.outcomes}\n"
        f"Follow-ups: {', '.join(i.follow_up_actions) if i.follow_up_actions else 'None'}"
        for i in interactions
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a pharmaceutical KAM intelligence AI.

Analyse the interaction history with this HCP and write a brief strategic summary (max 150 words) covering:
1. Overall engagement trend and sentiment arc
2. Key clinical topics and products of interest
3. Recommended next-best action

Be factual, professional, and specific. No bullet points — write a single coherent paragraph."""),
        ("human", "HCP: {name} | Specialty: {specialty}\n\nInteraction History:\n{history}"),
    ])

    try:
        chain    = prompt | _llm(temperature=0.3)
        response = chain.invoke({
            "name":      hcp.name,
            "specialty": hcp.get_specialty_display(),
            "history":   history_text,
        })
        summary = response.content.strip()

    except Exception as exc:
        logger.exception("summarize_history_tool LLM call failed: %s", exc)
        summary     = ""
        state["error"] = f"Summary generation failed: {exc}"

    state["tool_name"]   = "summarize_history_tool"
    state["tool_result"] = {
        "status":             "ok",
        "hcp_id":             hcp.pk,
        "hcp_name":           hcp.name,
        "specialty":          hcp.get_specialty_display(),
        "total_interactions": interactions.count(),
        "summary":            summary,
    }
    return state


# ═════════════════════════════════════════════════════════════════════════════
#  NODE — Response Formatter
# ═════════════════════════════════════════════════════════════════════════════

def format_response_node(state: AgentState) -> AgentState:
    """
    Wraps tool_result into the standardised final_response envelope.
    Always returns structured JSON-serialisable dict.
    """
    state["final_response"] = {
        "tool":    state.get("tool_name", "unknown"),
        "intent":  state.get("intent",   "unknown"),
        "result":  state.get("tool_result", {}),
        "error":   state.get("error",    ""),
    }
    return state


# ═════════════════════════════════════════════════════════════════════════════
#  GRAPH CONSTRUCTION
# ═════════════════════════════════════════════════════════════════════════════

def build_agent_graph() -> Any:
    """Compile and return the LangGraph StateGraph."""

    graph = StateGraph(AgentState)

    # ── Nodes ─────────────────────────────────────────────────────────────
    graph.add_node("intent_classifier",    intent_node)
    graph.add_node("log_interaction",      log_interaction_tool)
    graph.add_node("edit_interaction",     edit_interaction_tool)
    graph.add_node("suggest_followup",     suggest_followup_tool)
    graph.add_node("search_hcp",           search_hcp_tool)
    graph.add_node("summarize_history",    summarize_history_tool)
    graph.add_node("format_response",      format_response_node)

    # ── Entry ──────────────────────────────────────────────────────────────
    graph.set_entry_point("intent_classifier")

    # ── Conditional routing from classifier → tool ─────────────────────────
    graph.add_conditional_edges(
        "intent_classifier",
        route_intent,
        {
            "log_interaction":   "log_interaction",
            "edit_interaction":  "edit_interaction",
            "suggest_followup":  "suggest_followup",
            "search_hcp":        "search_hcp",
            "summarize_history": "summarize_history",
        },
    )

    # ── All tools → formatter → END ────────────────────────────────────────
    for tool_node in [
        "log_interaction",
        "edit_interaction",
        "suggest_followup",
        "search_hcp",
        "summarize_history",
    ]:
        graph.add_edge(tool_node, "format_response")

    graph.add_edge("format_response", END)

    return graph.compile()


# ─── Module-level compiled graph (lazy singleton) ─────────────────────────────
_AGENT_GRAPH = None


def get_agent() -> Any:
    """Return a compiled (cached) agent graph."""
    global _AGENT_GRAPH
    if _AGENT_GRAPH is None:
        _AGENT_GRAPH = build_agent_graph()
    return _AGENT_GRAPH


# ─── Public run function ──────────────────────────────────────────────────────

def run_agent(
    user_message:   str,
    interaction_id: Optional[int] = None,
    hcp_name:       Optional[str] = None,
) -> dict:
    """
    Main entry point for the HCP CRM LangGraph agent.

    Args:
        user_message:   Natural language command from the user.
        interaction_id: Optional — required for edit/suggest_followup.
        hcp_name:       Optional — hint for search/summarize.

    Returns:
        dict: {
            "tool":   str,
            "intent": str,
            "result": dict,
            "error":  str,
        }
    """
    initial_state: AgentState = {
        "user_message":   user_message,
        "interaction_id": interaction_id,
        "hcp_name":       hcp_name,
        "intent":         "",
        "tool_name":      "",
        "tool_result":    {},
        "error":          "",
        "final_response": {},
    }

    try:
        agent       = get_agent()
        final_state = agent.invoke(initial_state)
        return final_state.get("final_response", {})

    except Exception as exc:
        logger.exception("Agent execution failed: %s", exc)
        return {
            "tool":   "unknown",
            "intent": "unknown",
            "result": {},
            "error":  f"Agent execution failed: {exc}",
        }
