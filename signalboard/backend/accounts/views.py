from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from notifications.dispatcher import fire_trigger

from .serializers import LoginSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


def _auth_payload(user):
    token, _ = Token.objects.get_or_create(user=user)
    return {"token": token.key, "user": UserSerializer(user).data}


def _request_meta(request):
    ua = request.META.get("HTTP_USER_AGENT", "")
    return {"device": ua[:120]}


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = s.save()
    user.last_login = timezone.now()  # registering signs the user in
    user.save(update_fields=["last_login"])
    return Response(_auth_payload(user), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    s = LoginSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    email = s.validated_data["email"].lower().strip()
    user = authenticate(request, username=email, password=s.validated_data["password"])
    if not user:
        return Response({"detail": "Email or password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    user.profile.last_seen = timezone.now()
    user.profile.save(update_fields=["last_seen"])
    fire_trigger("login", user=user, context=_request_meta(request))
    return Response(_auth_payload(user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    user = request.user
    fire_trigger("logout", user=user, context=_request_meta(request))
    Token.objects.filter(user=user).delete()
    return Response({"detail": "Logged out."})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    if request.method == "PATCH":
        s = ProfileUpdateSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        if "name" in s.validated_data:
            first, _, last = s.validated_data["name"].strip().partition(" ")
            user.first_name, user.last_name = first, last
            user.save(update_fields=["first_name", "last_name"])
        if "phone" in s.validated_data:
            user.profile.phone = s.validated_data["phone"]
            user.profile.save(update_fields=["phone", "updated_at"])
    return Response(UserSerializer(user).data)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def push_subscription(request):
    """The browser calls this after OneSignal gives it a subscription id."""
    profile = request.user.profile
    if request.method == "DELETE":
        profile.push_subscription_id = ""
    else:
        sub_id = str(request.data.get("subscription_id", "")).strip()
        if not sub_id:
            return Response({"detail": "subscription_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        profile.push_subscription_id = sub_id[:100]
    profile.save(update_fields=["push_subscription_id", "updated_at"])
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset(request):
    """Fires the password_reset trigger. Always answers the same way so the
    endpoint can't be used to check which emails have accounts."""
    email = str(request.data.get("email", "")).lower().strip()
    user = User.objects.filter(username=email).first()
    if user:
        from django.conf import settings

        fire_trigger("password_reset", user=user, context={
            "reset_link": f"{settings.FRONTEND_URL}/login?reset=demo",
        })
    return Response({"detail": "If that email has an account, a reset message is on its way."})