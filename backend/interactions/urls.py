"""
URL Configuration — interactions app
Versioned under /api/v1/

Endpoints:
    /api/v1/hcps/                          — HCP CRUD
    /api/v1/interactions/                  — Interaction CRUD
    /api/v1/interactions/{id}/enrich/      — AI enrichment (old pipeline)
    /api/v1/hcps/{id}/summary/             — AI HCP summary (old pipeline)
    /api/v1/agent/                         — LangGraph agent (NL → tool)
    /api/v1/agent/detect-intent/           — Intent classifier only
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "interactions"

router = DefaultRouter()
router.register(r"hcps",         views.HCPViewSet,         basename="hcp")
router.register(r"interactions", views.InteractionViewSet, basename="interaction")

urlpatterns = [
    path("", include(router.urls)),

    # ── Legacy AI Pipeline Endpoints ───────────────────────────────────────
    path(
        "interactions/<int:pk>/enrich/",
        views.EnrichInteractionView.as_view(),
        name="enrich-interaction",
    ),
    path(
        "hcps/<int:pk>/summary/",
        views.HCPSummaryView.as_view(),
        name="hcp-summary",
    ),

    # ── LangGraph Agent Endpoints ──────────────────────────────────────────
    path(
        "agent/",
        views.AgentView.as_view(),
        name="agent",
    ),
    path(
        "agent/detect-intent/",
        views.DetectIntentView.as_view(),
        name="agent-detect-intent",
    ),
]
