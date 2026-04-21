import datetime
import uuid
from django.db import models
from django.utils import timezone

PERMANENT_PAUSE_DATE = datetime.datetime(9999, 12, 31, tzinfo=datetime.timezone.utc)


class ChatConversation(models.Model):
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    agent = models.ForeignKey(
        'properties.Agent',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations',
    )
    first_property = models.ForeignKey(
        'properties.Property',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='first_intent_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    admin_paused_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return str(self.session_id)

    @property
    def is_ai_paused(self):
        return self.admin_paused_until and self.admin_paused_until > timezone.now()

    @property
    def is_permanently_paused(self):
        return (self.admin_paused_until and
                self.admin_paused_until.year >= 9999)

    def pause_ai(self, minutes=30, permanent=False):
        if permanent:
            self.admin_paused_until = PERMANENT_PAUSE_DATE
        else:
            self.admin_paused_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=['admin_paused_until'])

    def unpause_ai(self):
        self.admin_paused_until = None
        self.save(update_fields=['admin_paused_until'])


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'
        ADMIN = 'admin', 'Admin'

    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name='messages'
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.content[:50]}'


class ClientIntent(models.Model):
    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name='intents'
    )
    phone = models.CharField(max_length=50, blank=True, default='')
    operacion = models.CharField(max_length=50, blank=True, default='')
    tipo_propiedad = models.CharField(max_length=100, blank=True, default='')
    distritos = models.CharField(max_length=500, blank=True, default='')
    precio_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    precio_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    habitaciones = models.CharField(max_length=50, blank=True, default='')
    caracteristicas = models.TextField(blank=True, default='')
    resumen = models.TextField(blank=True, default='')
    notificado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.phone or self.conversation.session_id} - {self.tipo_propiedad} {self.operacion}'


class PropertyInterest(models.Model):
    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name='interested_properties'
    )
    property = models.ForeignKey(
        'properties.Property', on_delete=models.CASCADE, related_name='client_interests'
    )
    first_shown_at = models.DateTimeField(auto_now_add=True)
    last_shown_at = models.DateTimeField(auto_now=True)
    shown_count = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('conversation', 'property')
        ordering = ['-last_shown_at']

    def __str__(self):
        return f'{self.conversation.session_id} → {self.property_id} (×{self.shown_count})'


class SystemPrompt(models.Model):
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Prompt'

    def __str__(self):
        return f'System Prompt (updated {self.updated_at})'
