from ...views import *

class AdminLoginDetailView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        try:
            current_admin = AdminAccount.objects.select_related().get(id=request.user.id)
            
            sessions = Superadminlogindetails.objects.filter(
                staff=current_admin
            ).order_by('-login_timestamp')
            
            serialized_data = SuperAdminLoginDetailSerializer(sessions, many=True)

            enriched_data = []
            for item in serialized_data.data:
                try:
                    staff_obj = AdminAccount.objects.only('full_name').get(id=item['staff'])
                    item['staff'] = staff_obj.full_name.strip() or "Unknown User"
                except AdminAccount.DoesNotExist:
                    item['staff'] = "Deleted User"
                enriched_data.append(item)

            return Response({
                'success': True,
                'message': 'Session history retrieved successfully',
                'data': {
                    'sessions': enriched_data
                }
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Admin profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as unexpected_error:
            return Response({
                'success': False,
                'message': 'Something went wrong on server',
                'error': str(unexpected_error)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)