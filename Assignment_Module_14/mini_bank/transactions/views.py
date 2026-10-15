import csv
from decimal import Decimal

from django.conf import settings
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import BankAccount
from .models import Transaction
from .serializers import (
    DepositWithdrawSerializer, TransferSerializer, TransactionSerializer,
)


def error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({'error': message}, status=code)


class DepositView(APIView):
    def post(self, request):
        serializer = DepositWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        # atomic = if something fails, nothing is saved
        with db_transaction.atomic():
            # only the owner can use the account
            account = get_object_or_404(
                BankAccount.objects.select_for_update(),
                pk=serializer.validated_data['account_id'], owner=request.user,
            )
            if not account.is_active:
                return error('This account is not active.')

            account.balance += amount
            account.save()
            txn = Transaction.objects.create(
                transaction_type=Transaction.DEPOSIT, amount=amount, account=account,
            )

        return Response(
            {'message': 'Deposit successful.', 'new_balance': str(account.balance),
             'transaction': TransactionSerializer(txn).data},
            status=status.HTTP_201_CREATED,
        )


class WithdrawView(APIView):
    def post(self, request):
        serializer = DepositWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        with db_transaction.atomic():
            account = get_object_or_404(
                BankAccount.objects.select_for_update(),
                pk=serializer.validated_data['account_id'], owner=request.user,
            )
            if not account.is_active:
                return error('This account is not active.')

            if account.balance < amount:
                return error('Insufficient balance.')

            # bonus: daily withdrawal limit
            today = timezone.localdate()
            withdrawn_today = Transaction.objects.filter(
                account=account, transaction_type=Transaction.WITHDRAW,
                created_at__date=today,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            limit = Decimal(settings.DAILY_WITHDRAWAL_LIMIT)
            if withdrawn_today + amount > limit:
                return error(f'Daily withdrawal limit of {limit} exceeded.')

            account.balance -= amount
            account.save()
            txn = Transaction.objects.create(
                transaction_type=Transaction.WITHDRAW, amount=amount, account=account,
            )

        return Response(
            {'message': 'Withdrawal successful.', 'new_balance': str(account.balance),
             'transaction': TransactionSerializer(txn).data},
            status=status.HTTP_201_CREATED,
        )


class TransferView(APIView):
    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        amount = data['amount']

        # sender must be my account
        sender_check = get_object_or_404(BankAccount, pk=data['from_account_id'], owner=request.user)

        receiver_check = BankAccount.objects.filter(account_number=data['to_account_number']).first()
        if receiver_check is None:
            return error('Receiver account not found.', status.HTTP_404_NOT_FOUND)

        if sender_check.id == receiver_check.id:
            return error('You cannot transfer money to the same account.')

        with db_transaction.atomic():
            # lock both rows. Always lock the smaller id first so two transfers
            # in opposite directions cannot block each other forever.
            ids = sorted([sender_check.id, receiver_check.id])
            locked = {a.id: a for a in BankAccount.objects.select_for_update().filter(id__in=ids).order_by('id')}
            sender = locked[sender_check.id]
            receiver = locked[receiver_check.id]

            if not sender.is_active or not receiver.is_active:
                return error('Both accounts must be active.')

            if sender.balance < amount:
                return error('Insufficient balance.')

            sender.balance -= amount
            receiver.balance += amount
            sender.save()
            receiver.save()

            txn = Transaction.objects.create(
                transaction_type=Transaction.TRANSFER, amount=amount,
                account=sender, to_account=receiver,
            )

        return Response(
            {'message': 'Transfer successful.', 'new_balance': str(sender.balance),
             'transaction': TransactionSerializer(txn).data},
            status=status.HTTP_201_CREATED,
        )


class TransactionListView(generics.ListAPIView):
    """History of my accounts. Filters: ?type=deposit&start_date=2026-01-01&end_date=2026-12-31"""
    serializer_class = TransactionSerializer

    def get_queryset(self):
        user = self.request.user
        # transactions where I am the sender/owner OR the receiver of a transfer
        queryset = Transaction.objects.filter(
            Q(account__owner=user) | Q(to_account__owner=user)
        ).select_related('account', 'to_account')

        txn_type = self.request.query_params.get('type')
        if txn_type:
            queryset = queryset.filter(transaction_type=txn_type)

        # bonus: date range filter
        start = parse_date(self.request.query_params.get('start_date', ''))
        end = parse_date(self.request.query_params.get('end_date', ''))
        if start:
            queryset = queryset.filter(created_at__date__gte=start)
        if end:
            queryset = queryset.filter(created_at__date__lte=end)

        return queryset


class AdminTransactionListView(generics.ListAPIView):
    queryset = Transaction.objects.all().select_related('account', 'to_account')
    serializer_class = TransactionSerializer
    permission_classes = [IsAdminUser]


class AccountStatementView(APIView):
    """Bonus: download the statement of one account as a CSV file."""

    def get(self, request, pk):
        account = get_object_or_404(BankAccount, pk=pk, owner=request.user)
        transactions = Transaction.objects.filter(
            Q(account=account) | Q(to_account=account)
        ).order_by('created_at')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="statement_{account.account_number}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Reference', 'Type', 'Amount', 'From account', 'To account'])
        for t in transactions:
            writer.writerow([
                t.created_at.strftime('%Y-%m-%d %H:%M:%S'), t.reference, t.transaction_type, t.amount,
                t.account.account_number, t.to_account.account_number if t.to_account else '',
            ])
        return response
