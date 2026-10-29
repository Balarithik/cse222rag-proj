from django.contrib import admin

from .models import ChatMessage, UploadedDocument


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "workspace_id", "pages_count", "chunks_count", "created_at")
    search_fields = ("original_name", "workspace_id")
    readonly_fields = ("workspace_id", "original_name", "pages_count", "chunks_count", "created_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("role", "workspace_id", "created_at")
    search_fields = ("content", "workspace_id")
    readonly_fields = ("workspace_id", "role", "content", "sources", "created_at")
