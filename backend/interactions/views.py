"""
Views — interactions app
AI-First CRM HCP Module

ViewSets:
    HCPViewSet          — CRUD for Healthcare Professionals
    InteractionViewSet  — CRUD for Interactions

AI Views:
    EnrichInteractionView — POST: run LangGraph pipeline to enrich an interaction
    HCPSummaryView        — GET:  generate AI engagement summary for an HCP
    AgentView             — POST: natural language → LangGraph agent router
    DetectIntentView      — POST: classify intent without invoking tool
"""

import logging
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import HCP, Interaction
from .serializers import (
    HCPSerializer,
    HCPListSerializer,
    InteractionSerializer,
    InteractionListSerializer,
)

logger = logging.getLogger(__name__)


# ─── HCP ViewSet ─────────────────────────────────────────────────────────────

class HCPViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Healthcare Professionals.

    list:       GET  /api/v1/hcps/
    create:     POST /api/v1/hcps/
    retrieve:   GET  /api/v1/hcps/{id}/
    update:     PUT  /api/v1/hcps/{id}/
    partial_update: PATCH /api/v1/hcps/{id}/
    destroy:    DELETE /api/v1/hcps/{id}/
    """

    queryset = HCP.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ["name", "email", "hospital", "city", "specialty"]
    ordering_fields = ["name", "specialty", "created_at"]
    ordering        = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return HCPListSerializer
        return HCPSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        specialty = self.request.query_params.get("specialty")
        is_active = self.request.query_params.get("is_active")
        if specialty:
            qs = qs.filter(specialty=specialty)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    @action(detail=True, methods=["get"], url_path="interactions")
    def interactions(self, request, pk=None):
        """GET /api/v1/hcps/{id}/interactions/ — all interactions for an HCP."""
        hcp = self.get_object()
        qs  = hcp.interactions.order_by("-date")
        serializer = InteractionListSerializer(qs, many=True)
        return Response(serializer.data)


# ─── Interaction ViewSet ──────────────────────────────────────────────────────

class InteractionViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for HCP Interactions.

    list:       GET  /api/v1/interactions/
    create:     POST /api/v1/interactions/
    retrieve:   GET  /api/v1/interactions/{id}/
    update:     PUT  /api/v1/interactions/{id}/
    partial_update: PATCH /api/v1/interactions/{id}/
    destroy:    DELETE /api/v1/interactions/{id}/
    """

    queryset = Interaction.objects.select_related("hcp").all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ["hcp__name", "topics_discussed", "outcomes"]
    ordering_fields = ["date", "created_at", "sentiment"]
    ordering        = ["-date"]

    def get_serializer_class(self):
        if self.action == "list":
            return InteractionListSerializer
        return InteractionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        hcp_id           = params.get("hcp")
        interaction_type = params.get("interaction_type")
        sentiment        = params.get("sentiment")
        ai_processed     = params.get("ai_processed")
        date_from        = params.get("date_from")
        date_to          = params.get("date_to")

        if hcp_id:
            qs = qs.filter(hcp_id=hcp_id)
        if interaction_type:
            qs = qs.filter(interaction_type=interaction_type)
        if sentiment:
            qs = qs.filter(sentiment=sentiment)
        if ai_processed is not None:
            qs = qs.filter(ai_processed=ai_processed.lower() == "true")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs


# ─── AI Enrichment View ───────────────────────────────────────────────────────

class EnrichInteractionView(APIView):
    """
    POST /api/v1/interactions/{id}/enrich/

    Triggers the LangGraph AI pipeline to enrich an interaction record:
      - Sentiment analysis
      - Outcome summarisation
      - Follow-up action extraction
    """

    def post(self, request, pk: int):
        interaction = get_object_or_404(Interaction, pk=pk)

        if not interaction.rep_notes:
            return Response(
                {"detail": "rep_notes is empty — nothing to enrich."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # ── Lazy import to avoid startup penalty ──────────────────────
            from .ai.pipeline import run_enrichment_pipeline  # noqa: F401
            result = run_enrichment_pipeline(interaction)

            interaction.sentiment        = result.get("sentiment",        interaction.sentiment)
            interaction.outcomes         = result.get("outcomes",         interaction.outcomes)
            interaction.follow_up_actions = result.get("follow_up_actions", interaction.follow_up_actions)
            interaction.ai_processed     = True
            interaction.save(update_fields=[
                "sentiment", "outcomes", "follow_up_actions", "ai_processed", "updated_at"
            ])

            serializer = InteractionSerializer(interaction)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ImportError:
            logger.warning("AI pipeline not yet implemented — returning stub.")
            return Response(
                {
                    "detail": "AI pipeline module not yet wired up.",
                    "interaction_id": pk,
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        except Exception as exc:
            logger.exception("AI enrichment failed for interaction %s: %s", pk, exc)
            return Response(
                {"detail": f"AI enrichment failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─── HCP AI Summary View ──────────────────────────────────────────────────────

class HCPSummaryView(APIView):
    """
    GET /api/v1/hcps/{id}/summary/

    Returns an AI-generated engagement summary across all interactions
    for the specified HCP (powered by LangChain + Groq).
    """

    def get(self, request, pk: int):
        hcp = get_object_or_404(HCP, pk=pk)
        interactions = hcp.interactions.order_by("-date")[:20]

        if not interactions.exists():
            return Response(
                {"detail": "No interactions found for this HCP."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            from .ai.pipeline import run_hcp_summary_pipeline  # noqa: F401
            summary = run_hcp_summary_pipeline(hcp, list(interactions))
            return Response({"hcp_id": pk, "hcp_name": hcp.name, "summary": summary})

        except ImportError:
            logger.warning("AI pipeline not yet implemented — returning stub.")
            return Response(
                {
                    "hcp_id":   pk,
                    "hcp_name": hcp.name,
                    "summary":  "AI pipeline not yet implemented.",
                    "total_interactions": interactions.count(),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("HCP summary failed for HCP %s: %s", pk, exc)
            return Response(
                {"detail": f"Summary generation failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─── Agent View ───────────────────────────────────────────────────────────────

class AgentView(APIView):
    """
    POST /api/v1/agent/

    Natural-language gateway to the LangGraph agent.
    The agent detects intent and routes to the appropriate tool automatically.

    Request body:
        {
            "message":        "<natural language command>",
            "interaction_id": <int|null>,   // optional — for edit/suggest_followup
            "hcp_name":       "<string>"    // optional — hint for search/summarize
        }

    Response:
        {
            "tool":       "<tool_name>",
            "tool_label": "<Human Readable Label>",
            "intent":     "<detected_intent>",
            "result":     { ... },
            "error":      "",
            "input":      { ... }
        }
    """

    def post(self, request):
        message        = request.data.get("message", "").strip()
        interaction_id = request.data.get("interaction_id")  # int or None
        hcp_name       = request.data.get("hcp_name", "").strip() or None

        if not message:
            return Response(
                {"detail": "'message' field is required and cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Coerce interaction_id to int if provided
        if interaction_id is not None:
            try:
                interaction_id = int(interaction_id)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "'interaction_id' must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            from .agent_router import route
            result = route(
                user_message=message,
                interaction_id=interaction_id,
                hcp_name=hcp_name,
            )
            http_status = (
                status.HTTP_500_INTERNAL_SERVER_ERROR
                if result.get("error") and not result.get("result")
                else status.HTTP_200_OK
            )
            return Response(result, status=http_status)

        except Exception as exc:
            logger.exception("AgentView: unexpected error: %s", exc)
            return Response(
                {"detail": f"Agent error: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─── Intent-only Detection View ───────────────────────────────────────────────

class DetectIntentView(APIView):
    """
    POST /api/v1/agent/detect-intent/

    Classify a message's intent without invoking any tool.
    Useful for frontend pre-loading (e.g. showing a form before submission).

    Request body:  { "message": "<string>" }
    Response:      { "intent": "<key>", "tool_label": "<Human label>" }
    """

    def post(self, request):
        message = request.data.get("message", "").strip()
        if not message:
            return Response(
                {"detail": "'message' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from .agent_router import AgentRouter
            router = AgentRouter()
            return Response(router.detect(message), status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception("DetectIntentView error: %s", exc)
            return Response(
                {"detail": f"Intent detection failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ═════════════════════════════════════════════════════════════════════════════
#  /api/  — Simplified REST Layer (Prompt 3)
# ═════════════════════════════════════════════════════════════════════════════

# ─── Chat View ────────────────────────────────────────────────────────────────

class ChatView(APIView):
    """
    POST /api/chat/

    Natural-language gateway to the LangGraph agent.
    Simplified response shape for frontend consumption.

    Request body:
        {
            "message":        "<natural language command>",
            "interaction_id": <int>   // optional
        }

    Response:
        {
            "tool_used": "<tool_name>",
            "result":    { ...tool output... },
            "message":   "<human readable summary>"
        }
    """

    def post(self, request):
        message        = (request.data.get("message") or "").strip()
        interaction_id = request.data.get("interaction_id")

        if not message:
            return Response(
                {"detail": "'message' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if interaction_id is not None:
            try:
                interaction_id = int(interaction_id)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "'interaction_id' must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            from .agent_router import route
            agent_result = route(
                user_message=message,
                interaction_id=interaction_id,
            )

            # ── Build human-readable summary message ──────────────────────
            tool  = agent_result.get("tool", "unknown")
            error = agent_result.get("error", "")
            result = agent_result.get("result", {})

            if error and not result:
                summary = f"❌ {error}"
            elif tool == "log_interaction_tool":
                iid  = result.get("interaction_id", "?")
                hcp  = result.get("hcp_name", "unknown HCP")
                summary = (
                    f"✅ Interaction #{iid} logged for {hcp}."
                    if result.get("status") == "created"
                    else f"⚠️ {result.get('message', 'Could not log interaction.')}"
                )
            elif tool == "edit_interaction_tool":
                fields = list(result.get("changed_fields", {}).keys())
                summary = (
                    f"✅ Updated fields: {', '.join(fields)}."
                    if result.get("status") == "updated"
                    else f"⚠️ {error or 'Update failed.'}"
                )
            elif tool == "suggest_followup_tool":
                n = len(result.get("suggestions", []))
                summary = f"💡 Generated {n} follow-up suggestions."
            elif tool == "search_hcp_tool":
                n = result.get("count", 0)
                summary = f"🔍 Found {n} HCP record(s) matching your query."
            elif tool == "summarize_history_tool":
                hcp = result.get("hcp_name", "")
                summary = f"📋 Engagement summary generated for {hcp}."
            else:
                summary = "✅ Request processed successfully."

            return Response(
                {
                    "tool_used": tool,
                    "result":    result,
                    "message":   summary,
                    "error":     error,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.exception("ChatView error: %s", exc)
            return Response(
                {"detail": f"Agent error: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─── Followup View ────────────────────────────────────────────────────────────

class FollowupView(APIView):
    """
    POST /api/interactions/<id>/followup/

    Triggers suggest_followup_tool for the given interaction.
    Convenience shortcut — no natural language required.

    Response:
        {
            "tool_used":      "suggest_followup_tool",
            "result":         { "suggestions": [...] },
            "message":        "💡 Generated 3 follow-up suggestions."
        }
    """

    def post(self, request, pk: int):
        interaction = get_object_or_404(Interaction, pk=pk)

        try:
            from .agent_router import route
            agent_result = route(
                user_message=f"Suggest follow-up actions for interaction {pk}",
                interaction_id=pk,
            )

            result      = agent_result.get("result", {})
            error       = agent_result.get("error", "")
            suggestions = result.get("suggestions", [])
            n           = len(suggestions)

            if error and not suggestions:
                return Response(
                    {"detail": error},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "tool_used":       "suggest_followup_tool",
                    "interaction_id":  pk,
                    "hcp_name":        interaction.hcp.name,
                    "result":          result,
                    "message":         f"💡 Generated {n} follow-up suggestion{'s' if n != 1 else ''}.",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.exception("FollowupView error for interaction %s: %s", pk, exc)
            return Response(
                {"detail": f"Follow-up generation failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─── HCP Search View ──────────────────────────────────────────────────────────

class HCPSearchView(APIView):
    """
    GET /api/hcp/search/?name=<query>

    Search HCPs by name (case-insensitive, partial match).
    Returns a flat list — lightweight for autocomplete / typeahead.

    Response:
        [
            { "id": 1, "name": "Dr. Patel", "specialty": "cardiology",
              "email": "...", "hospital": "...", "city": "..." },
            ...
        ]
    """

    def get(self, request):
        query = (request.query_params.get("name") or "").strip()

        if not query:
            return Response(
                {"detail": "Query parameter 'name' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = HCP.objects.filter(name__icontains=query, is_active=True).order_by("name")

        results = [
            {
                "id":           hcp.pk,
                "name":         hcp.name,
                "specialty":    hcp.specialty,
                "specialty_display": hcp.get_specialty_display(),
                "email":        hcp.email,
                "phone":        hcp.phone,
                "hospital":     hcp.hospital,
                "city":         hcp.city,
                "total_interactions": hcp.interactions.count(),
            }
            for hcp in qs
        ]

        return Response(
            {
                "query":   query,
                "count":   len(results),
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
