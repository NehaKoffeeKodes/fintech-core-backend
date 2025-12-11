from ...views import*

class AboutusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            overview = Aboutus.objects.first()
            if not overview:
                return Response({
                    'status': 'fail',
                    'message': 'Company overview not configured yet.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = AboutusSerializer(overview, context={'request': request})
            return Response({
                'status': 'success',
                'message': 'Company overview retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            existing = Aboutus.objects.first()
            if existing:
                return Response({
                    'status': 'fail',
                    'message': 'Company overview already exists. Use update endpoint.',
                    'action': 'use_put_method'
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = AboutusSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    instance = serializer.save(created_by=request.user)

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='create',
                        description='Created company overview section',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_data=request.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Company overview created successfully.',
                        'data': serializer.data
                    }, status=status.HTTP_201_CREATED)

            return Response({
                'status': 'fail',
                'message': 'Invalid data provided.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            overview = Aboutus.objects.first()
            if not overview:
                return Response({
                    'status': 'fail',
                    'message': 'No company overview found to update.',
                    'action': 'use_post_to_create'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = AboutusSerializer(
                overview, data=request.data, partial=True, context={'request': request}
            )

            if serializer.is_valid():
                with transaction.atomic():
                    updated_instance = serializer.save()

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='update',
                        description='Updated company overview content',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_data=request.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Company overview updated successfully.',
                        'data': serializer.data
                    }, status=status.HTTP_200_OK)

            return Response({
                'status': 'fail',
                'message': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicaboutusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            overview = Aboutus.objects.filter(is_active=True).first()
            if not overview:
                return Response({
                    'status': 'fail',
                    'message': 'Company overview is not available at the moment.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = AboutusSerializer(
                overview,
                context={'request': request, 'public_view': True}
            )

            return Response({
                'status': 'success',
                'message': 'Company overview loaded.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Service temporarily unavailable.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)