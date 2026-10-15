import random

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Customer. I extend Django's user so I get login/password for free."""
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.username


def make_account_number():
    """Makes a random 12 digit number that is not used by another account."""
    while True:
        number = str(random.randint(10**11, 10**12 - 1))
        if not BankAccount.objects.filter(account_number=number).exists():
            return number


class BankAccount(models.Model):
    SAVINGS = 'savings'
    CURRENT = 'current'
    ACCOUNT_TYPES = [
        (SAVINGS, 'Savings'),
        (CURRENT, 'Current'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=12, unique=True, default=make_account_number, editable=False)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)  # status of the account
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_number} ({self.owner.username})"
