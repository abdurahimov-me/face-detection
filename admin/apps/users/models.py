import argon2
from django.db import models

from ..common.models import BaseModel


class User(BaseModel):
    email = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )
    phone = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )
    telegram_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True
    )
    is_seller = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return str(self.email or self.phone)


class TelegramUser(BaseModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    chat_id = models.BigIntegerField(unique=True)
    phone = models.CharField(max_length=100, unique=True, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'telegram_users'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Moderator(BaseModel):
    updated_at = None
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    password: str = models.CharField(max_length=100)
    is_admin = models.BooleanField(default=True)

    class Meta:
        db_table = 'moderators'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def check_hashing(self):
        if not self.password.startswith('$argon2id$v=19$m'):
            ph = argon2.PasswordHasher()
            self.password = ph.hash(self.password)

    def save(self, *args, **kwargs):
        self.check_hashing()
        super().save(*args, **kwargs)


class Profile(models.Model):
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_accepted = models.BooleanField()

    class Meta:
        db_table = 'profiles'


class Wallet(BaseModel):
    balance = models.DecimalField(max_digits=20, decimal_places=2)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'wallets'
