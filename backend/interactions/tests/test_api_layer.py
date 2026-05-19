"""
interactions/tests/test_api_layer.py
Integration tests for the simplified /api/ REST layer (Prompt 3).

Tests cover:
    ChatView          — POST /api/chat/
    InteractionListAPIView   — GET /api/interactions/
    InteractionDetailAPIView — GET /api/interactions/<id>/
    HCPListAPIView    — GET /api/hcp/
    HCPSearchView     — GET /api/hcp/search/?name=<q>
    FollowupView      — POST /api/interactions/<id>/followup/

Run with:
    python manage.py test interactions.tests.test_api_layer
"""

from datetime import date
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from interactions.models import HCP, Interaction, Specialty, InteractionType, SentimentScore


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_hcp(name="Dr. Anita Desai", email="anita@test.in", specialty=Specialty.CARDIOLOGY, **kw) -> HCP:
    return HCP.objects.create(
        name=name, email=email, specialty=specialty,
        hospital="Apollo", city="Mumbai", **kw
    )


def make_interaction(hcp, **kw) -> Interaction:
    defaults = dict(
        interaction_type=InteractionType.IN_PERSON,
        date=date(2025, 6, 15),
        topics_discussed="CardioMax discussion",
        sentiment=SentimentScore.POSITIVE,
        outcomes="HCP interested.",
        attendees=["Rep A"],
    )
    defaults.update(kw)
    return Interaction.objects.create(hcp=hcp, **defaults)


# ═════════════════════════════════════════════════════════════════════════════
#  ChatView  — POST /api/chat/
# ═════════════════════════════════════════════════════════════════════════════

class ChatViewTests(APITestCase):

    def _url(self):
        return reverse("api-chat")

    def test_missing_message_returns_400(self):
        response = self.client.post(self._url(), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_blank_message_returns_400(self):
        response = self.client.post(self._url(), {"message": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_interaction_id_returns_400(self):
        response = self.client.post(
            self._url(),
            {"message": "edit something", "interaction_id": "abc"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("interactions.views.route")
    def test_successful_search_response_shape(self, mock_route):
        mock_route.return_value = {
            "tool":   "search_hcp_tool",
            "intent": "search_hcp",
            "result": {"status": "ok", "count": 2, "results": []},
            "error":  "",
        }
        response = self.client.post(
            self._url(), {"message": "Find Dr. Patel"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tool_used",  response.data)
        self.assertIn("result",     response.data)
        self.assertIn("message",    response.data)
        self.assertEqual(response.data["tool_used"], "search_hcp_tool")

    @patch("interactions.views.route")
    def test_log_interaction_message_text(self, mock_route):
        mock_route.return_value = {
            "tool":   "log_interaction_tool",
            "intent": "log_interaction",
            "result": {"status": "created", "interaction_id": 7, "hcp_name": "Dr. Sharma"},
            "error":  "",
        }
        response = self.client.post(
            self._url(), {"message": "Logged visit with Dr. Sharma"}, format="json"
        )
        self.assertIn("#7", response.data["message"])
        self.assertIn("Dr. Sharma", response.data["message"])

    @patch("interactions.views.route")
    def test_edit_interaction_message_text(self, mock_route):
        mock_route.return_value = {
            "tool":   "edit_interaction_tool",
            "intent": "edit_interaction",
            "result": {"status": "updated", "changed_fields": {"sentiment": "positive"}},
            "error":  "",
        }
        response = self.client.post(
            self._url(),
            {"message": "Change sentiment to positive", "interaction_id": 1},
            format="json",
        )
        self.assertIn("sentiment", response.data["message"])

    @patch("interactions.views.route")
    def test_suggest_followup_message_text(self, mock_route):
        mock_route.return_value = {
            "tool":   "suggest_followup_tool",
            "intent": "suggest_followup",
            "result": {"status": "ok", "suggestions": ["A", "B", "C"]},
            "error":  "",
        }
        response = self.client.post(
            self._url(),
            {"message": "Suggest follow-ups for interaction 1", "interaction_id": 1},
            format="json",
        )
        self.assertIn("3", response.data["message"])

    @patch("interactions.views.route")
    def test_error_result_shows_error_text(self, mock_route):
        mock_route.return_value = {
            "tool":   "unknown",
            "intent": "unknown",
            "result": {},
            "error":  "GROQ_API_KEY is not set.",
        }
        response = self.client.post(
            self._url(), {"message": "do something"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("GROQ_API_KEY", response.data["message"])

    @patch("interactions.views.route")
    def test_interaction_id_passed_to_agent(self, mock_route):
        mock_route.return_value = {
            "tool": "suggest_followup_tool", "intent": "suggest_followup",
            "result": {"suggestions": []}, "error": "",
        }
        self.client.post(
            self._url(),
            {"message": "suggest follow-ups", "interaction_id": 42},
            format="json",
        )
        call_kwargs = mock_route.call_args.kwargs
        self.assertEqual(call_kwargs["interaction_id"], 42)


# ═════════════════════════════════════════════════════════════════════════════
#  InteractionListAPIView  — GET /api/interactions/
# ═════════════════════════════════════════════════════════════════════════════

class InteractionListAPIViewTests(APITestCase):

    def _url(self):
        return reverse("api-interaction-list")

    def test_empty_list_returns_200(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_returns_all_interactions(self):
        hcp = make_hcp()
        make_interaction(hcp)
        make_interaction(hcp, date=date(2025, 7, 1))
        response = self.client.get(self._url())
        self.assertEqual(response.data["count"], 2)

    def test_uses_list_serializer_fields(self):
        hcp = make_hcp()
        make_interaction(hcp)
        response = self.client.get(self._url())
        item = response.data["results"][0]
        self.assertIn("hcp_name", item)
        self.assertNotIn("hcp_detail", item)  # list serializer only

    def test_ordered_by_date_desc(self):
        hcp = make_hcp()
        make_interaction(hcp, date=date(2025, 1, 1))
        make_interaction(hcp, date=date(2025, 12, 31))
        response = self.client.get(self._url())
        dates = [r["date"] for r in response.data["results"]]
        self.assertEqual(dates, sorted(dates, reverse=True))


# ═════════════════════════════════════════════════════════════════════════════
#  InteractionDetailAPIView  — GET /api/interactions/<id>/
# ═════════════════════════════════════════════════════════════════════════════

class InteractionDetailAPIViewTests(APITestCase):

    def setUp(self):
        self.hcp = make_hcp()
        self.interaction = make_interaction(self.hcp)

    def _url(self, pk=None):
        return reverse("api-interaction-detail", kwargs={"pk": pk or self.interaction.pk})

    def test_retrieve_returns_full_detail(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("hcp_detail", response.data)  # full serializer
        self.assertEqual(response.data["id"], self.interaction.pk)

    def test_nonexistent_returns_404(self):
        response = self.client.get(self._url(pk=99999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_ai_fields(self):
        response = self.client.get(self._url())
        for field in ("sentiment", "outcomes", "follow_up_actions", "ai_processed"):
            self.assertIn(field, response.data)


# ═════════════════════════════════════════════════════════════════════════════
#  HCPListAPIView  — GET /api/hcp/
# ═════════════════════════════════════════════════════════════════════════════

class HCPListAPIViewTests(APITestCase):

    def _url(self):
        return reverse("api-hcp-list")

    def test_empty_list(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_returns_only_active_hcps(self):
        make_hcp()
        make_hcp(name="Dr. Inactive", email="inactive@test.in", is_active=False)
        response = self.client.get(self._url())
        self.assertEqual(response.data["count"], 1)

    def test_ordered_by_name(self):
        make_hcp(name="Dr. Zara",  email="z@test.in")
        make_hcp(name="Dr. Aaron", email="a@test.in")
        response = self.client.get(self._url())
        names = [r["name"] for r in response.data["results"]]
        self.assertEqual(names, sorted(names))

    def test_uses_list_serializer(self):
        make_hcp()
        response = self.client.get(self._url())
        item = response.data["results"][0]
        self.assertIn("total_interactions", item)
        self.assertNotIn("specialty_choices", item)


# ═════════════════════════════════════════════════════════════════════════════
#  HCPSearchView  — GET /api/hcp/search/?name=<query>
# ═════════════════════════════════════════════════════════════════════════════

class HCPSearchViewTests(APITestCase):

    def _url(self, name=""):
        base = reverse("api-hcp-search")
        return f"{base}?name={name}" if name else base

    def setUp(self):
        make_hcp(name="Dr. Priya Patel",  email="priya@test.in", specialty=Specialty.CARDIOLOGY)
        make_hcp(name="Dr. Rahul Patel",  email="rahul@test.in", specialty=Specialty.ONCOLOGY)
        make_hcp(name="Dr. Suresh Mehta", email="suresh@test.in", specialty=Specialty.NEUROLOGY)

    def test_missing_name_returns_400(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_name_returns_400(self):
        response = self.client.get(self._url(name=""))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_match_returns_results(self):
        response = self.client.get(self._url(name="Patel"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_case_insensitive_search(self):
        response = self.client.get(self._url(name="patel"))
        self.assertEqual(response.data["count"], 2)

    def test_no_match_returns_empty(self):
        response = self.client.get(self._url(name="XYZNobody"))
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_result_shape_has_required_fields(self):
        response = self.client.get(self._url(name="Mehta"))
        record = response.data["results"][0]
        for field in ("id", "name", "specialty", "email", "hospital", "city", "total_interactions"):
            self.assertIn(field, record)

    def test_inactive_hcp_excluded(self):
        make_hcp(name="Dr. Gone Patel", email="gone@test.in", is_active=False)
        response = self.client.get(self._url(name="Patel"))
        self.assertEqual(response.data["count"], 2)  # inactive excluded


# ═════════════════════════════════════════════════════════════════════════════
#  FollowupView  — POST /api/interactions/<id>/followup/
# ═════════════════════════════════════════════════════════════════════════════

class FollowupViewTests(APITestCase):

    def setUp(self):
        self.hcp = make_hcp()
        self.interaction = make_interaction(self.hcp)

    def _url(self, pk=None):
        return reverse("api-interaction-followup", kwargs={"pk": pk or self.interaction.pk})

    def test_nonexistent_interaction_returns_404(self):
        response = self.client.post(reverse("api-interaction-followup", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("interactions.views.route")
    def test_successful_followup_response_shape(self, mock_route):
        mock_route.return_value = {
            "tool":   "suggest_followup_tool",
            "intent": "suggest_followup",
            "result": {
                "status": "ok",
                "suggestions": [
                    "Send clinical dossier",
                    "Schedule speaker program",
                    "Follow up in 2 weeks",
                ],
            },
            "error": "",
        }
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tool_used"],      "suggest_followup_tool")
        self.assertEqual(response.data["interaction_id"], self.interaction.pk)
        self.assertEqual(response.data["hcp_name"],       self.hcp.name)
        self.assertIn("result",   response.data)
        self.assertIn("message",  response.data)
        self.assertIn("3",        response.data["message"])

    @patch("interactions.views.route")
    def test_followup_singular_message_when_one_suggestion(self, mock_route):
        mock_route.return_value = {
            "tool":   "suggest_followup_tool",
            "intent": "suggest_followup",
            "result": {"status": "ok", "suggestions": ["Send brochure"]},
            "error": "",
        }
        response = self.client.post(self._url())
        self.assertIn("1 follow-up suggestion.", response.data["message"])

    @patch("interactions.views.route")
    def test_agent_error_returns_500(self, mock_route):
        mock_route.return_value = {
            "tool":   "suggest_followup_tool",
            "intent": "suggest_followup",
            "result": {"suggestions": []},
            "error":  "GROQ_API_KEY not set.",
        }
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("interactions.views.route")
    def test_route_called_with_correct_interaction_id(self, mock_route):
        mock_route.return_value = {
            "tool": "suggest_followup_tool", "intent": "suggest_followup",
            "result": {"suggestions": ["A", "B", "C"]}, "error": "",
        }
        self.client.post(self._url())
        call_kwargs = mock_route.call_args.kwargs
        self.assertEqual(call_kwargs["interaction_id"], self.interaction.pk)
