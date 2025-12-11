import jwt
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken          
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from web_portal.models import AdminAccount  
from rest_framework.permissions import BasePermission
from web_portal.models import *
from control_panel.models import*

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
            
        if not isinstance(user, AdminAccount):
            return False

        if user.is_superuser and user.is_staff:
            return True

        return (
            user.is_superuser
            and user.is_staff
            and user.is_active
            and not user.is_deleted
            and user.has_changed_initial_password   
        )
        


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            member = PortalUser.objects.only('member_type').get(id=request.user.id)
            return member.member_type == 'SUPER_ADMIN'
        except PortalUser.DoesNotExist:
            return False

# def generate_jwt_token(user, expiry_minutes=None):
#     refresh = RefreshToken.for_user(user)       
#     refresh["role"] = "SUPERADMIN"
#     refresh["username"] = user.username
#     refresh["user_id"] = user.id
    
#     if expiry_minutes:
#         refresh.access_token.set_exp(lifetime=timedelta(minutes=expiry_minutes))

#     return str(refresh.access_token)


def generate_jwt_token(user, access_token_lifetime_minutes=None):
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
    refresh_token["username"] = getattr(user, 'username', 'unknown')
    refresh_token["user_id"] = user.id
    refresh_token["full_name"] = user.get_full_name() if hasattr(user, 'get_full_name') else ""

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
        