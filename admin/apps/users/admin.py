from django.contrib import admin
from unfold import admin as unfold

from . import models


@admin.register(models.User)
class UserAdmin(unfold.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "user_id", "tenant")
