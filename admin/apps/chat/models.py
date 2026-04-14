from django.db import models

from ..common.models import BaseModel


class Conversation(BaseModel):
    deleted = models.BooleanField(default=False)
    uuid = models.UUIDField()
    name = models.CharField(max_length=255)
    type = models.SmallIntegerField()
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


class Message(BaseModel):
    deleted = models.BooleanField(default=False)
    sender = models.ForeignKey("users.User", on_delete=models.PROTECT)
    conversation = models.ForeignKey("Conversation", on_delete=models.PROTECT)
    text = models.TextField()
    reply = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    type = models.SmallIntegerField()

    class Meta:
        db_table = 'messages'


class MessageRead(models.Model):
    id = None
    message = models.ForeignKey(
        "Message",
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_reads"
        unique_together = ("message", "user")
