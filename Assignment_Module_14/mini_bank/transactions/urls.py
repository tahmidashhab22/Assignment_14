from django.urls import path

from . import views

urlpatterns = [
    path('transactions/', views.TransactionListView.as_view()),
    path('transactions/deposit/', views.DepositView.as_view()),
    path('transactions/withdraw/', views.WithdrawView.as_view()),
    path('transactions/transfer/', views.TransferView.as_view()),
    path('accounts/<int:pk>/statement/', views.AccountStatementView.as_view()),

    # admin only
    path('admin/transactions/', views.AdminTransactionListView.as_view()),
]
