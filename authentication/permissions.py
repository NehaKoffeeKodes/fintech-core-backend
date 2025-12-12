from control_panel.models import PortalUser
from web_portal.models import AdminAccount
from rest_framework.permissions import BasePermission

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