from django.contrib import admin
from unfold import admin as unfold

from . import models


@admin.register(models.Category)
class CategoryAdmin(unfold.ModelAdmin):
    list_display = ('id', 'name', 'order', 'set_home')
    list_editable = ('set_home', 'order')


@admin.register(models.Offer)
class OfferAdmin(unfold.ModelAdmin):
    list_display = ('id', 'user', 'text', 'response',)
