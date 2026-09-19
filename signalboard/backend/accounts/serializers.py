import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


def clean_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if digits and not (8 <= len(digits) <= 15):
        raise serializers.ValidationError("Enter the number with country code, e.g. 919876543210.")
    return digits


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source="profile.phone", read_only=True)
    push_subscribed = serializers.SerializerMethodField()
    last_seen = serializers.DateTimeField(source="profile.last_seen", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "is_staff", "push_subscribed", "last_seen", "date_joined"]

    def get_name(self, obj):
        return obj.get_full_name() or obj.email.split("@")[0]

    def get_push_subscribed(self, obj):
        return bool(getattr(obj, "profile", None) and obj.profile.push_subscription_id)


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("An account with this email already exists. Log in instead.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_phone(self, value):
        return clean_phone(value)

    def create(self, data):
        first, _, last = data["name"].strip().partition(" ")
        user = User.objects.create_user(
            username=data["email"], email=data["email"], password=data["password"],
            first_name=first, last_name=last,
        )
        user.profile.phone = data.get("phone", "")
        user.profile.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_phone(self, value):
        return clean_phone(value)
