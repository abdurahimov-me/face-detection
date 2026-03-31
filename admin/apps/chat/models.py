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

    def __str__(self):
        return self.name


class Member(BaseModel):
    deleted = models.BooleanField(default=False)
    user = models.ForeignKey("users.User", on_delete=models.PROTECT)
    conversation = models.ForeignKey("Conversation", on_delete=models.PROTECT)
    role = models.SmallIntegerField()
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'members'
