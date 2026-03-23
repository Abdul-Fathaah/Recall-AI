from django.contrib import admin
from .models import Document, ChatSession, ChatMessage


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'session_user', 'session_title', 'size', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('name', 'session__title', 'session__user__username')
    readonly_fields = ('uploaded_at',)

    def session_user(self, obj):
        return obj.session.user.username if obj.session else '—'
    session_user.short_description = 'User'

    def session_title(self, obj):
        return obj.session.title if obj.session else '—'
    session_title.short_description = 'Session'


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('timestamp',)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'document_count')
    list_filter = ('created_at',)
    search_fields = ('title', 'user__username')
    inlines = [ChatMessageInline]

    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = 'Docs'