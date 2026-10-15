from decimal import Decimal

from rest_framework import serializers

from .models import Transaction

# smallest money amount allowed (so zero and negative are rejected)
MIN_AMOUNT = Decimal('0.01')


class DepositWithdrawSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=MIN_AMOUNT,
        error_messages={'min_value': 'Amount must be greater than zero.'},
    )


class TransferSerializer(serializers.Serializer):
    from_account_id = serializers.IntegerField()
    to_account_number = serializers.CharField(max_length=12)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=MIN_AMOUNT,
        error_messages={'min_value': 'Amount must be greater than zero.'},
    )


class TransactionSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    to_account_number = serializers.CharField(source='to_account.account_number', read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = [
            'id', 'reference', 'transaction_type', 'amount',
            'account', 'account_number', 'to_account', 'to_account_number', 'created_at',
        ]
