from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User, BankAccount
from .models import Transaction


class BankTests(APITestCase):
    def setUp(self):
        # two customers, each with one account
        self.alice = User.objects.create_user('alice', 'alice@test.com', 'pass1234')
        self.bob = User.objects.create_user('bob', 'bob@test.com', 'pass1234')
        self.alice_acc = BankAccount.objects.create(owner=self.alice, account_type='savings', balance=1000)
        self.bob_acc = BankAccount.objects.create(owner=self.bob, account_type='current', balance=500)

        self.client.force_authenticate(user=self.alice)

    # ---------- auth ----------
    def test_private_endpoint_needs_login(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/accounts/')
        self.assertEqual(response.status_code, 401)

    def test_register_and_login(self):
        self.client.force_authenticate(user=None)
        data = {'username': 'carl', 'email': 'carl@test.com', 'password': 'secret123'}
        self.assertEqual(self.client.post('/api/auth/register/', data).status_code, 201)
        response = self.client.post('/api/auth/login/', {'username': 'carl', 'password': 'secret123'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

    # ---------- accounts ----------
    def test_create_account_gets_unique_number(self):
        response = self.client.post('/api/accounts/', {'account_type': 'current'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['account_number']), 12)
        self.assertEqual(Decimal(response.data['balance']), 0)

    def test_cannot_see_other_customers_account(self):
        response = self.client.get(f'/api/accounts/{self.bob_acc.id}/')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/api/accounts/{self.bob_acc.id}/balance/')
        self.assertEqual(response.status_code, 404)

    # ---------- deposit ----------
    def test_deposit(self):
        response = self.client.post('/api/transactions/deposit/', {'account_id': self.alice_acc.id, 'amount': '200.50'})
        self.assertEqual(response.status_code, 201)
        self.alice_acc.refresh_from_db()
        self.assertEqual(self.alice_acc.balance, Decimal('1200.50'))
        self.assertEqual(Transaction.objects.filter(transaction_type='deposit').count(), 1)

    def test_deposit_zero_or_negative_rejected(self):
        for amount in ['0', '-50']:
            response = self.client.post('/api/transactions/deposit/', {'account_id': self.alice_acc.id, 'amount': amount})
            self.assertEqual(response.status_code, 400)
        self.alice_acc.refresh_from_db()
        self.assertEqual(self.alice_acc.balance, 1000)

    def test_cannot_deposit_to_other_customers_account(self):
        response = self.client.post('/api/transactions/deposit/', {'account_id': self.bob_acc.id, 'amount': '100'})
        self.assertEqual(response.status_code, 404)
        self.bob_acc.refresh_from_db()
        self.assertEqual(self.bob_acc.balance, 500)

    # ---------- withdraw ----------
    def test_withdraw(self):
        response = self.client.post('/api/transactions/withdraw/', {'account_id': self.alice_acc.id, 'amount': '300'})
        self.assertEqual(response.status_code, 201)
        self.alice_acc.refresh_from_db()
        self.assertEqual(self.alice_acc.balance, 700)

    def test_withdraw_insufficient_balance(self):
        response = self.client.post('/api/transactions/withdraw/', {'account_id': self.alice_acc.id, 'amount': '5000'})
        self.assertEqual(response.status_code, 400)
        self.alice_acc.refresh_from_db()
        self.assertEqual(self.alice_acc.balance, 1000)  # unchanged
        self.assertEqual(Transaction.objects.count(), 0)  # nothing recorded

    def test_daily_withdrawal_limit(self):
        self.alice_acc.balance = 200000
        self.alice_acc.save()
        response = self.client.post('/api/transactions/withdraw/', {'account_id': self.alice_acc.id, 'amount': '60000'})
        self.assertEqual(response.status_code, 400)

    # ---------- transfer ----------
    def test_transfer(self):
        response = self.client.post('/api/transactions/transfer/', {
            'from_account_id': self.alice_acc.id,
            'to_account_number': self.bob_acc.account_number,
            'amount': '250',
        })
        self.assertEqual(response.status_code, 201)
        self.alice_acc.refresh_from_db()
        self.bob_acc.refresh_from_db()
        self.assertEqual(self.alice_acc.balance, 750)
        self.assertEqual(self.bob_acc.balance, 750)
        self.assertEqual(Transaction.objects.filter(transaction_type='transfer').count(), 1)

    def test_transfer_to_same_account_rejected(self):
        response = self.client.post('/api/transactions/transfer/', {
            'from_account_id': self.alice_acc.id,
            'to_account_number': self.alice_acc.account_number,
            'amount': '10',
        })
        self.assertEqual(response.status_code, 400)

    def test_transfer_insufficient_funds_changes_nothing(self):
        response = self.client.post('/api/transactions/transfer/', {
            'from_account_id': self.alice_acc.id,
            'to_account_number': self.bob_acc.account_number,
            'amount': '99999',
        })
        self.assertEqual(response.status_code, 400)
        self.alice_acc.refresh_from_db()
        self.bob_acc.refresh_from_db()
        self.assertEqual(self.alice_acc.balance, 1000)
        self.assertEqual(self.bob_acc.balance, 500)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_cannot_transfer_from_other_customers_account(self):
        response = self.client.post('/api/transactions/transfer/', {
            'from_account_id': self.bob_acc.id,
            'to_account_number': self.alice_acc.account_number,
            'amount': '10',
        })
        self.assertEqual(response.status_code, 404)

    # ---------- history ----------
    def test_history_only_shows_my_transactions_and_filters(self):
        Transaction.objects.create(transaction_type='deposit', amount=10, account=self.alice_acc)
        Transaction.objects.create(transaction_type='withdraw', amount=5, account=self.alice_acc)
        Transaction.objects.create(transaction_type='deposit', amount=99, account=self.bob_acc)  # not mine

        response = self.client.get('/api/transactions/')
        self.assertEqual(response.data['count'], 2)

        response = self.client.get('/api/transactions/?type=deposit')
        self.assertEqual(response.data['count'], 1)

    # ---------- admin ----------
    def test_normal_user_cannot_use_admin_endpoints(self):
        for url in ['/api/admin/customers/', '/api/admin/accounts/', '/api/admin/transactions/']:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_can_see_everything(self):
        admin = User.objects.create_superuser('boss', 'boss@test.com', 'pass1234')
        self.client.force_authenticate(user=admin)
        self.assertEqual(self.client.get('/api/admin/customers/').data['count'], 3)
        self.assertEqual(self.client.get('/api/admin/accounts/').data['count'], 2)
        self.assertEqual(self.client.get('/api/admin/transactions/').status_code, 200)
