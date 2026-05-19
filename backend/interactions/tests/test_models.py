"""
interactions/tests/test_models.py
Unit tests for HCP and Interaction models.

Run with:
    python manage.py test interactions.tests.test_models
"""

from datetime import date, time
from django.test import TestCase
from django.core.exceptions import ValidationError
from interactions.models import HCP, Interaction, InteractionType, SentimentScore, Specialty


class HCPModelTests(TestCase):

    def _make_hcp(self, **kwargs) -> HCP:
        defaults = dict(
            name="Dr. Priya Sharma",
            specialty=Specialty.CARDIOLOGY,
            email="priya.sharma@hospital.in",
            phone="+919876543210",
            hospital="Apollo Hospital",
            city="Mumbai",
        )
        defaults.update(kwargs)
        return HCP.objects.create(**defaults)

    # ── Creation ──────────────────────────────────────────────────────────

    def test_create_hcp_minimal(self):
        hcp = HCP.objects.create(
            name="Dr. Raj",
            specialty=Specialty.NEUROLOGY,
            email="raj@clinic.in",
        )
        self.assertIsNotNone(hcp.pk)
        self.assertTrue(hcp.is_active)

    def test_create_hcp_full(self):
        hcp = self._make_hcp()
        self.assertEqual(hcp.name, "Dr. Priya Sharma")
        self.assertEqual(hcp.specialty, Specialty.CARDIOLOGY)
        self.assertEqual(hcp.country, "India")

    # ── __str__ ───────────────────────────────────────────────────────────

    def test_str_representation(self):
        hcp = self._make_hcp()
        self.assertIn("Dr. Priya Sharma", str(hcp))
        self.assertIn("Cardiology", str(hcp))

    # ── Uniqueness ────────────────────────────────────────────────────────

    def test_duplicate_email_raises_error(self):
        self._make_hcp()
        with self.assertRaises(Exception):
            HCP.objects.create(
                name="Another Doctor",
                specialty=Specialty.ONCOLOGY,
                email="priya.sharma@hospital.in",  # duplicate
            )

    # ── Specialty choices ─────────────────────────────────────────────────

    def test_specialty_display(self):
        hcp = self._make_hcp(specialty=Specialty.CARDIOLOGY)
        self.assertEqual(hcp.get_specialty_display(), "Cardiology")

    # ── Timestamps ────────────────────────────────────────────────────────

    def test_timestamps_auto_set(self):
        hcp = self._make_hcp()
        self.assertIsNotNone(hcp.created_at)
        self.assertIsNotNone(hcp.updated_at)

    # ── Ordering ──────────────────────────────────────────────────────────

    def test_default_ordering_by_name(self):
        HCP.objects.create(name="Zeena", specialty=Specialty.OTHER, email="z@test.com")
        HCP.objects.create(name="Arun",  specialty=Specialty.OTHER, email="a@test.com")
        names = list(HCP.objects.values_list("name", flat=True))
        self.assertEqual(names, sorted(names))


class InteractionModelTests(TestCase):

    def setUp(self):
        self.hcp = HCP.objects.create(
            name="Dr. Amit Kapoor",
            specialty=Specialty.ONCOLOGY,
            email="amit.kapoor@oncologyindia.in",
        )

    def _make_interaction(self, **kwargs) -> Interaction:
        defaults = dict(
            hcp=self.hcp,
            interaction_type=InteractionType.IN_PERSON,
            date=date(2025, 6, 15),
            time=time(10, 30, 0),
            attendees=["Rep A", "Rep B"],
            topics_discussed="Discussed Keytruda efficacy data",
            materials_shared=["Keytruda brochure", "Clinical trial PDF"],
            samples_distributed=["Keytruda 50mg sample"],
            sentiment=SentimentScore.POSITIVE,
            outcomes="HCP showed strong interest in prescribing for NSCLC.",
            follow_up_actions=["Send full trial data", "Schedule demo next month"],
        )
        defaults.update(kwargs)
        return Interaction.objects.create(**defaults)

    # ── Creation ──────────────────────────────────────────────────────────

    def test_create_interaction_minimal(self):
        interaction = Interaction.objects.create(
            hcp=self.hcp,
            interaction_type=InteractionType.PHONE,
            date=date.today(),
        )
        self.assertIsNotNone(interaction.pk)
        self.assertFalse(interaction.ai_processed)

    def test_create_interaction_full(self):
        interaction = self._make_interaction()
        self.assertEqual(interaction.hcp, self.hcp)
        self.assertEqual(interaction.sentiment, SentimentScore.POSITIVE)
        self.assertIsInstance(interaction.attendees, list)
        self.assertIsInstance(interaction.materials_shared, list)
        self.assertIsInstance(interaction.follow_up_actions, list)

    # ── __str__ ───────────────────────────────────────────────────────────

    def test_str_representation(self):
        interaction = self._make_interaction()
        s = str(interaction)
        self.assertIn("Dr. Amit Kapoor", s)
        self.assertIn("2025-06-15", s)

    # ── FK relationship ───────────────────────────────────────────────────

    def test_hcp_reverse_relation(self):
        self._make_interaction()
        self._make_interaction(date=date(2025, 7, 1))
        self.assertEqual(self.hcp.interactions.count(), 2)

    # ── Cascade delete ────────────────────────────────────────────────────

    def test_cascade_delete_with_hcp(self):
        self._make_interaction()
        self.assertEqual(Interaction.objects.count(), 1)
        self.hcp.delete()
        self.assertEqual(Interaction.objects.count(), 0)

    # ── JSONField defaults ────────────────────────────────────────────────

    def test_json_fields_default_to_empty_list(self):
        interaction = Interaction.objects.create(
            hcp=self.hcp,
            interaction_type=InteractionType.EMAIL,
            date=date.today(),
        )
        self.assertEqual(interaction.attendees, [])
        self.assertEqual(interaction.materials_shared, [])
        self.assertEqual(interaction.samples_distributed, [])
        self.assertEqual(interaction.follow_up_actions, [])

    # ── ai_processed flag ─────────────────────────────────────────────────

    def test_ai_processed_defaults_false(self):
        interaction = Interaction.objects.create(
            hcp=self.hcp,
            interaction_type=InteractionType.VIRTUAL,
            date=date.today(),
        )
        self.assertFalse(interaction.ai_processed)

    def test_set_ai_processed(self):
        interaction = self._make_interaction()
        interaction.ai_processed = True
        interaction.save(update_fields=["ai_processed", "updated_at"])
        interaction.refresh_from_db()
        self.assertTrue(interaction.ai_processed)

    # ── Ordering ──────────────────────────────────────────────────────────

    def test_default_ordering_by_date_desc(self):
        self._make_interaction(date=date(2025, 1, 1))
        self._make_interaction(date=date(2025, 12, 31))
        dates = list(Interaction.objects.values_list("date", flat=True))
        self.assertEqual(dates, sorted(dates, reverse=True))
