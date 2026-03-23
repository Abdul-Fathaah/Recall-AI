from django.contrib import admin
from .models import Document, ChatSession, ChatMessage

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'size', 'uploaded_at')
    list_filter = ('session__user',)
    search_fields = ('name', 'session__title', 'session__user__username')
    readonly_fields = ('uploaded_at',)

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('timestamp',)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'user__username')
    inlines = [ChatMessageInline]