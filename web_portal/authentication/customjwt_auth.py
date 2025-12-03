from ..views import*
from rest_framework_simplejwt.authentication import JWTAuthentication


def generate_jwt_token(user, expiry_minutes=None):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = "SUPERADMIN"
    refresh["username"] = user.username
    refresh["user_id"] = user.id
    if expiry_minutes:
        refresh.access_token.set_exp(lifetime=timedelta(minutes=expiry_minutes))

    return str(refresh.access_token)


class SuperAdminOnlyPermission:
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and isinstance(user, AdminAccount)
            and getattr(user, "has_changed_initial_password", False)
            and not getattr(user, "is_deleted", False)
        )


class SecureJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user_id = validated_token.get("user_id")

            if not user_id:
                raise exceptions.AuthenticationFailed("Token missing user_id")

            user = AdminAccount.objects.only("id", "username", "is_deleted").get(id=user_id, is_deleted=False)
            return (user, validated_token)

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token")
        except AdminAccount.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found or deactivated")
        except Exception as e:
            raise exceptions.AuthenticationFailed("Authentication failed")