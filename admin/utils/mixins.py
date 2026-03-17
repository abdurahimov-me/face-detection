from django.db import models

from admin.utils.choices import CheckingConditions


class DeletedMixin(models.Model):
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class ConditionMixin(models.Model):
    condition = models.CharField(
        choices=CheckingConditions.choices,
        max_length=100,
        verbose_name='Condition',
        default=CheckingConditions.WAITING,
    )

    class Meta:
        abstract = True
