from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, BankAccount
from .serializers import (
    RegisterSerializer, LoginSerializer, ProfileSerializer, BankAccountSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'user': serializer.data, 'token': token.key}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET and PATCH the profile of the logged in user only."""
    serializer_class = ProfileSerializer
    http_method_names = ['get', 'patch']

    def get_object(self):
        return self.request.user


class AccountListCreateView(generics.ListCreateAPIView):
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        # only my own accounts
        return BankAccount.objects.filter(owner=self.request.user).order_by('id')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class AccountDetailView(generics.RetrieveAPIView):
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        # other people's accounts are not in this queryset, so they give 404
        return BankAccount.objects.filter(owner=self.request.user)


class AccountBalanceView(APIView):
    def get(self, request, pk):
        account = get_object_or_404(BankAccount, pk=pk, owner=request.user)
        return Response({'account_number': account.account_number, 'balance': str(account.balance)})


# ---------- Admin views ----------

class AdminCustomerListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('id')
    serializer_class = ProfileSerializer
    permission_classes = [IsAdminUser]


class AdminAccountListView(generics.ListAPIView):
    queryset = BankAccount.objects.all().order_by('id')
    serializer_class = BankAccountSerializer
    permission_classes = [IsAdminUser]
