from ...views import*

logger = logging.getLogger(__name__)


class AdminBlockView(APIView):
    """
    SuperAdmin use karta hai kisi client ko block/unblock karne ke liye
    Ye toggle karta hai — block hai to unblock, unblock hai to block
    """
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def patch(self, request):
        client_admin_id = request.data.get('client_admin_id')

        if not client_admin_id:
            return Response({
                'success': False,
                'message': 'client_admin_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            client_admin = Admin.objects.select_related().get(
                client_admin_id=client_admin_id
            )
            
            if client_admin.status == 'PENDING':
                return Response({
                    'success': False,
                    'message': 'Cannot modify access: Client approval is still pending'
                }, status=status.HTTP_409_CONFLICT)

            switch_to_database(client_admin.database_alias)
            main_portal_user = PortalUser.objects.using(client_admin.database_alias).get(id=1)

            if client_admin.is_deleted:
                client_admin.is_deleted = False
                client_admin.is_active = True
                client_admin.status = 'ACTIVE'
                client_admin.save()

                main_portal_user.is_deleted = False
                main_portal_user.is_active = True
                main_portal_user.account_status = 'ACTIVE'
                main_portal_user.save(using=client_admin.database_alias)

                return Response({
                    'success': True,
                    'message': 'Client access restored successfully',
                    'action': 'unblocked'
                }, status=status.HTTP_200_OK)

            else:
                client_admin.is_deleted = True
                client_admin.is_active = False
                client_admin.status = 'BLOCKED'
                client_admin.save()

                main_portal_user.is_deleted = True
                main_portal_user.is_active = False
                main_portal_user.account_status = 'BLOCKED'
                main_portal_user.save(using=client_admin.database_alias)

                return Response({
                    'success': True,
                    'message': 'Client has been blocked successfully',
                    'action': 'blocked'
                }, status=status.HTTP_200_OK)

        except Admin.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Client record not found'
            }, status=status.HTTP_404_NOT_FOUND)

        except PortalUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Main portal user not found in client database'
            }, status=status.HTTP_424_FAILED_DEPENDENCY)

        except Exception as err:
            logger.error(f"Client access toggle failed for ID {client_admin_id}: {str(err)}")
            return Response({
                'success': False,
                'message': 'Operation failed due to server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)