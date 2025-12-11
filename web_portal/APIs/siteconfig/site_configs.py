from ...views import*

class SiteConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            config = SiteConfig.objects.first()
            if not config:
                return Response({
                    "status": "not_found",
                    "message": "No site configuration found.",
                    "data": {}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = SiteConfigSerializer(config, context={'request': request})
            return Response({
                "status": "success",
                "message": "Site configuration retrieved",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                "status": "error",
                "message": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            existing_config = SiteConfig.objects.first()

            serializer = SiteConfigSerializer(
                instance=existing_config,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if not serializer.is_valid():
                return Response({
                    "status": "invalid",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                saved_config = serializer.save(
                    created_by=request.user if not existing_config else existing_config.created_by,
                    updated_at=timezone.now()
                )

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='update',          
                    description="Your message here",
                    request_data=request.data,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                action_msg = "Site configuration updated successfully" if existing_config else "Site configuration created successfully"

                return Response({
                    "status": "success",
                    "message": action_msg,
                    "data": serializer.data
                }, status=status.HTTP_200_OK if existing_config else status.HTTP_201_CREATED)

        except Exception as exc:
            return Response({
                "status": "error",
                "message": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PublicSiteInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            current_host = request.META.get('HTTP_HOST', '')
            ALLOWED_DOMAINS = ['localhost:3000', '127.0.0.1:8000']  

            if current_host not in ALLOWED_DOMAINS:
                return Response({
                    "status": "forbidden",
                    "message": "Access denied from this domain"
                }, status=status.HTTP_403_FORBIDDEN)

            config = SiteConfig.objects.first()
            if not config:
                return Response({
                    "status": "empty",
                    "message": "Site information not configured yet",
                    "data": {}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = SiteConfigSerializer(
                config,
                context={
                    'request': request,
                    'exclude_fields': ['created_at', 'updated_at', 'created_by', 'config_id']
                }
            )

            return Response({
                "status": "success",
                "message": "Site information loaded",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                "status": "error",
                "message": "Server error occurred"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)