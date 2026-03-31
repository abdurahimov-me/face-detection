from django.db import models

from ..common.models import BaseModel


class Conversation(BaseModel):
    deleted = models.BooleanField(default=False)
    uuid = models.UUIDField()
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        "users.User",
        related_name="conversations",
        on_delete=models.PROTECT,
    )

    class Meta:
        db_table = 'conversations'
