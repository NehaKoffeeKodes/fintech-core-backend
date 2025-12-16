from ...views import *


class UpdatePasswordView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        current_pass = request.data.get('current_password')
        proposed_pass = request.data.get('new_password')

        if not all([current_pass, proposed_pass]):
            return Response({
                "success": False,
                "message": "Both current and new password are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin_user = AdminAccount.objects.get(id=request.user.id)

            if not check_password(current_pass, admin_user.password):
                return Response({
                    "success": False,
                    "message": "Current password is incorrect"
                }, status=status.HTTP_401_UNAUTHORIZED)

            if check_password(proposed_pass, admin_user.password):
                return Response({
                    "success": False,
                    "message": "New password must be different from the old one"
                }, status=status.HTTP_400_BAD_REQUEST)


            admin_user.set_password(proposed_pass)
            admin_user.save(update_fields=['password'])
            self.trigger_security_alert(request, admin_user)

            return Response({
                "success": True,
                "message": "Your password has been updated successfully",
                "timestamp": datetime.now().isoformat()
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                "success": False,
                "message": "User session invalid"
            }, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as err:
            return Response({
                "success": False,
                "message": "Password update failed due to server error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def trigger_security_alert(self, request, user):
        try:
            config = SmtpEmail.objects.filter(
                template_key__iexact='admin_password_change'
            ).first()

            if not config:
                return  

            subject, body_html = self.build_alert_email(request, user)

            payload = {
                "to": user.email,
                "subject": subject,
                "html_body": body_html,
                "sender_email": config.sender_address,
                "sender_pass": config.sender_password,
                "smtp_server": config.server_host,
                "smtp_port": config.server_port,
                "use_tls": config.use_tls,
            }

            requests.post(settings.NOTIFICATION_SERVICE_URL, json=payload, timeout=10)

        except Exception:
            pass 

    def build_alert_email(self, request, user):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
        platform = request.META.get('HTTP_SEC_CH_UA_PLATFORM', 'Unknown').strip('"')
        browser = 'Unknown'

        ua = request.META.get('HTTP_USER_AGENT', '')
        if 'Edg' in ua and 'Chrome' in ua:
            browser = 'Microsoft Edge'
        elif 'Chrome' in ua:
            browser = 'Google Chrome'
        elif 'Firefox' in ua:
            browser = 'Mozilla Firefox'
        elif 'Safari' in ua and 'Chrome' not in ua:
            browser = 'Apple Safari'
        else:
            browser = 'Unknown Browser'

        timestamp = datetime.now().strftime("%d %B %Y at %I:%M %p")

        subject = "Security Alert: Your Password Was Changed"

        html = f"""
        <div style="font-family: system-ui, sans-serif; max-width: 600px; margin: auto; background: #f9fafb; padding: 20px;">
            <div style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
                <div style="background: linear-gradient(135deg, #7c3aed, #3b82f6); color: white; padding: 24px; text-align: center;">
                    <h2 style="margin:0; font-size:24px;">Password Changed Successfully</h2>
                </div>

                <div style="padding: 32px;">
                    <p style="font-size:16px; color:#1f2937;">Hello <strong>{user.get_full_name() or user.username}</strong>,</p>
                    <p style="font-size:15px; color:#4b5563; line-height:1.7;">
                        Your account password was successfully changed on <strong>{timestamp}</strong>.
                    </p>

                    <div style="background:#f3f4f6; padding:16px; border-radius:8px; margin:20px 0; font-size:14px;">
                        <strong>Activity Details:</strong><br><br>
                        Time: {timestamp}<br>
                        IP Address: {ip}<br>
                        Device: {platform}<br>
                        Browser: {browser}
                    </div>

                    <p style="color:#dc2626; font-weight:600;">
                        If you did NOT make this change, please contact support immediately.
                    </p>

                    <div style="text-align:center; margin:30px 0;">
                        <a href="https://tapicashless.com/support" 
                           style="background:#111827; color:white; padding:12px 28px; text-decoration:none; border-radius:8px; font-weight:600;">
                            Contact Security Team
                        </a>
                    </div>

                    <p style="font-size:13px; color:#6b7280;">
                        Stay safe,<br><strong>TAPI Cashless Security</strong>
                    </p>
                </div>

                <div style="background:#1f2937; color:#9ca3af; text-align:center; padding:16px; font-size:12px;">
                    This is an automated security notification • © 2025 TAPI Cashless Pvt Ltd
                </div>
            </div>
        </div>
        """

        return subject, html