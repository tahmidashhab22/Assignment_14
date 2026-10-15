import uuid

from django.db import models

from accounts.models import BankAccount


class Transaction(models.Model):
    DEPOSIT = 'deposit'
    WITHDRAW = 'withdraw'
    TRANSFER = 'transfer'
    TYPES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAW, 'Withdraw'),
        (TRANSFER, 'Transfer'),
    ]

    # unique reference for every transaction
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    transaction_type = models.CharField(max_length=10, choices=TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # the main account (for a transfer this is the sender)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    # only used for transfers (the receiver)
    to_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name='received_transactions',
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']  # newest first

    def __str__(self):
        return f"{self.transaction_type} {self.amount} ({self.reference})"
