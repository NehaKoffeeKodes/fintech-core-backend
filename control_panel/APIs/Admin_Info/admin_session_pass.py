from ...views import *



class AdminSessionByPassView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        client_code = request.data.get('client_code')

        if not client_code:
            return Response({
                'success': False,
                'message': 'client_code is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = Admin.objects.get(
                db_name=client_code,
                is_active=True
            )

            switch_to_database(client.db_name)

            portal_user = PortalUser.objects.using(client.db_name).get(id=1)

            temp_token = create_jwt_token(
                portal_user,
                access_token_lifetime_minutes=10,
                db_name=client.db_name  
            )

            response_data = {
                'temp_access_token': str(temp_token),
                'dashboard_url': f"https://{client_code}.yourdomain.com",  
                'expires_in_minutes': 10
            }

            return Response({
                'success': True,
                'message': 'Quick access link generated successfully',
                'data': response_data
                
            }, status=status.HTTP_200_OK)

        except Admin.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid or inactive client code'
            }, status=status.HTTP_404_NOT_FOUND)

        except PortalUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Portal admin not found in client database'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as err:
            return Response({
                'success': False,
                'message': 'Access generation failed',
                'detail': str(err)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifySessionBypass(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        token = request.data.get('access_token')

        if not token:
            return Response({
                'success': False,
                'message': 'Access token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = AccessToken(token)
            user_id = payload['user_id']
            db_name = payload.get('db_name')

            if not db_name:
                raise ValueError("Database identifier missing from token")

            switch_to_database(db_name)

            user = PortalUser.objects.using(db_name).get(id=user_id)

            refresh = RefreshToken.for_user(user)
            refresh.set_exp(lifetime=timedelta(days=1))

            return Response({
                'success': True,
                'message': 'Session activated successfully',
                'user_id': user_id,
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'valid_for': '24 hours'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'message': 'Invalid or expired access link',
                'detail': 'This link may have expired or already been used'
            }, status=status.HTTP_401_UNAUTHORIZED)