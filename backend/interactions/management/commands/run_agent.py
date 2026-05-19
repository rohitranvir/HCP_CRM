"""
Management command: run_agent
Usage:
    python manage.py run_agent "Log a call with Dr. Sharma today about CardioMax"
    python manage.py run_agent "Suggest follow-ups for interaction 3" --id 3
    python manage.py run_agent "Search for Dr. Patel"
    python manage.py run_agent "Summarise history for Dr. Kapoor" --hcp "Dr. Kapoor"
"""

import json
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run the HCP CRM LangGraph agent from the command line."

    def add_arguments(self, parser):
        parser.add_argument(
            "message",
            type=str,
            help="Natural language message to send to the agent.",
        )
        parser.add_argument(
            "--id",
            dest="interaction_id",
            type=int,
            default=None,
            help="Interaction ID (required for edit/suggest_followup).",
        )
        parser.add_argument(
            "--hcp",
            dest="hcp_name",
            type=str,
            default=None,
            help="HCP name hint (optional, for search/summarize).",
        )
        parser.add_argument(
            "--intent-only",
            action="store_true",
            help="Detect intent only, do not run the full agent.",
        )

    def handle(self, *args, **options):
        message        = options["message"]
        interaction_id = options["interaction_id"]
        hcp_name       = options["hcp_name"]
        intent_only    = options["intent_only"]

        self.stdout.write(self.style.HTTP_INFO(f"\n📨  Message: {message}"))
        if interaction_id:
            self.stdout.write(self.style.HTTP_INFO(f"🔑  interaction_id: {interaction_id}"))
        if hcp_name:
            self.stdout.write(self.style.HTTP_INFO(f"👤  hcp_name: {hcp_name}"))
        self.stdout.write("")

        try:
            if intent_only:
                from interactions.agent_router import AgentRouter
                router = AgentRouter()
                result = router.detect(message)
                self.stdout.write(self.style.SUCCESS("✅  Intent detected:"))
                self.stdout.write(json.dumps(result, indent=2))
                return

            from interactions.agent_router import route
            result = route(
                user_message=message,
                interaction_id=interaction_id,
                hcp_name=hcp_name,
            )

            if result.get("error"):
                self.stdout.write(self.style.ERROR(f"❌  Error: {result['error']}"))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"✅  Tool: {result.get('tool_label', result.get('tool'))}"
                ))

            self.stdout.write(json.dumps(result, indent=2, default=str))

        except Exception as exc:
            raise CommandError(f"Agent failed: {exc}") from exc
