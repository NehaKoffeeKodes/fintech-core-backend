from ...views import *

class AdminLoginDetailView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        try:
            current_admin = AdminAccount.objects.only('id', 'first_name', 'last_name').get(id=request.user.id)
            login_sessions = Superadminlogindetails.objects.filter(
                user=current_admin
            ).order_by('-login_time')

            sessions_list = []
            for session in login_sessions:
                sessions_list.append({
                    "id": session.id,
                    "admin_name": current_admin.get_full_name().strip() or "Unknown Admin",
                    "ip_address": session.ip_address or "N/A",
                    "browser_name": session.browser_name or "Unknown",
                    "device_info": session.device_info or "Unknown Device",
                    "login_time": session.login_time.isoformat() if session.login_time else "N/A"
                })

            return Response({
                "success": True,
                "message": "Login session history fetched successfully",
                "data": {
                    "total_sessions": len(sessions_list),
                    "sessions": sessions_list
                }
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                "success": False,
                "message": "Admin account not found or invalid session"
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "success": False,
                "message": "Failed to retrieve login history",
                "details": "Internal server error"  
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)