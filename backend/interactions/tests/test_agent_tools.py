"""
interactions/tests/test_agent_tools.py
Unit tests for individual LangGraph agent tool nodes.
All LLM calls and DB writes are mocked.

Run with:
    python manage.py test interactions.tests.test_agent_tools
"""

from datetime import date
from unittest.mock import patch, MagicMock, PropertyMock
from django.test import TestCase
from interactions.models import HCP, Interaction, Specialty, InteractionType, SentimentScore
from interactions.agent import (
    AgentState,
    log_interaction_tool,
    edit_interaction_tool,
    suggest_followup_tool,
    search_hcp_tool,
    summarize_history_tool,
    intent_node,
    format_response_node,
)


def _base_state(**overrides) -> AgentState:
    state: AgentState = {
        "user_message":   "test message",
        "interaction_id": None,
        "hcp_name":       None,
        "intent":         "",
        "tool_name":      "",
        "tool_result":    {},
        "error":          "",
        "final_response": {},
    }
    state.update(overrides)
    return state


# ─── Intent Node Tests ────────────────────────────────────────────────────────

class IntentNodeTests(TestCase):

    @patch("interactions.agent._llm")
    def test_valid_intent_set(self, mock_llm_factory):
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MagicMock(content="log_interaction")
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(user_message="Log a call with Dr. Shah")
        result = intent_node(state)
        self.assertEqual(result["intent"], "log_interaction")
        self.assertEqual(result["error"], "")

    @patch("interactions.agent._llm")
    def test_invalid_intent_defaults_to_search_hcp(self, mock_llm_factory):
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MagicMock(content="gibberish_intent_xyz")
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(user_message="something")
        result = intent_node(state)
        self.assertEqual(result["intent"], "search_hcp")

    @patch("interactions.agent._llm")
    def test_llm_error_defaults_gracefully(self, mock_llm_factory):
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("network error")
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(user_message="something")
        result = intent_node(state)
        self.assertEqual(result["intent"], "search_hcp")
        self.assertIn("error", result)


# ─── log_interaction_tool Tests ───────────────────────────────────────────────

class LogInteractionToolTests(TestCase):

    def setUp(self):
        self.hcp = HCP.objects.create(
            name="Dr. Priya Sharma",
            specialty=Specialty.CARDIOLOGY,
            email="priya@test.com",
        )

    @patch("interactions.agent._llm")
    def test_successful_log_creates_interaction(self, mock_llm_factory):
        import json
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        extracted = {
            "hcp_name": "Dr. Priya Sharma",
            "interaction_type": "in_person",
            "date": "2025-06-15",
            "time": None,
            "attendees": ["Rep A"],
            "topics_discussed": "CardioMax",
            "materials_shared": [],
            "samples_distributed": [],
            "sentiment": "positive",
            "outcomes": "Interested in prescribing.",
        }
        mock_chain.invoke.return_value = MagicMock(content=json.dumps(extracted))
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(user_message="Visited Dr. Priya Sharma today")
        result = log_interaction_tool(state)

        self.assertEqual(result["tool_name"], "log_interaction_tool")
        self.assertEqual(result["tool_result"]["status"], "created")
        self.assertIn("interaction_id", result["tool_result"])
        self.assertEqual(Interaction.objects.count(), 1)

    @patch("interactions.agent._llm")
    def test_hcp_not_found_returns_helpful_message(self, mock_llm_factory):
        import json
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        extracted = {
            "hcp_name": "Dr. Unknown Nobody",
            "interaction_type": "phone",
            "date": "2025-06-15",
            "time": None,
            "attendees": [],
            "topics_discussed": "",
            "materials_shared": [],
            "samples_distributed": [],
            "sentiment": "neutral",
            "outcomes": "",
        }
        mock_chain.invoke.return_value = MagicMock(content=json.dumps(extracted))
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(user_message="Visited Dr. Unknown Nobody")
        result = log_interaction_tool(state)

        self.assertEqual(result["tool_result"]["status"], "hcp_not_found")
        self.assertEqual(Interaction.objects.count(), 0)

    @patch("interactions.agent._llm")
    def test_invalid_json_from_llm_returns_error(self, mock_llm_factory):
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MagicMock(content="NOT JSON AT ALL !!!")
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(user_message="something")
        result = log_interaction_tool(state)
        self.assertIn("error", result)
        self.assertTrue(len(result["error"]) > 0)


# ─── search_hcp_tool Tests ────────────────────────────────────────────────────

class SearchHCPToolTests(TestCase):

    def setUp(self):
        HCP.objects.create(name="Dr. Patel",  specialty=Specialty.CARDIOLOGY,   email="patel@test.com")
        HCP.objects.create(name="Dr. Patel2", specialty=Specialty.ONCOLOGY,     email="patel2@test.com")
        HCP.objects.create(name="Dr. Mehta",  specialty=Specialty.NEUROLOGY,    email="mehta@test.com")

    def test_search_returns_matching_hcps(self):
        state = _base_state(user_message="find Dr. Patel", hcp_name="Patel")
        result = search_hcp_tool(state)
        self.assertEqual(result["tool_name"], "search_hcp_tool")
        self.assertEqual(result["tool_result"]["status"], "ok")
        self.assertEqual(result["tool_result"]["count"], 2)

    def test_search_no_results_returns_empty_list(self):
        state = _base_state(user_message="find Dr. XYZNobody", hcp_name="XYZNobody")
        result = search_hcp_tool(state)
        self.assertEqual(result["tool_result"]["count"], 0)
        self.assertEqual(result["tool_result"]["results"], [])

    def test_result_contains_expected_fields(self):
        state = _base_state(user_message="find Mehta", hcp_name="Mehta")
        result = search_hcp_tool(state)
        record = result["tool_result"]["results"][0]
        for field in ("id", "name", "specialty", "email", "is_active", "total_interactions"):
            self.assertIn(field, record)


# ─── suggest_followup_tool Tests ──────────────────────────────────────────────

class SuggestFollowupToolTests(TestCase):

    def setUp(self):
        self.hcp = HCP.objects.create(
            name="Dr. Kapoor",
            specialty=Specialty.ONCOLOGY,
            email="kapoor@test.com",
        )
        self.interaction = Interaction.objects.create(
            hcp=self.hcp,
            interaction_type=InteractionType.IN_PERSON,
            date=date(2025, 6, 15),
            topics_discussed="Keytruda for NSCLC",
            sentiment=SentimentScore.POSITIVE,
        )

    @patch("interactions.agent._llm")
    def test_suggestions_returned_as_list(self, mock_llm_factory):
        import json
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        suggestions = ["Send clinical data", "Follow up in 2 weeks", "Arrange speaker program"]
        mock_chain.invoke.return_value = MagicMock(content=json.dumps(suggestions))
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(
            user_message="suggest follow-ups",
            interaction_id=self.interaction.pk,
        )
        result = suggest_followup_tool(state)
        self.assertEqual(result["tool_name"], "suggest_followup_tool")
        self.assertEqual(result["tool_result"]["status"], "ok")
        self.assertEqual(len(result["tool_result"]["suggestions"]), 3)

    def test_missing_id_returns_error(self):
        state = _base_state(user_message="give me suggestions")
        result = suggest_followup_tool(state)
        self.assertIn("error", result)

    def test_invalid_id_returns_not_found(self):
        state = _base_state(user_message="suggestions", interaction_id=99999)
        result = suggest_followup_tool(state)
        self.assertEqual(result["tool_result"]["status"], "not_found")


# ─── edit_interaction_tool Tests ──────────────────────────────────────────────

class EditInteractionToolTests(TestCase):

    def setUp(self):
        self.hcp = HCP.objects.create(
            name="Dr. Joshi",
            specialty=Specialty.PSYCHIATRY,
            email="joshi@test.com",
        )
        self.interaction = Interaction.objects.create(
            hcp=self.hcp,
            interaction_type=InteractionType.IN_PERSON,
            date=date(2025, 5, 10),
            sentiment=SentimentScore.NEUTRAL,
        )

    @patch("interactions.agent._llm")
    def test_edit_updates_only_specified_fields(self, mock_llm_factory):
        import json
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MagicMock(
            content=json.dumps({"sentiment": "positive"})
        )
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        original_date = self.interaction.date
        state = _base_state(
            user_message="change sentiment to positive",
            interaction_id=self.interaction.pk,
        )
        result = edit_interaction_tool(state)

        self.interaction.refresh_from_db()
        self.assertEqual(self.interaction.sentiment, "positive")
        self.assertEqual(self.interaction.date, original_date)  # unchanged
        self.assertEqual(result["tool_result"]["status"], "updated")

    def test_missing_interaction_id_returns_error(self):
        state = _base_state(user_message="update sentiment")
        result = edit_interaction_tool(state)
        self.assertIn("error", result)
        self.assertIn("interaction_id", result["error"])

    def test_nonexistent_id_returns_not_found(self):
        state = _base_state(user_message="update something", interaction_id=99999)
        result = edit_interaction_tool(state)
        self.assertEqual(result["tool_result"]["status"], "not_found")


# ─── summarize_history_tool Tests ─────────────────────────────────────────────

class SummarizeHistoryToolTests(TestCase):

    def setUp(self):
        self.hcp = HCP.objects.create(
            name="Dr. Rao",
            specialty=Specialty.CARDIOLOGY,
            email="rao@test.com",
        )

    def test_hcp_not_found_returns_error(self):
        state = _base_state(user_message="summarize Dr. Nobody", hcp_name="Dr. Nobody")
        result = summarize_history_tool(state)
        self.assertEqual(result["tool_result"]["status"], "hcp_not_found")

    def test_no_interactions_returns_no_interactions_status(self):
        state = _base_state(user_message="summarize Dr. Rao", hcp_name="Rao")
        result = summarize_history_tool(state)
        self.assertEqual(result["tool_result"]["status"], "no_interactions")

    @patch("interactions.agent._llm")
    def test_summary_generated_for_hcp_with_interactions(self, mock_llm_factory):
        Interaction.objects.create(
            hcp=self.hcp,
            interaction_type=InteractionType.IN_PERSON,
            date=date(2025, 3, 1),
            topics_discussed="CardioMax launch",
            sentiment=SentimentScore.POSITIVE,
        )
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MagicMock(
            content="Dr. Rao shows consistent interest in CardioMax."
        )
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        state = _base_state(user_message="summarise Dr. Rao", hcp_name="Rao")
        result = summarize_history_tool(state)
        self.assertEqual(result["tool_result"]["status"], "ok")
        self.assertIn("summary", result["tool_result"])
        self.assertTrue(len(result["tool_result"]["summary"]) > 0)


# ─── format_response_node Tests ───────────────────────────────────────────────

class FormatResponseNodeTests(TestCase):

    def test_wraps_into_final_response(self):
        state = _base_state(
            tool_name="search_hcp_tool",
            intent="search_hcp",
            tool_result={"status": "ok", "count": 2},
            error="",
        )
        result = format_response_node(state)
        self.assertIn("final_response", result)
        fr = result["final_response"]
        self.assertEqual(fr["tool"],   "search_hcp_tool")
        self.assertEqual(fr["intent"], "search_hcp")
        self.assertEqual(fr["result"]["count"], 2)
        self.assertEqual(fr["error"], "")

    def test_error_propagated_to_final_response(self):
        state = _base_state(
            tool_name="log_interaction_tool",
            intent="log_interaction",
            tool_result={},
            error="DB save failed",
        )
        result = format_response_node(state)
        self.assertEqual(result["final_response"]["error"], "DB save failed")
