"""
interactions/api_urls.py
Simplified /api/ URL layer — Prompt 3

Routes:
    POST   /api/chat/                        → ChatView
    GET    /api/interactions/                → InteractionListAPIView
    GET    /api/interactions/<id>/           → InteractionDetailAPIView
    GET    /api/hcp/                         → HCPListAPIView
    GET    /api/hcp/search/?name=<q>         → HCPSearchView
    POST   /api/interactions/<id>/followup/  → FollowupView
"""

from django.urls import path
from . import views

# ── Thin read-only views (reuse serializers, no DRF router) ──────────────────

from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import HCP, Interaction
from .serializers import HCPListSerializer, InteractionSerializer, InteractionListSerializer


class InteractionListAPIView(ListAPIView):
    """GET /api/interactions/ — paginated list of all interactions."""
    queryset         = Interaction.objects.select_related("hcp").order_by("-date")
    serializer_class = InteractionListSerializer


class InteractionDetailAPIView(RetrieveAPIView):
    """GET /api/interactions/<id>/ — single interaction detail."""
    queryset         = Interaction.objects.select_related("hcp").all()
    serializer_class = InteractionSerializer


class HCPListAPIView(ListAPIView):
    """GET /api/hcp/ — paginated list of all active HCPs."""
    queryset         = HCP.objects.filter(is_active=True).order_by("name")
    serializer_class = HCPListSerializer


# ── URL patterns ─────────────────────────────────────────────────────────────

urlpatterns = [
    # ── Chat (NL agent gateway) ───────────────────────────────────────────
    path(
        "chat/",
        views.ChatView.as_view(),
        name="api-chat",
    ),

    # ── Interactions ──────────────────────────────────────────────────────
    path(
        "interactions/",
        InteractionListAPIView.as_view(),
        name="api-interaction-list",
    ),
    path(
        "interactions/<int:pk>/",
        InteractionDetailAPIView.as_view(),
        name="api-interaction-detail",
    ),
    path(
        "interactions/<int:pk>/followup/",
        views.FollowupView.as_view(),
        name="api-interaction-followup",
    ),

    # ── HCP ───────────────────────────────────────────────────────────────
    path(
        "hcp/",
        HCPListAPIView.as_view(),
        name="api-hcp-list",
    ),
    path(
        "hcp/search/",
        views.HCPSearchView.as_view(),
        name="api-hcp-search",
    ),
]
