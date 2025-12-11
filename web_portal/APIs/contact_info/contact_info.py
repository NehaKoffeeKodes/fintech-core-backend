from ...views import*

class ContactInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            info = ContactInfo.objects.filter(is_deleted=False).first()
            if not info:
                return Response({
                    "status": "fail",
                    "message": "Contact information not configured yet.",
                    "data": {}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = ContactInfoSerializer(info, context={'request': request})
            return Response({
                "status": "success",
                "message": "Contact information retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "Something went wrong. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            existing = ContactInfo.objects.filter(is_deleted=False).first()

            serializer = ContactInfoSerializer(
                instance=existing,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if not serializer.is_valid():
                return Response({
                    "status": "fail",
                    "message": "Validation failed.",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                instance = serializer.save()

                action = "update" if existing else "create"
                desc = f"Contact information {'updated' if existing else 'created'}"

                AdminActivityLog.objects.create(
                    user=request.user,                    
                    action=action.upper(),                
                    description=desc,                     
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_data=request.data
                )

                return Response({
                    "status": "success",
                    "message": "Contact information saved successfully.",
                    "data": serializer.data
                }, status=status.HTTP_200_OK if existing else status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "Failed to save Contact information."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)