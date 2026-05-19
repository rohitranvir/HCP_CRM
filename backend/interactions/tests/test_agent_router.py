"""
interactions/tests/test_agent_router.py
Unit tests for the agent router intent detection and response structure.

Run with:
    python manage.py test interactions.tests.test_agent_router
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase

from interactions.agent_router import detect_intent, route, AgentRouter, VALID_INTENTS


class DetectIntentTests(TestCase):
    """Test intent classification logic."""

    @patch("interactions.agent_router._get_llm")
    def test_returns_valid_intent(self, mock_llm_factory):
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        mock_response      = MagicMock()
        mock_response.content = "log_interaction"

        # Chain: prompt | llm → invoke
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        result = detect_intent("I just visited Dr. Sharma and discussed CardioMax")
        self.assertIn(result, VALID_INTENTS)

    @patch("interactions.agent_router._get_llm")
    def test_unknown_intent_defaults_to_search_hcp(self, mock_llm_factory):
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        mock_response         = MagicMock()
        mock_response.content = "completely_invalid_intent_xyz"

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_response
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        result = detect_intent("some ambiguous message")
        self.assertEqual(result, "search_hcp")

    @patch("interactions.agent_router._get_llm")
    def test_llm_failure_defaults_to_search_hcp(self, mock_llm_factory):
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("Groq connection error")
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        result = detect_intent("any message")
        self.assertEqual(result, "search_hcp")


class RouteTests(TestCase):
    """Test the route() function response structure."""

    def test_empty_message_returns_error(self):
        result = route(user_message="")
        self.assertIn("error", result)
        self.assertTrue(len(result["error"]) > 0)

    def test_whitespace_message_returns_error(self):
        result = route(user_message="   ")
        self.assertIn("error", result)

    @patch("interactions.agent_router.detect_intent", return_value="search_hcp")
    @patch("interactions.agent_router.run_agent")
    def test_successful_route_has_required_keys(self, mock_run, mock_intent):
        mock_run.return_value = {
            "tool":   "search_hcp_tool",
            "intent": "search_hcp",
            "result": {"status": "ok", "results": []},
            "error":  "",
        }
        result = route("Find Dr. Patel")
        for key in ("tool", "tool_label", "intent", "result", "error", "input"):
            self.assertIn(key, result)

    @patch("interactions.agent_router.detect_intent", return_value="edit_interaction")
    def test_edit_without_id_returns_helpful_error(self, mock_intent):
        result = route("Change the sentiment of interaction to positive")
        self.assertIn("error", result)
        self.assertIn("interaction_id", result["error"].lower())

    @patch("interactions.agent_router.detect_intent", return_value="suggest_followup")
    def test_suggest_followup_auto_extracts_id_from_message(self, mock_intent):
        with patch("interactions.agent_router.run_agent") as mock_run:
            mock_run.return_value = {
                "tool":   "suggest_followup_tool",
                "intent": "suggest_followup",
                "result": {"suggestions": ["Call back", "Send brochure", "Schedule demo"]},
                "error":  "",
            }
            result = route("What should I do after interaction 42?")
            # Should auto-extract interaction_id=42
            self.assertEqual(result["input"]["interaction_id"], 42)


class AgentRouterClassTests(TestCase):
    """Test the AgentRouter class wrapper."""

    @patch("interactions.agent_router.detect_intent", return_value="log_interaction")
    def test_detect_returns_dict_with_intent_and_label(self, mock_intent):
        router = AgentRouter()
        result = router.detect("I logged a call with Dr. Mehta")
        self.assertEqual(result["intent"], "log_interaction")
        self.assertIn("tool_label", result)
        self.assertTrue(len(result["tool_label"]) > 0)
