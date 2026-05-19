"""
Django Admin — interactions app
"""

from django.contrib import admin
from .models import HCP, Interaction


@admin.register(HCP)
class HCPAdmin(admin.ModelAdmin):
    list_display   = ["name", "specialty", "email", "phone", "hospital", "city", "is_active"]
    list_filter    = ["specialty", "is_active", "country"]
    search_fields  = ["name", "email", "hospital"]
    ordering       = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Identity", {
            "fields": ("name", "specialty", "email", "phone"),
        }),
        ("Organisation", {
            "fields": ("hospital", "city", "state", "country"),
        }),
        ("Status & Notes", {
            "fields": ("is_active", "notes"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display    = [
        "hcp", "interaction_type", "date", "sentiment", "ai_processed", "created_at"
    ]
    list_filter     = ["interaction_type", "sentiment", "ai_processed", "date"]
    search_fields   = ["hcp__name", "topics_discussed", "outcomes"]
    ordering        = ["-date"]
    readonly_fields = ["created_at", "updated_at", "ai_processed"]
    raw_id_fields   = ["hcp"]

    fieldsets = (
        ("Core", {
            "fields": ("hcp", "interaction_type", "date", "time"),
        }),
        ("Participants & Content", {
            "fields": ("attendees", "topics_discussed", "materials_shared", "samples_distributed"),
        }),
        ("AI-Enriched", {
            "fields": ("rep_notes", "sentiment", "outcomes", "follow_up_actions", "ai_processed"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
