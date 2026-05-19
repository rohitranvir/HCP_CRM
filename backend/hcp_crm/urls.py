"""
Root URL Configuration — hcp_crm
AI-First CRM HCP Module

URL namespaces:
    /              → health-check
    /admin/        → Django admin
    /api/          → Simplified REST layer (Prompt 3)
    /api/v1/       → Full DRF router layer with agent endpoints
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def api_root(request):
    """Health-check / discovery endpoint."""
    return JsonResponse(
        {
            "service": "HCP CRM API",
            "version": "1.0.0",
            "status":  "running",
            "endpoints": {
                "chat":              "/api/chat/",
                "interactions":      "/api/interactions/",
                "hcp":               "/api/hcp/",
                "hcp_search":        "/api/hcp/search/?name=<query>",
                "agent_nl":          "/api/v1/agent/",
                "agent_intent":      "/api/v1/agent/detect-intent/",
                "hcps_full":         "/api/v1/hcps/",
                "interactions_full": "/api/v1/interactions/",
                "admin":             "/admin/",
            },
        }
    )


urlpatterns = [
    # ── Admin ──────────────────────────────────────────────────────────────
    path("admin/", admin.site.urls),

    # ── Health-check / root ────────────────────────────────────────────────
    path("", api_root, name="api-root"),

    # ── Simplified REST Layer  (/api/) ─────────────────────────────────────
    path("api/", include("interactions.api_urls")),

    # ── Full DRF + Agent Layer (/api/v1/) ──────────────────────────────────
    path("api/v1/", include("interactions.urls", namespace="interactions")),
]
