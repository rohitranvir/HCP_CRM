"""
Data Models — interactions app
AI-First CRM HCP Module

Models:
    HCP         — Healthcare Professional master record
    Interaction — Logged HCP interaction with full AI-enrichable metadata
"""

from django.db import models
from django.core.validators import EmailValidator, RegexValidator


# ─── Choices ─────────────────────────────────────────────────────────────────

class InteractionType(models.TextChoices):
    IN_PERSON      = "in_person",      "In-Person Visit"
    VIRTUAL        = "virtual",        "Virtual Meeting"
    PHONE          = "phone",          "Phone Call"
    EMAIL          = "email",          "Email"
    CONFERENCE     = "conference",     "Conference / Event"
    WEBINAR        = "webinar",        "Webinar"
    OTHER          = "other",          "Other"


class SentimentScore(models.TextChoices):
    VERY_POSITIVE  = "very_positive",  "Very Positive"
    POSITIVE       = "positive",       "Positive"
    NEUTRAL        = "neutral",        "Neutral"
    NEGATIVE       = "negative",       "Negative"
    VERY_NEGATIVE  = "very_negative",  "Very Negative"
    UNKNOWN        = "unknown",        "Unknown"


class Specialty(models.TextChoices):
    CARDIOLOGY         = "cardiology",         "Cardiology"
    ONCOLOGY           = "oncology",           "Oncology"
    NEUROLOGY          = "neurology",          "Neurology"
    ENDOCRINOLOGY      = "endocrinology",      "Endocrinology"
    GASTROENTEROLOGY   = "gastroenterology",   "Gastroenterology"
    PULMONOLOGY        = "pulmonology",        "Pulmonology"
    NEPHROLOGY         = "nephrology",         "Nephrology"
    RHEUMATOLOGY       = "rheumatology",       "Rheumatology"
    PSYCHIATRY         = "psychiatry",         "Psychiatry"
    DERMATOLOGY        = "dermatology",        "Dermatology"
    GENERAL_PRACTICE   = "general_practice",   "General Practice"
    PEDIATRICS         = "pediatrics",         "Pediatrics"
    SURGERY            = "surgery",            "Surgery"
    RADIOLOGY          = "radiology",          "Radiology"
    PATHOLOGY          = "pathology",          "Pathology"
    OTHER              = "other",              "Other"


# ─── HCP Model ───────────────────────────────────────────────────────────────

class HCP(models.Model):
    """
    Healthcare Professional (HCP) — master record.

    Represents a doctor, nurse-practitioner, or other clinician
    that the commercial team tracks and engages.
    """

    phone_validator = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits.",
    )

    # ── Identity ──────────────────────────────────────────────────────────
    name          = models.CharField(max_length=255, db_index=True)
    specialty     = models.CharField(
        max_length=50,
        choices=Specialty.choices,
        default=Specialty.OTHER,
        db_index=True,
    )
    email         = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        db_index=True,
    )
    phone         = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator],
    )

    # ── Organisation ──────────────────────────────────────────────────────
    hospital      = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    state         = models.CharField(max_length=100, blank=True)
    country       = models.CharField(max_length=100, blank=True, default="India")

    # ── Meta ──────────────────────────────────────────────────────────────
    is_active     = models.BooleanField(default=True)
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "HCP"
        verbose_name_plural = "HCPs"
        ordering            = ["name"]
        indexes             = [
            models.Index(fields=["specialty", "is_active"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.get_specialty_display()}"


# ─── Interaction Model ────────────────────────────────────────────────────────

class Interaction(models.Model):
    """
    A single logged engagement between a commercial rep and an HCP.

    Stores structured call-reporting data plus AI-generated enrichment
    fields (sentiment, outcomes, follow_up_actions).
    """

    # ── Relationship ──────────────────────────────────────────────────────
    hcp               = models.ForeignKey(
        HCP,
        on_delete=models.CASCADE,
        related_name="interactions",
        db_index=True,
    )

    # ── Call Metadata ─────────────────────────────────────────────────────
    interaction_type  = models.CharField(
        max_length=20,
        choices=InteractionType.choices,
        default=InteractionType.IN_PERSON,
        db_index=True,
    )
    date              = models.DateField(db_index=True)
    time              = models.TimeField(blank=True, null=True)

    # ── Participants ──────────────────────────────────────────────────────
    attendees         = models.JSONField(
        default=list,
        blank=True,
        help_text="List of attendee names / roles (JSON array).",
    )

    # ── Engagement Content ────────────────────────────────────────────────
    topics_discussed  = models.TextField(
        blank=True,
        help_text="Free-text or structured summary of topics covered.",
    )
    materials_shared  = models.JSONField(
        default=list,
        blank=True,
        help_text="List of material names / IDs shared during the interaction.",
    )
    samples_distributed = models.JSONField(
        default=list,
        blank=True,
        help_text="List of sample product names / quantities distributed.",
    )

    # ── AI-Enriched Fields ────────────────────────────────────────────────
    sentiment         = models.CharField(
        max_length=20,
        choices=SentimentScore.choices,
        default=SentimentScore.UNKNOWN,
        help_text="AI-inferred or manually set sentiment of the interaction.",
    )
    outcomes          = models.TextField(
        blank=True,
        help_text="AI-summarised or manually entered interaction outcomes.",
    )
    follow_up_actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Structured list of follow-up tasks generated by AI or rep.",
    )

    # ── System Fields ─────────────────────────────────────────────────────
    rep_notes         = models.TextField(
        blank=True,
        help_text="Raw notes entered by the sales rep (used as AI input).",
    )
    ai_processed      = models.BooleanField(
        default=False,
        help_text="Whether AI has processed and enriched this interaction.",
    )
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Interaction"
        verbose_name_plural = "Interactions"
        ordering            = ["-date", "-created_at"]
        indexes             = [
            models.Index(fields=["hcp", "date"]),
            models.Index(fields=["interaction_type"]),
            models.Index(fields=["sentiment"]),
            models.Index(fields=["ai_processed"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.get_interaction_type_display()}] "
            f"{self.hcp.name} on {self.date}"
        )
