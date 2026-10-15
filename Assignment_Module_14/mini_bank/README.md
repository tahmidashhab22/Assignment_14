# Mini Bank Management System API

A simple banking REST API built with **Django REST Framework** for my assignment.
Customers can register, open bank accounts, deposit, withdraw, transfer money and see their transaction history. Admins can see all customers, accounts and transactions.

## Features

- Register / login (token authentication)
- View and update own profile
- Create accounts (Savings or Current) with a unique 12-digit account number
- Deposit, withdraw and transfer money
- Transaction history with pagination and filters (by type and by date range)
- Admin-only endpoints
- **Bonus:** date range filter, daily withdrawal limit, unit tests, downloadable CSV statement

## Tech used

- Python 3
- Django
- Django REST Framework (TokenAuthentication)
- SQLite database (default)

## Project structure

```
mini_bank/
├── config/          # project settings and main urls
├── accounts/        # User, BankAccount (auth, profile, accounts, admin views)
├── transactions/    # Transaction (deposit, withdraw, transfer, history, tests)
├── manage.py
├── requirements.txt
└── README.md
```

## Setup and installation

1. Clone the repo and go into the folder

   ```bash
   git clone <your-repo-url>
   cd mini_bank
   ```

2. Create and activate a virtual environment

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```

3. Install the requirements

   ```bash
   pip install -r requirements.txt
   ```

4. Run the database migrations

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. Create an admin user (needed to test the admin endpoints)

   ```bash
   python manage.py createsuperuser
   ```

6. Start the server

   ```bash
   python manage.py runserver
   ```

The API is now at `http://127.0.0.1:8000/api/`.

## Environment setup

No `.env` file is needed. The default settings use SQLite. The daily withdrawal limit can be changed in `config/settings.py`:

```python
DAILY_WITHDRAWAL_LIMIT = 50000
```

## How to use the API

All endpoints except register and login need this header:

```
Authorization: Token <your token>
```

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/register/` | Register a customer (returns a token) |
| POST | `/api/auth/login/` | Login (returns a token) |
| GET | `/api/profile/` | View own profile |
| PATCH | `/api/profile/` | Update own profile |
| GET | `/api/accounts/` | List own accounts |
| POST | `/api/accounts/` | Create an account |
| GET | `/api/accounts/<id>/` | View account details |
| GET | `/api/accounts/<id>/balance/` | Check balance |
| GET | `/api/accounts/<id>/statement/` | Download CSV statement (bonus) |
| POST | `/api/transactions/deposit/` | Deposit money |
| POST | `/api/transactions/withdraw/` | Withdraw money |
| POST | `/api/transactions/transfer/` | Transfer money |
| GET | `/api/transactions/` | Transaction history |
| GET | `/api/admin/customers/` | (admin) all customers |
| GET | `/api/admin/accounts/` | (admin) all accounts |
| GET | `/api/admin/transactions/` | (admin) all transactions |

### Example requests (JSON bodies)

**Register**  `POST /api/auth/register/`
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "alice1234",
  "first_name": "Alice",
  "phone": "01700000000"
}
```

**Login**  `POST /api/auth/login/`
```json
{ "username": "alice", "password": "alice1234" }
```

**Create account**  `POST /api/accounts/`
```json
{ "account_type": "savings" }
```
`account_type` is `savings` or `current`.

**Deposit / Withdraw**  `POST /api/transactions/deposit/` or `/withdraw/`
```json
{ "account_id": 1, "amount": "500.00" }
```

**Transfer**  `POST /api/transactions/transfer/`
```json
{
  "from_account_id": 1,
  "to_account_number": "123456789012",
  "amount": "250.00"
}
```

### Transaction history filters

```
GET /api/transactions/?type=deposit
GET /api/transactions/?type=transfer&page=2
GET /api/transactions/?start_date=2026-01-01&end_date=2026-12-31
```

`type` can be `deposit`, `withdraw` or `transfer`. Results are paginated (5 per page).

## Business rules and how they are handled

| Rule | How |
|------|-----|
| Unique account number | `unique=True` on the field, random number generated and checked |
| Balance never negative | Checked before every withdrawal and transfer |
| Amount must be positive | Serializer `min_value=0.01` rejects zero and negative |
| Only owner can use an account | Views look up the account with `owner=request.user` (others get 404) |
| Failed transaction changes nothing | Checks happen before saving, and everything runs in `transaction.atomic()` |
| Transfer is consistent | Both balances and the transaction record are saved inside one atomic block |
| Money fields | `DecimalField` is used everywhere |

## Status codes

- `200 OK` - successful GET / PATCH
- `201 Created` - account created, deposit / withdraw / transfer done
- `400 Bad Request` - invalid amount, insufficient balance, same-account transfer, limit exceeded
- `401 Unauthorized` - missing or wrong token
- `403 Forbidden` - normal user calling an admin endpoint
- `404 Not Found` - account not found (or belongs to someone else)

## Running the tests

```bash
python manage.py test
```

The tests cover registration, login, account privacy, deposit, withdrawal, transfer, history filtering, the daily limit and admin permissions.

## Testing with Postman

1. Register or login and copy the `token`.
2. In Postman, open the **Authorization** tab, choose type **API Key** (or add a header manually): key `Authorization`, value `Token <your token>`.
3. Send requests to the endpoints above with `Content-Type: application/json`.
