from django.db import models
from django.contrib.auth.models import User


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or "New Chat"


class Document(models.Model):
    session = models.ForeignKey(
        'ChatSession',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    name = models.CharField(max_length=255, null=True, blank=True)
    size = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        session_info = f"[Session: {self.session_id}]" if self.session_id else "[No session]"
        return f"{self.name or 'Document'} {session_info}"


class ChatMessage(models.Model):
    session = models.ForeignKey(
        ChatSession,
        related_name='messages',
        on_delete=models.CASCADE
    )
    is_user = models.BooleanField(default=True)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        role = "User" if self.is_user else "Bot"
        preview = self.text[:60].replace('\n', ' ')
        return f"[{role}] {preview}"