"""
interactions/tests/test_views.py
Integration tests for HCP and Interaction REST API endpoints.
Uses Django test client — no real DB writes to PostgreSQL required (uses test DB).

Run with:
    python manage.py test interactions.tests.test_views
"""

import json
from datetime import date
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from interactions.models import HCP, Interaction, Specialty, InteractionType, SentimentScore


# ═════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═════════════════════════════════════════════════════════════════════════════

def make_hcp(**kwargs) -> HCP:
    defaults = dict(
        name="Dr. Anita Desai",
        specialty=Specialty.CARDIOLOGY,
        email="anita.desai@hospital.in",
        phone="+919898989898",
        hospital="Lilavati Hospital",
        city="Mumbai",
    )
    defaults.update(kwargs)
    return HCP.objects.create(**defaults)


def make_interaction(hcp: HCP, **kwargs) -> Interaction:
    defaults = dict(
        hcp=hcp,
        interaction_type=InteractionType.IN_PERSON,
        date=date(2025, 6, 15),
        topics_discussed="CardioMax efficacy",
        sentiment=SentimentScore.POSITIVE,
        outcomes="HCP agreed to trial prescription.",
        attendees=["Rep A"],
        materials_shared=["Brochure"],
        samples_distributed=["CardioMax 5mg"],
        follow_up_actions=["Send data", "Follow up in 2 weeks"],
    )
    defaults.update(kwargs)
    return Interaction.objects.create(**defaults)


# ═════════════════════════════════════════════════════════════════════════════
#  HCP ViewSet Tests
# ═════════════════════════════════════════════════════════════════════════════

class HCPListCreateTests(APITestCase):

    def test_list_hcps_empty(self):
        url = reverse("interactions:hcp-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_list_hcps_returns_records(self):
        make_hcp()
        make_hcp(name="Dr. Rajan", email="rajan@test.in")
        url = reverse("interactions:hcp-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_create_hcp_success(self):
        url = reverse("interactions:hcp-list")
        payload = {
            "name":      "Dr. Suresh Mehta",
            "specialty": "cardiology",
            "email":     "suresh.mehta@clinic.in",
            "phone":     "+919001234567",
            "hospital":  "Breach Candy Hospital",
            "city":      "Mumbai",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HCP.objects.count(), 1)
        self.assertEqual(response.data["name"], "Dr. Suresh Mehta")

    def test_create_hcp_duplicate_email_fails(self):
        make_hcp()
        url = reverse("interactions:hcp-list")
        payload = {
            "name":      "Dr. Another",
            "specialty": "neurology",
            "email":     "anita.desai@hospital.in",  # duplicate
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_hcp_missing_required_fields(self):
        url = reverse("interactions:hcp-list")
        response = self.client.post(url, {"name": "Dr. X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_uses_list_serializer(self):
        """List response should NOT include 'specialty_choices' (detail-only field)."""
        make_hcp()
        url = reverse("interactions:hcp-list")
        response = self.client.get(url)
        hcp_data = response.data["results"][0]
        self.assertNotIn("specialty_choices", hcp_data)
        self.assertIn("total_interactions", hcp_data)


class HCPRetrieveUpdateDeleteTests(APITestCase):

    def setUp(self):
        self.hcp = make_hcp()

    def test_retrieve_hcp(self):
        url = reverse("interactions:hcp-detail", kwargs={"pk": self.hcp.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Dr. Anita Desai")
        self.assertIn("specialty_choices", response.data)

    def test_partial_update_hcp(self):
        url = reverse("interactions:hcp-detail", kwargs={"pk": self.hcp.pk})
        response = self.client.patch(url, {"city": "Delhi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hcp.refresh_from_db()
        self.assertEqual(self.hcp.city, "Delhi")

    def test_full_update_hcp(self):
        url = reverse("interactions:hcp-detail", kwargs={"pk": self.hcp.pk})
        payload = {
            "name":      "Dr. Anita Desai Updated",
            "specialty": "oncology",
            "email":     "anita.desai@hospital.in",
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hcp.refresh_from_db()
        self.assertEqual(self.hcp.specialty, "oncology")

    def test_delete_hcp(self):
        url = reverse("interactions:hcp-detail", kwargs={"pk": self.hcp.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HCP.objects.count(), 0)

    def test_retrieve_nonexistent_returns_404(self):
        url = reverse("interactions:hcp-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HCPFilterTests(APITestCase):

    def setUp(self):
        self.cardio_hcp = make_hcp(specialty=Specialty.CARDIOLOGY)
        make_hcp(name="Dr. Rao", specialty=Specialty.ONCOLOGY, email="rao@test.in")

    def test_filter_by_specialty(self):
        url = reverse("interactions:hcp-list") + "?specialty=cardiology"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["specialty"], "cardiology")

    def test_filter_by_is_active(self):
        self.cardio_hcp.is_active = False
        self.cardio_hcp.save()
        url = reverse("interactions:hcp-list") + "?is_active=true"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)

    def test_search_by_name(self):
        url = reverse("interactions:hcp-list") + "?search=Anita"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)

    def test_hcp_interactions_action(self):
        make_interaction(self.cardio_hcp)
        make_interaction(self.cardio_hcp, date=date(2025, 7, 1))
        url = reverse("interactions:hcp-interactions", kwargs={"pk": self.cardio_hcp.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


# ═════════════════════════════════════════════════════════════════════════════
#  Interaction ViewSet Tests
# ═════════════════════════════════════════════════════════════════════════════

class InteractionListCreateTests(APITestCase):

    def setUp(self):
        self.hcp = make_hcp()

    def test_list_interactions_empty(self):
        url = reverse("interactions:interaction-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_create_interaction_success(self):
        url = reverse("interactions:interaction-list")
        payload = {
            "hcp":              self.hcp.pk,
            "interaction_type": "virtual",
            "date":             "2025-06-20",
            "time":             "14:30:00",
            "attendees":        ["Rep A", "Medical Manager"],
            "topics_discussed": "Discussed Keytruda Phase 3 data.",
            "materials_shared": ["Phase3 PDF"],
            "samples_distributed": [],
            "sentiment":        "positive",
            "outcomes":         "HCP requested full dossier.",
            "follow_up_actions": ["Send dossier by Friday"],
            "rep_notes":        "Very engaged, asked detailed questions.",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interaction.objects.count(), 1)
        self.assertIn("hcp_detail", response.data)

    def test_create_interaction_invalid_hcp_fails(self):
        url = reverse("interactions:interaction-list")
        payload = {
            "hcp":  99999,
            "date": "2025-06-20",
            "interaction_type": "phone",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InteractionFilterTests(APITestCase):

    def setUp(self):
        self.hcp = make_hcp()
        self.i1 = make_interaction(
            self.hcp,
            interaction_type=InteractionType.IN_PERSON,
            sentiment=SentimentScore.POSITIVE,
            date=date(2025, 1, 1),
        )
        self.i2 = make_interaction(
            self.hcp,
            interaction_type=InteractionType.VIRTUAL,
            sentiment=SentimentScore.NEGATIVE,
            date=date(2025, 6, 1),
        )

    def test_filter_by_hcp(self):
        url = reverse("interactions:interaction-list") + f"?hcp={self.hcp.pk}"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 2)

    def test_filter_by_sentiment(self):
        url = reverse("interactions:interaction-list") + "?sentiment=positive"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_interaction_type(self):
        url = reverse("interactions:interaction-list") + "?interaction_type=virtual"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)

    def test_filter_date_range(self):
        url = reverse("interactions:interaction-list") + "?date_from=2025-05-01&date_to=2025-12-31"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 1)

    def test_list_uses_list_serializer(self):
        url = reverse("interactions:interaction-list")
        response = self.client.get(url)
        item = response.data["results"][0]
        self.assertIn("hcp_name", item)
        self.assertNotIn("hcp_detail", item)


# ═════════════════════════════════════════════════════════════════════════════
#  Agent View Tests
# ═════════════════════════════════════════════════════════════════════════════

class AgentViewTests(APITestCase):

    def test_missing_message_returns_400(self):
        url = reverse("interactions:agent")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_message_returns_400(self):
        url = reverse("interactions:agent")
        response = self.client.post(url, {"message": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_interaction_id_returns_400(self):
        url = reverse("interactions:agent")
        response = self.client.post(
            url,
            {"message": "edit interaction", "interaction_id": "not-a-number"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("interactions.views.route")
    def test_successful_agent_call_returns_200(self, mock_route):
        mock_route.return_value = {
            "tool":       "search_hcp_tool",
            "tool_label": "Search HCP Records",
            "intent":     "search_hcp",
            "result":     {"status": "ok", "count": 1, "results": []},
            "error":      "",
            "input":      {"message": "find Dr. Patel", "interaction_id": None, "hcp_name": None},
        }
        url = reverse("interactions:agent")
        response = self.client.post(url, {"message": "find Dr. Patel"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tool", response.data)
        self.assertIn("intent", response.data)
        self.assertIn("result", response.data)

    @patch("interactions.views.route")
    def test_agent_passes_interaction_id_and_hcp_name(self, mock_route):
        mock_route.return_value = {
            "tool": "suggest_followup_tool",
            "tool_label": "Suggest Follow-up Actions",
            "intent": "suggest_followup",
            "result": {"status": "ok", "suggestions": []},
            "error": "",
            "input": {"message": "suggest", "interaction_id": 5, "hcp_name": None},
        }
        url = reverse("interactions:agent")
        response = self.client.post(
            url,
            {"message": "suggest follow-up actions", "interaction_id": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify route was called with correct interaction_id
        call_kwargs = mock_route.call_args.kwargs
        self.assertEqual(call_kwargs["interaction_id"], 5)


class DetectIntentViewTests(APITestCase):

    def test_missing_message_returns_400(self):
        url = reverse("interactions:agent-detect-intent")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("interactions.views.AgentRouter")
    def test_detect_returns_intent_and_label(self, mock_router_class):
        mock_router = MagicMock()
        mock_router.detect.return_value = {
            "intent":     "log_interaction",
            "tool_label": "Log New Interaction",
        }
        mock_router_class.return_value = mock_router

        url = reverse("interactions:agent-detect-intent")
        response = self.client.post(url, {"message": "I visited Dr. Shah today"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["intent"], "log_interaction")
        self.assertIn("tool_label", response.data)
