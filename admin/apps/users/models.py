from django.db import models

from ..common.models import BaseModel


class User(BaseModel):
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    face = models.CharField(max_length=1000, null=True, blank=True)
    user_id = models.BigIntegerField()
    tenant = models.BigIntegerField()

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.user_id} - {self.tenant}"
