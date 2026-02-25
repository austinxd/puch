from django.core.management.base import BaseCommand
from chatbot.models import ChatConversation, ChatMessage
from chatbot.services import assign_conversation_agent


class Command(BaseCommand):
    help = 'Assign agents to existing conversations based on first user message'

    def handle(self, *args, **options):
        conversations = ChatConversation.objects.filter(agent__isnull=True)
        total = conversations.count()
        assigned = 0
        skipped = 0

        self.stdout.write(f"Found {total} conversations without agent")

        for conv in conversations:
            first_msg = (
                ChatMessage.objects
                .filter(conversation=conv, role='user')
                .order_by('created_at')
                .values_list('content', flat=True)
                .first()
            )
            if not first_msg:
                skipped += 1
                continue

            assign_conversation_agent(conv, first_msg)
            if conv.agent:
                assigned += 1
                self.stdout.write(f"  {conv.session_id} → {conv.agent.name}")
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done: {assigned} assigned, {skipped} skipped (no property match), {total} total"
        ))
