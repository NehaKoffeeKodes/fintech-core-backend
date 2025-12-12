from ...views import*
from utils.Api.helpers import secure_random_string 

class AdminSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            username = request.data.get('username')
            password = request.data.get('password')

            if not username or not password:
                return Response({
                    'status': 'fail',
                    'message': 'Username and password are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            user = authenticate(request, username=username, password=password)
            if not user:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid username or password'
                }, status=status.HTTP_401_UNAUTHORIZED)

            if not user.is_active or user.is_deleted:
                return Response({
                    'status': 'fail',
                    'message': 'Account is deactivated'
                }, status=status.HTTP_403_FORBIDDEN)

            admin = user 
            short_token = generate_jwt_token(admin, expiry_minutes=10)

            if not admin.has_changed_initial_password:
                return Response({
                    'status': 'success',
                    'message': 'Please change your default password to continue.',
                    'requires_password_change': True
                }, status=status.HTTP_200_OK)

            if not admin.google_auth_key:
                return self._setup_2fa_and_send_qr(admin, short_token)

            return Response({
                'status': 'success',
                'message': 'Please enter your 2FA code from Authenticator.',
                'requires_totp': True,
                'access_token': short_token
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _setup_2fa_and_send_qr(self, admin, token):
        try:
            totp_secret = send_qr_code_via_smtp(
                to_email=admin.email,
                username=admin.username
            )

            admin.google_auth_key = totp_secret
            admin.save(update_fields=['google_auth_key'])

            return Response({
                'status': 'success',
                'message': 'QR code sent to your email. Please scan it to complete 2FA setup.',
                'requires_2fa_setup': True,
                'access_token': token
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to send 2FA setup email. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateInitialPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = PasswordChangeSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            username = request.data.get('username')
            if not username:
                return Response({
                    'status': 'fail',
                    'message': 'Username is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            admin = AdminAccount.objects.get(username=username, is_deleted=False)
            admin.set_password(serializer.validated_data['new_password'])
            admin.has_changed_initial_password = True

            if not admin.google_auth_key:
                totp_secret = send_qr_code_via_smtp(
                    to_email=admin.email,
                    username=admin.username
                )
                admin.google_auth_key = totp_secret
                admin.save(update_fields=['google_auth_key'])

                short_token = generate_jwt_token(admin, expiry_minutes=10)
                return Response({
                    'status': 'success',
                    'message': 'Password changed successfully. Please set up 2FA.',
                    'requires_2fa_setup': True,
                    'access_token': short_token
                }, status=status.HTTP_200_OK)
            else:
                admin.save()
                full_token = generate_jwt_token(admin, expiry_minutes=None)
                return Response({
                    'status': 'success',
                    'message': 'Password changed successfully! You now have full access.',
                    'access_token': full_token,
                    'requires_2fa_setup': False
                }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Invalid username'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TOTPVerificationView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            serializer = OTPInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            otp = serializer.validated_data['otp']
            user = request.user

            if not user.google_auth_key:
                return Response({
                    'status': 'fail',
                    'message': '2FA not configured for this account'
                }, status=status.HTTP_400_BAD_REQUEST)

            totp = pyotp.TOTP(user.google_auth_key)
            if totp.verify(otp, valid_window=1):
                final_token = generate_jwt_token(user, expiry_minutes=None)

                ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '0.0.0.0')
                browser = request.META.get('HTTP_SEC_CH_UA', 'Unknown')

                Superadminlogindetails.objects.create(
                    user=user,
                    ip_address=ip,
                    browser_name=str(browser)[:200]
                )

                return Response({
                    'status': 'success',
                    'message': '2FA successful! Welcome back.',
                    'access_token': final_token,
                    'token_type': 'Bearer'
                }, status=status.HTTP_200_OK)

            return Response({
                'status': 'fail',
                'message': 'Invalid or expired code'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = EmailInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            email = serializer.validated_data['email']
            admin = AdminAccount.objects.get(email=email, is_deleted=False)
            
            code = secure_random_string(6, '0123456789')
            admin.verify_code = make_password(code)
            admin.verify_code_expire_at = timezone.now() + timedelta(minutes=10)
            admin.save()

            send_welcome_email_direct_smtp(
                to_email=admin.email,
                full_name=f"{admin.first_name} {admin.last_name}".strip(),
                username=admin.username,
                password=code
            )

            AdminActivityLog.objects.create(
                user=admin,
                action="forgot_password_request",
                description=f"Password reset requested for {email}",
                ip_address=request.META.get('REMOTE_ADDR'),
                request_data=request.data
            )

            return Response({
                'status': 'success',
                'message': 'Verification code sent to your email'
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'This email is not registered.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmResetCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            code = request.data.get('code')

            if not email or not code:
                return Response({
                    'status': 'fail',
                    'message': 'Email and code are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            admin = AdminAccount.objects.get(email=email, is_deleted=False)

            if (admin.verify_code and 
                check_password(code, admin.verify_code) and
                admin.verify_code_expire_at and 
                admin.verify_code_expire_at > timezone.now()):

                admin.verify_code = None
                admin.verify_code_expire_at = None
                admin.is_verify = True
                admin.save()

                payload = {
                    'user_id': admin.id,
                    'purpose': 'password_reset',
                    'exp': timezone.now() + timedelta(minutes=15),
                    'iat': timezone.now()
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

                AdminActivityLog.objects.create(
                    user=admin,
                    action="verify_reset_code",
                    description="Password reset code verified",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    request_data=request.data
                )

                return Response({
                    'status': 'success',
                    'message': 'Code verified successfully',
                    'token': token
                }, status=status.HTTP_200_OK)

            return Response({
                'status': 'error',
                'message': 'Invalid or expired code'
            }, status=status.HTTP_400_BAD_REQUEST)

        except AdminAccount.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FinalizePasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
            new_password = request.data.get('new_password')

            if not token or not new_password:
                return Response({
                    'status': 'fail',
                    'message': 'Token and new password are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            admin = AdminAccount.objects.get(id=payload['user_id'], is_deleted=False)

            if not getattr(admin, 'is_verify', False):
                return Response({
                    'status': 'fail',
                    'message': 'Invalid or expired session'
                }, status=status.HTTP_400_BAD_REQUEST)

            admin.set_password(new_password)
            admin.is_verify = False
            admin.has_changed_initial_password = True
            admin.save()

            AdminActivityLog.objects.create(
                user=admin,
                action="password_reset_completed",
                description="Password changed via forgot password flow",
                ip_address=request.META.get('REMOTE_ADDR'),
                request_data={"new_password": "*****"}
            )

            return Response({
                'status': 'success',
                'message': 'Password changed successfully. You can now login.'
            }, status=status.HTTP_200_OK)

        except jwt.ExpiredSignatureError:
            return Response({
                'status': 'error',
                'message': 'Token expired'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except (jwt.InvalidTokenError, jwt.DecodeError):
            return Response({
                'status': 'error',
                'message': 'Invalid token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except AdminAccount.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)