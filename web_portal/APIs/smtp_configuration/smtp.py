from ...views import*

class SMTPConfigurationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            config = SmtpEmail.objects.first()

            if not config:
                return Response({
                    'status': 'fail',
                    'message': 'SMTP configuration has not been set up yet.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = SmtpEmailSerializer(config, context={'request': request})
            return Response({
                'status': 'success',
                'message': 'SMTP settings retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        current_user = request.user
        ip_addr = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        try:
            existing_smtp = SmtpEmail.objects.first()

            serializer = SmtpEmailSerializer(
                instance=existing_smtp,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if not serializer.is_valid():
                return Response({
                    'status': 'fail',
                    'message': 'Invalid data provided.',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                if existing_smtp:
                    smtp_instance = serializer.save()
                    action = 'Updated'
                    msg = 'SMTP configuration updated successfully.'
                    http_code = status.HTTP_200_OK
                else:
                    smtp_instance = serializer.save()
                    action = 'Created'
                    msg = 'SMTP configuration created successfully.'
                    http_code = status.HTTP_201_CREATED

                AdminActivityLog.objects.create(
                    user=current_user if hasattr(current_user, 'AdminAccount') else None,
                    action='SMTP_CONFIG_CHANGE',
                    description=f'{action} SMTP email settings (ID: {smtp_instance.pk})',
                    ip_address=ip_addr,
                    user_agent=user_agent,
                    request_data=request.data
                )

                return Response({
                    'status': 'success',
                    'message': msg,
                    'data': serializer.data
                }, status=http_code)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)