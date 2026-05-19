"""
backend/interactions/tests.py
Final testing module ensuring the LangGraph agent tools and API endpoints function correctly.
Uses Django's APITestCase to mock LLM calls and test view routing.

Run with:
    cd backend
    python manage.py test interactions
"""

from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from interactions.models import HCP, Interaction, Specialty


class FinalProjectTests(APITestCase):

    def setUp(self):
        # Create seed data for testing
        self.hcp = HCP.objects.create(
            name="Dr. Smith", 
            email="smith@test.in", 
            specialty=Specialty.CARDIOLOGY
        )
        self.interaction = Interaction.objects.create(
            hcp=self.hcp, 
            topics_discussed="Initial meeting",
            sentiment="unknown"
        )

    # ─── 1. Test Agent Tools ──────────────────────────────────────────────────

    @patch("interactions.agent._llm")
    def test_log_interaction_tool_with_sample_message(self, mock_llm_factory):
        import json
        from interactions.agent import log_interaction_tool

        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MagicMock(content=json.dumps({
            "hcp_name": "Dr. Smith",
            "interaction_type": "in_person",
            "date": "2026-01-01",
            "sentiment": "positive",
            "topics_discussed": "Product X efficiency",
            "materials_shared": ["brochures"]
        }))
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = {"user_message": "Met Dr. Smith today, discussed Product X efficiency, sentiment positive, shared brochures"}
        result = log_interaction_tool(state)
        
        self.assertEqual(result["tool_result"]["status"], "created")
        self.assertEqual(Interaction.objects.count(), 2)

    @patch("interactions.agent._llm")
    def test_edit_interaction_tool_with_correction_message(self, mock_llm_factory):
        import json
        from interactions.agent import edit_interaction_tool

        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        # Mocking the AI deciding to change the sentiment based on user prompt
        mock_chain.invoke.return_value = MagicMock(content=json.dumps({
            "sentiment": "negative"
        }))
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = {
            "user_message": "Change the name to Dr. John and sentiment to negative",
            "interaction_id": self.interaction.pk
        }
        result = edit_interaction_tool(state)
        
        self.assertEqual(result["tool_result"]["status"], "updated")
        self.interaction.refresh_from_db()
        self.assertEqual(self.interaction.sentiment, "negative")


    # ─── 2. Test All 5 API Endpoints ──────────────────────────────────────────

    @patch("interactions.views.route")
    def test_api_chat(self, mock_route):
        """1. POST /api/chat/"""
        mock_route.return_value = {
            "tool": "search_hcp_tool",
            "result": {"status": "ok", "count": 1},
            "message": "Found HCP"
        }
        url = reverse("api-chat")
        response = self.client.post(url, {"message": "Search for Dr. Smith"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tool_used"], "search_hcp_tool")

    def test_api_interactions_list(self):
        """2. GET /api/interactions/"""
        url = reverse("api-interaction-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_api_interactions_detail(self):
        """3. GET /api/interactions/<id>/"""
        url = reverse("api-interaction-detail", kwargs={"pk": self.interaction.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.interaction.pk)

    def test_api_hcp_list(self):
        """4. GET /api/hcp/"""
        url = reverse("api-hcp-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_api_hcp_search(self):
        """5. GET /api/hcp/search/?name=<query>"""
        url = reverse("api-hcp-search") + "?name=Smith"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Dr. Smith")

    @patch("interactions.views.route")
    def test_api_interactions_followup(self, mock_route):
        """6. POST /api/interactions/<id>/followup/"""
        mock_route.return_value = {
            "tool": "suggest_followup_tool",
            "result": {"suggestions": ["Email Dr. Smith", "Schedule visit"]},
            "message": "Generated suggestions"
        }
        url = reverse("api-interaction-followup", kwargs={"pk": self.interaction.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tool_used"], "suggest_followup_tool")
