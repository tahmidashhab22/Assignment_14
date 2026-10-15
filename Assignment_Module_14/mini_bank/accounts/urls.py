from django.urls import path

from . import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view()),
    path('auth/login/', views.LoginView.as_view()),
    path('profile/', views.ProfileView.as_view()),
    path('accounts/', views.AccountListCreateView.as_view()),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view()),
    path('accounts/<int:pk>/balance/', views.AccountBalanceView.as_view()),

    # admin only
    path('admin/customers/', views.AdminCustomerListView.as_view()),
    path('admin/accounts/', views.AdminAccountListView.as_view()),
]
