"""
Serializers — interactions app
AI-First CRM HCP Module

Provides DRF serializers for:
    HCPSerializer          — Full HCP read/write
    HCPListSerializer      — Lightweight HCP list view
    InteractionSerializer  — Full Interaction read/write with nested HCP
    InteractionListSerializer — Compact list view
"""

from rest_framework import serializers
from .models import HCP, Interaction, InteractionType, SentimentScore, Specialty


# ─── HCP Serializers ──────────────────────────────────────────────────────────

class HCPListSerializer(serializers.ModelSerializer):
    """Compact serializer for list endpoints — avoids over-fetching."""

    specialty_display = serializers.CharField(
        source="get_specialty_display", read_only=True
    )
    total_interactions = serializers.SerializerMethodField()

    class Meta:
        model  = HCP
        fields = [
            "id",
            "name",
            "specialty",
            "specialty_display",
            "email",
            "phone",
            "hospital",
            "city",
            "is_active",
            "total_interactions",
        ]
        read_only_fields = ["id", "total_interactions"]

    def get_total_interactions(self, obj: HCP) -> int:
        return obj.interactions.count()


class HCPSerializer(serializers.ModelSerializer):
    """Full HCP serializer — used for create, retrieve, update."""

    specialty_display = serializers.CharField(
        source="get_specialty_display", read_only=True
    )
    total_interactions = serializers.SerializerMethodField()

    # Expose choice options for front-end dropdowns
    specialty_choices = serializers.SerializerMethodField()

    class Meta:
        model  = HCP
        fields = [
            "id",
            "name",
            "specialty",
            "specialty_display",
            "specialty_choices",
            "email",
            "phone",
            "hospital",
            "city",
            "state",
            "country",
            "is_active",
            "notes",
            "total_interactions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "total_interactions"]

    def get_total_interactions(self, obj: HCP) -> int:
        return obj.interactions.count()

    def get_specialty_choices(self, obj: HCP) -> list[dict]:
        return [{"value": v, "label": l} for v, l in Specialty.choices]

    def validate_email(self, value: str) -> str:
        """Ensure email uniqueness on update (exclude current instance)."""
        qs = HCP.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An HCP with this email already exists.")
        return value.lower()

    def validate_phone(self, value: str) -> str:
        if value and not value.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise serializers.ValidationError("Phone must contain only digits, +, -, or spaces.")
        return value


# ─── Interaction Serializers ──────────────────────────────────────────────────

class InteractionListSerializer(serializers.ModelSerializer):
    """Compact serializer for paginated interaction lists."""

    hcp_name              = serializers.CharField(source="hcp.name",         read_only=True)
    hcp_specialty         = serializers.CharField(source="hcp.specialty",     read_only=True)
    interaction_type_display = serializers.CharField(
        source="get_interaction_type_display", read_only=True
    )
    sentiment_display     = serializers.CharField(
        source="get_sentiment_display", read_only=True
    )

    class Meta:
        model  = Interaction
        fields = [
            "id",
            "hcp",
            "hcp_name",
            "hcp_specialty",
            "interaction_type",
            "interaction_type_display",
            "date",
            "time",
            "sentiment",
            "sentiment_display",
            "ai_processed",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class InteractionSerializer(serializers.ModelSerializer):
    """
    Full Interaction serializer.
    - Accepts hcp (FK id) on write.
    - Returns nested HCP detail on read via hcp_detail.
    """

    # Read-only nested HCP object
    hcp_detail = HCPListSerializer(source="hcp", read_only=True)

    # Human-readable display fields
    interaction_type_display = serializers.CharField(
        source="get_interaction_type_display", read_only=True
    )
    sentiment_display = serializers.CharField(
        source="get_sentiment_display", read_only=True
    )

    # Expose choice options for front-end dropdowns
    interaction_type_choices = serializers.SerializerMethodField()
    sentiment_choices        = serializers.SerializerMethodField()

    class Meta:
        model  = Interaction
        fields = [
            # ── Identity ──────────────────────────────────────────────
            "id",

            # ── Relationships ─────────────────────────────────────────
            "hcp",          # write: FK id
            "hcp_detail",   # read:  nested object

            # ── Call Metadata ─────────────────────────────────────────
            "interaction_type",
            "interaction_type_display",
            "interaction_type_choices",
            "date",
            "time",

            # ── Participants ──────────────────────────────────────────
            "attendees",

            # ── Engagement Content ────────────────────────────────────
            "topics_discussed",
            "materials_shared",
            "samples_distributed",

            # ── AI-Enriched Fields ────────────────────────────────────
            "sentiment",
            "sentiment_display",
            "sentiment_choices",
            "outcomes",
            "follow_up_actions",

            # ── Rep Input ─────────────────────────────────────────────
            "rep_notes",

            # ── System ────────────────────────────────────────────────
            "ai_processed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "hcp_detail",
            "interaction_type_display",
            "sentiment_display",
            "created_at",
            "updated_at",
        ]

    def get_interaction_type_choices(self, obj: Interaction) -> list[dict]:
        return [{"value": v, "label": l} for v, l in InteractionType.choices]

    def get_sentiment_choices(self, obj: Interaction) -> list[dict]:
        return [{"value": v, "label": l} for v, l in SentimentScore.choices]

    # ── Validation ────────────────────────────────────────────────────────

    def validate_attendees(self, value) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("Attendees must be a JSON array.")
        return value

    def validate_materials_shared(self, value) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("materials_shared must be a JSON array.")
        return value

    def validate_samples_distributed(self, value) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("samples_distributed must be a JSON array.")
        return value

    def validate_follow_up_actions(self, value) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("follow_up_actions must be a JSON array.")
        return value

    def validate(self, attrs: dict) -> dict:
        """Cross-field validation."""
        date = attrs.get("date")
        time = attrs.get("time")
        if time and not date:
            raise serializers.ValidationError(
                {"time": "A date must be provided when time is specified."}
            )
        return attrs
