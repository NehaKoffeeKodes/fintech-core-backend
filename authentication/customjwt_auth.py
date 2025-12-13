import jwt
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken          
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from web_portal.models import *
from control_panel.models import*


def generate_jwt_token(user, expiry_minutes=None):
    refresh = RefreshToken.for_user(user)       
    refresh["role"] = "SUPERADMIN"
    refresh["username"] = user.username
    refresh["user_id"] = user.id
    
    if expiry_minutes:
        refresh.access_token.set_exp(lifetime=timedelta(minutes=expiry_minutes))

    return str(refresh.access_token)


def create_jwt_token(user, access_token_lifetime_minutes=None, db_name=None):
    try:
        role_map = {
            "ADMIN": "ADMIN",
            "DISTRIBUTOR": "DISTRIBUTOR",
            "RETAILER": "RETAILER"
        }
        user_role = role_map.get(getattr(user, 'pu_role', ''), "SUPERADMIN")
    except Exception:
        user_role = "SUPERADMIN"

    refresh_token = RefreshToken.for_user(user)
    refresh_token["role"] = user_role
    refresh_token["username"] = getattr(user, 'email_address', 'unknown')
    refresh_token["user_id"] = user.pk
    refresh_token["full_name"] = getattr(user, 'full_name', '')

    # ADD THIS: Include db_name in payload
    if db_name:
        refresh_token["db_name"] = db_name

    if access_token_lifetime_minutes:
        refresh_token.access_token.set_exp(
            lifetime=timedelta(minutes=access_token_lifetime_minutes)
        )

    return str(refresh_token.access_token)



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

            user = AdminAccount.objects.only("id", "username", "is_deleted").get(
                id=user_id, is_deleted=False
            )
            return (user, validated_token)

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token")
        except AdminAccount.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found or deactivated")
        except Exception:
            raise exceptions.AuthenticationFailed("Authentication failed")
        