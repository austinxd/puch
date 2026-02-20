from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from properties.models import Agent

User = get_user_model()


class Command(BaseCommand):
    help = 'Create an admin user linked to an existing agent'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--password', required=True)
        parser.add_argument('--agent-id', type=int, required=True)

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        agent_id = options['agent_id']

        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Agent {agent_id} not found'))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'is_staff': True, 'is_superuser': True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user "{username}"'))
        else:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.WARNING(f'Updated existing user "{username}" to admin'))

        agent.user = user
        agent.save()
        self.stdout.write(self.style.SUCCESS(f'Linked user "{username}" to agent "{agent.name}" (id={agent.id})'))
