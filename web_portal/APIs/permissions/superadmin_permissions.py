from rest_framework.permissions import BasePermission
from web_portal.models import AdminAccount

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