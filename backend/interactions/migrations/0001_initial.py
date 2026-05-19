"""
Initial migration for the interactions app.
Generated manually — run `python manage.py migrate` to apply.
"""

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # ── HCP ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="HCP",
            fields=[
                ("id",       models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name",     models.CharField(db_index=True, max_length=255)),
                ("specialty",models.CharField(
                    choices=[
                        ("cardiology",       "Cardiology"),
                        ("oncology",         "Oncology"),
                        ("neurology",        "Neurology"),
                        ("endocrinology",    "Endocrinology"),
                        ("gastroenterology", "Gastroenterology"),
                        ("pulmonology",      "Pulmonology"),
                        ("nephrology",       "Nephrology"),
                        ("rheumatology",     "Rheumatology"),
                        ("psychiatry",       "Psychiatry"),
                        ("dermatology",      "Dermatology"),
                        ("general_practice", "General Practice"),
                        ("pediatrics",       "Pediatrics"),
                        ("surgery",          "Surgery"),
                        ("radiology",        "Radiology"),
                        ("pathology",        "Pathology"),
                        ("other",            "Other"),
                    ],
                    db_index=True, default="other", max_length=50,
                )),
                ("email",    models.EmailField(db_index=True, max_length=254, unique=True,
                    validators=[django.core.validators.EmailValidator()])),
                ("phone",    models.CharField(blank=True, max_length=20,
                    validators=[django.core.validators.RegexValidator(
                        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits.",
                        regex="^\\+?1?\\d{9,15}$",
                    )])),
                ("hospital", models.CharField(blank=True, max_length=255)),
                ("city",     models.CharField(blank=True, max_length=100)),
                ("state",    models.CharField(blank=True, max_length=100)),
                ("country",  models.CharField(blank=True, default="India", max_length=100)),
                ("is_active",models.BooleanField(default=True)),
                ("notes",    models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name":        "HCP",
                "verbose_name_plural": "HCPs",
                "ordering":            ["name"],
            },
        ),

        # ── Interaction ───────────────────────────────────────────────────
        migrations.CreateModel(
            name="Interaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hcp", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="interactions", to="interactions.hcp",
                )),
                ("interaction_type", models.CharField(
                    choices=[
                        ("in_person",  "In-Person Visit"),
                        ("virtual",    "Virtual Meeting"),
                        ("phone",      "Phone Call"),
                        ("email",      "Email"),
                        ("conference", "Conference / Event"),
                        ("webinar",    "Webinar"),
                        ("other",      "Other"),
                    ],
                    db_index=True, default="in_person", max_length=20,
                )),
                ("date",               models.DateField(db_index=True)),
                ("time",               models.TimeField(blank=True, null=True)),
                ("attendees",          models.JSONField(blank=True, default=list,
                    help_text="List of attendee names / roles (JSON array).")),
                ("topics_discussed",   models.TextField(blank=True,
                    help_text="Free-text or structured summary of topics covered.")),
                ("materials_shared",   models.JSONField(blank=True, default=list,
                    help_text="List of material names / IDs shared during the interaction.")),
                ("samples_distributed",models.JSONField(blank=True, default=list,
                    help_text="List of sample product names / quantities distributed.")),
                ("sentiment", models.CharField(
                    choices=[
                        ("very_positive", "Very Positive"),
                        ("positive",      "Positive"),
                        ("neutral",       "Neutral"),
                        ("negative",      "Negative"),
                        ("very_negative", "Very Negative"),
                        ("unknown",       "Unknown"),
                    ],
                    default="unknown", max_length=20,
                    help_text="AI-inferred or manually set sentiment of the interaction.",
                )),
                ("outcomes",          models.TextField(blank=True,
                    help_text="AI-summarised or manually entered interaction outcomes.")),
                ("follow_up_actions", models.JSONField(blank=True, default=list,
                    help_text="Structured list of follow-up tasks generated by AI or rep.")),
                ("rep_notes",         models.TextField(blank=True,
                    help_text="Raw notes entered by the sales rep (used as AI input).")),
                ("ai_processed",      models.BooleanField(default=False,
                    help_text="Whether AI has processed and enriched this interaction.")),
                ("created_at",        models.DateTimeField(auto_now_add=True)),
                ("updated_at",        models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name":        "Interaction",
                "verbose_name_plural": "Interactions",
                "ordering":            ["-date", "-created_at"],
            },
        ),

        # ── Indexes ───────────────────────────────────────────────────────
        migrations.AddIndex(
            model_name="hcp",
            index=models.Index(fields=["specialty", "is_active"], name="hcp_specialty_active_idx"),
        ),
        migrations.AddIndex(
            model_name="hcp",
            index=models.Index(fields=["name"], name="hcp_name_idx"),
        ),
        migrations.AddIndex(
            model_name="interaction",
            index=models.Index(fields=["hcp", "date"], name="interaction_hcp_date_idx"),
        ),
        migrations.AddIndex(
            model_name="interaction",
            index=models.Index(fields=["interaction_type"], name="interaction_type_idx"),
        ),
        migrations.AddIndex(
            model_name="interaction",
            index=models.Index(fields=["sentiment"], name="interaction_sentiment_idx"),
        ),
        migrations.AddIndex(
            model_name="interaction",
            index=models.Index(fields=["ai_processed"], name="interaction_ai_processed_idx"),
        ),
        migrations.AddIndex(
            model_name="interaction",
            index=models.Index(fields=["-created_at"], name="interaction_created_at_idx"),
        ),
    ]
