from django.contrib import admin
from django.db.models import Count
from unfold import admin as unfold

from . import models


@admin.register(models.User)
class UserAdmin(unfold.ModelAdmin):
    class ProfileInline(unfold.StackedInline):
        model = models.Profile
        ordering_field = 'id'

    class WalletInline(unfold.StackedInline):
        model = models.Wallet
        ordering_field = 'id'

    list_display = ('id', 'email', 'phone', 'is_active', 'profile__last_name', 'profile__first_name', "telegram_id")
    search_fields = ('email', 'phone', 'telegram_id', 'profile__last_name', 'profile__first_name')
    inlines = (ProfileInline, WalletInline)
    list_editable = ("telegram_id", "phone")


@admin.register(models.TelegramUser)
class TelegramUserAdmin(unfold.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'phone', 'chat_id', 'created_at', "user")
    search_fields = ('phone', 'chat_id',)
    list_editable = ("chat_id", "phone")


@admin.register(models.Moderator)
class ModeratorAdmin(unfold.ModelAdmin):
    list_display = ('id', 'first_name', 'is_admin', 'get_count')

    def get_count(self, obj):
        return obj.count

    get_count.short_description = 'Count'

    def get_queryset(self, request):
        qs = super(ModeratorAdmin, self).get_queryset(request)

        qs = qs.annotate(
            count=Count('embeds__id'),
        )
        return qs
