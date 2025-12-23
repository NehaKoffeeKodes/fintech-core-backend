from asyncio import exceptions
from admin_hub.models import*
from web_portal.models import AdminAccount
from rest_framework.permissions import BasePermission
from admin_hub.models import*

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
        
        



class IsDistributor(BasePermission):
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            app_user = PortalUser.objects.only('role').get(id=request.user.id)
            
            if app_user.role.lower() != 'wholesaler':
                return False

            token = request.auth
            if isinstance(token, bytes):
                token = token.decode('utf-8')
                
            session_exists = UserLoginSession.objects.filter(
                user=app_user,
                access_token=token,
                is_logged_out=False,
                logout_at__isnull=True,
                last_active_at__gt=timezone.now() - timezone.timedelta(hours=24)  
            ).exists()

            if not session_exists:
                raise exceptions.AuthenticationFailed(
                    detail="Your session has expired. Please login again.",
                    code="expired_session"
                )

            return True

        except PortalUser.DoesNotExist:
            return False
        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
            return False


class IsRetailer(BasePermission):
    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False

        try:
            current_user = PortalUser.objects.only('role').get(pk=request.user.pk)
            
            if current_user.role.lower() != 'dealer':
                return False

            jwt_token = request.auth
            if hasattr(jwt_token, 'decode'):
                jwt_token = jwt_token.decode('utf-8') if isinstance(jwt_token, bytes) else str(jwt_token)

            is_valid_session = UserLoginSession.objects.filter(
                user=current_user,
                access_token=jwt_token,
                is_logged_out=False,
                logout_at__isnull=True,
                last_active_at__gte=timezone.now() - timezone.timedelta(days=7) 
            ).exists()

            if not is_valid_session:
                raise exceptions.AuthenticationFailed(
                    {"detail": "Session no longer valid. Re-login required.", "code": "session_invalid"},
                    code="session_invalid"
                )

            return True

        except PortalUser.DoesNotExist:
            return False
        except exceptions.AuthenticationFailed:
            raise
        except Exception:
            return False