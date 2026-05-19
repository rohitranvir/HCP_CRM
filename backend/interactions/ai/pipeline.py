"""
AI Pipeline — interactions/ai/pipeline.py
AI-First CRM HCP Module

LangGraph + LangChain-Groq powered enrichment pipeline.

Pipelines:
    run_enrichment_pipeline  — Enriches a single Interaction record
    run_hcp_summary_pipeline — Generates a narrative summary for an HCP
"""

import os
import logging
from typing import TypedDict

from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# ─── Groq LLM ────────────────────────────────────────────────────────────────

def _get_llm(model: str = "llama3-8b-8192") -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set in environment variables.")
    return ChatGroq(model=model, api_key=api_key, temperature=0.2)


# ─── State Schema ─────────────────────────────────────────────────────────────

class EnrichmentState(TypedDict):
    rep_notes:        str
    hcp_name:         str
    specialty:        str
    interaction_type: str
    sentiment:        str
    outcomes:         str
    follow_up_actions: list[str]
    error:            str


# ─── Node: Sentiment Analysis ─────────────────────────────────────────────────

def sentiment_node(state: EnrichmentState) -> EnrichmentState:
    """Classify the emotional tone of the rep's notes."""
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a pharmaceutical sales analytics AI. "
            "Classify the sentiment of a medical rep's call notes into exactly one of: "
            "very_positive, positive, neutral, negative, very_negative. "
            "Respond with ONLY the label — no explanation."
        )),
        ("human", "Call notes:\n{notes}"),
    ])
    chain    = prompt | llm
    response = chain.invoke({"notes": state["rep_notes"]})
    sentiment = response.content.strip().lower()

    valid = {"very_positive", "positive", "neutral", "negative", "very_negative"}
    state["sentiment"] = sentiment if sentiment in valid else "neutral"
    return state


# ─── Node: Outcome Summarisation ──────────────────────────────────────────────

def outcomes_node(state: EnrichmentState) -> EnrichmentState:
    """Summarise key outcomes from the interaction."""
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert at summarising pharmaceutical sales interactions. "
            "Given the rep's notes about a visit with a {specialty} specialist, "
            "write a concise 2-3 sentence outcome summary in professional language."
        )),
        ("human", "Rep notes:\n{notes}"),
    ])
    chain    = prompt | llm
    response = chain.invoke({
        "specialty": state.get("specialty", ""),
        "notes":     state["rep_notes"],
    })
    state["outcomes"] = response.content.strip()
    return state


# ─── Node: Follow-up Extraction ───────────────────────────────────────────────

def followup_node(state: EnrichmentState) -> EnrichmentState:
    """Extract structured follow-up action items."""
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a CRM assistant for a pharmaceutical company. "
            "Extract all follow-up action items from the rep's notes. "
            "Return ONLY a Python-style list of short action strings. "
            "Example: [\"Send product brochure\", \"Schedule follow-up in 2 weeks\"]"
        )),
        ("human", "Rep notes:\n{notes}"),
    ])
    chain    = prompt | llm
    response = chain.invoke({"notes": state["rep_notes"]})

    import ast
    try:
        actions = ast.literal_eval(response.content.strip())
        if isinstance(actions, list):
            state["follow_up_actions"] = [str(a) for a in actions]
        else:
            state["follow_up_actions"] = [response.content.strip()]
    except (ValueError, SyntaxError):
        state["follow_up_actions"] = [response.content.strip()]

    return state


# ─── Build Enrichment Graph ───────────────────────────────────────────────────

def _build_enrichment_graph() -> StateGraph:
    graph = StateGraph(EnrichmentState)
    graph.add_node("sentiment", sentiment_node)
    graph.add_node("outcomes",  outcomes_node)
    graph.add_node("followup",  followup_node)

    graph.set_entry_point("sentiment")
    graph.add_edge("sentiment", "outcomes")
    graph.add_edge("outcomes",  "followup")
    graph.add_edge("followup",  END)

    return graph.compile()


# ─── Public API ───────────────────────────────────────────────────────────────

def run_enrichment_pipeline(interaction) -> dict:
    """
    Run the LangGraph enrichment pipeline for a single Interaction instance.

    Args:
        interaction: interactions.models.Interaction instance

    Returns:
        dict with keys: sentiment, outcomes, follow_up_actions
    """
    logger.info("Starting AI enrichment for interaction %s", interaction.pk)

    initial_state: EnrichmentState = {
        "rep_notes":        interaction.rep_notes,
        "hcp_name":         interaction.hcp.name,
        "specialty":        interaction.hcp.get_specialty_display(),
        "interaction_type": interaction.get_interaction_type_display(),
        "sentiment":        "unknown",
        "outcomes":         "",
        "follow_up_actions": [],
        "error":            "",
    }

    pipeline     = _build_enrichment_graph()
    final_state  = pipeline.invoke(initial_state)

    logger.info(
        "Enrichment complete for interaction %s — sentiment: %s",
        interaction.pk, final_state["sentiment"]
    )

    return {
        "sentiment":        final_state["sentiment"],
        "outcomes":         final_state["outcomes"],
        "follow_up_actions": final_state["follow_up_actions"],
    }


def run_hcp_summary_pipeline(hcp, interactions: list) -> str:
    """
    Generate a narrative engagement summary for an HCP across recent interactions.

    Args:
        hcp:          interactions.models.HCP instance
        interactions: list of recent Interaction instances

    Returns:
        str: AI-generated engagement summary
    """
    llm = _get_llm()

    interaction_text = "\n\n".join(
        f"[{i.date}] ({i.get_interaction_type_display()}) "
        f"Sentiment: {i.get_sentiment_display()}\n"
        f"Topics: {i.topics_discussed}\n"
        f"Outcomes: {i.outcomes}"
        for i in interactions
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a pharmaceutical Key Account Management AI. "
            "Analyse the interaction history with the following HCP and provide "
            "a concise strategic engagement summary covering: "
            "1) Overall sentiment trend, 2) Key topics of interest, "
            "3) Recommended next engagement strategy. "
            "Keep the summary under 200 words."
        )),
        ("human", (
            "HCP: {name} | Specialty: {specialty}\n\n"
            "Recent Interactions:\n{interactions}"
        )),
    ])

    chain    = prompt | llm
    response = chain.invoke({
        "name":         hcp.name,
        "specialty":    hcp.get_specialty_display(),
        "interactions": interaction_text,
    })

    return response.content.strip()
