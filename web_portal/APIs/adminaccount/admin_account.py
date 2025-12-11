from ...views import* 

class AdminAccountView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        try:
            admin_user = get_object_or_404(AdminAccount, pk=request.user.id, is_deleted=False)

            serializer = AdminAccountSerializer(admin_user, context={'request': request})

            response_payload = {
                "success": True,
                "message": "Admin profile retrieved successfully",
                "admin_data": serializer.data
            }

            return Response(response_payload, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                "success": False,
                "message": "Admin account not found or deactivated"
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as err:
            return Response({
                "success": False,
                "message": "An unexpected error occurred",
                "details": str(err) if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)