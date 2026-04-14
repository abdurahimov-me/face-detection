from django.contrib import admin
from unfold import admin as unfold

from . import models


@admin.register(models.Conversation)
class ConversationAdmin(unfold.ModelAdmin):
    list_display = ('id', 'uuid', 'name', 'owner')


@admin.register(models.Member)
class MemberAdmin(unfold.ModelAdmin):
    list_display = ('user', 'conversation', 'joined_at', 'role')


@admin.register(models.Message)
class MessageAdmin(unfold.ModelAdmin):
    list_display = ("id", 'sender', 'conversation', 'text', 'created_at')


@admin.register(models.MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ('message_id', 'user_id', 'read_at',)