from django.db import models


class UploadedDocument(models.Model):
    """A PDF associated with one browser-session workspace."""

    workspace_id = models.CharField(max_length=64, db_index=True)
    file = models.FileField(upload_to="rag_uploads/%Y/%m/%d/")
    original_name = models.CharField(max_length=255)
    pages_count = models.PositiveIntegerField(default=0)
    chunks_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.original_name


class ChatMessage(models.Model):
    """Chat history is isolated by the workspace's hashed session identifier."""

    USER = "user"
    ASSISTANT = "assistant"
    ROLE_CHOICES = [(USER, "User"), (ASSISTANT, "Assistant")]

    workspace_id = models.CharField(max_length=64, db_index=True)
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:70]}"
