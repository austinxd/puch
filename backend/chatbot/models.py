import uuid
from django.db import models


class ChatConversation(models.Model):
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return str(self.session_id)


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

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
