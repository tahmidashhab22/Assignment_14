from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User, BankAccount


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'phone', 'address']

    def create(self, validated_data):
        # create_user hashes the password
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if user is None:
            raise serializers.ValidationError("Wrong username or password.")
        data['user'] = user
        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'address']
        read_only_fields = ['id', 'username']


class BankAccountSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = BankAccount
        fields = ['id', 'owner', 'account_number', 'account_type', 'balance', 'is_active', 'created_at']
        # balance can only change by deposit/withdraw/transfer, not by the user directly
        read_only_fields = ['id', 'owner', 'account_number', 'balance', 'is_active', 'created_at']
