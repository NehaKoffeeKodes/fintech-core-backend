from ...views import*


class SMSSettingsView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            search = request.data.get('search', '').strip()
            all_sms = SMSAccount.objects.all().order_by('-sms_id')

            if search:
                all_sms = all_sms.filter(
                    Q(action_type__icontains=search) |
                    Q(sms_api_key__icontains=search) |
                    Q(sms_sender_id__icontains=search) |
                    Q(sms_pe_id__icontains=search)
                )

            final_list = []

            for cred in all_sms:
                try:
                    template = SMSTemplate.objects.get(credentials=cred)
                except SMSTemplate.DoesNotExist:
                    template = None

                final_list.append({
                    "id": cred.sms_id,
                    "api_key": cred.sms_api_key,
                    "sender_id": cred.sms_sender_id,
                    "type": cred.action_type,
                    "action_id": cred.action_id,
                    "pe_id": cred.sms_pe_id,
                    "template_id": template.mt_te_id if template else "",
                    "message_body": template.message if template else "",
                    "added_on": cred.created_at.strftime("%d %b %Y, %I:%M %p")
                })

            total = len(final_list)
            total_pages = math.ceil(total / size)
            start = (page - 1) * size
            end = start + size
            current_page_data = final_list[start:end]

            return Response({
                "status": "success",
                "message": "SMS settings mil gaye",
                "data": {
                    "total_items": total,
                    "total_pages": total_pages,
                    "current_page": page,
                    "results": current_page_data
                }
            })

        except Exception as e:
            return Response({
                "status": "error",
                "message": "Error: " + str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            sms_id = request.data.get('id')
            if not sms_id:
                return Response({"status": "fail", "message": "ID chahiye"}, status=status.HTTP_400_BAD_REQUEST)

            cred = SMSAccount.objects.get(sms_id=sms_id)
            if request.data.get('api_key'):      cred.sms_api_key = request.data['api_key']
            if request.data.get('sender_id'):    cred.sms_sender_id = request.data['sender_id']
            if request.data.get('type'):         cred.action_type = request.data['type']
            if request.data.get('action_id'):    cred.action_id = request.data['action_id']
            if request.data.get('pe_id'):        cred.sms_pe_id = request.data['pe_id']
            cred.save()

            if request.data.get('message_body'):
                template = SMSTemplate.objects.get(credentials=cred)
                template.message = request.data['message_body']
                template.save()

            return Response({
                "status": "success",
                "message": "SMS settings update ho gaye!"
            })

        except SMSAccount.DoesNotExist:
            return Response({"status": "fail", "message": "SMS setting nahi mili"}, status=status.HTTP_404_NOT_FOUND)
        except SMSTemplate.DoesNotExist:
            return Response({"status": "fail", "message": "Template nahi mila"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class SmtpEmailsView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            search = request.data.get('search', '')

            emails = SmtpEmail.objects.filter(action_type='SUPERADMIN').order_by('-smtp_id')

            if search:
                emails = emails.filter(
                    Q(smtp_host__icontains=search) |
                    Q(smtp_host_user__icontains=search)
                )

            total = emails.count()
            total_pages = math.ceil(total / size)
            start = (page - 1) * size
            paginated = emails[start:start + size]

            result = []
            for e in paginated:
                result.append({
                    "id": e.smtp_id,
                    "host": e.smtp_host,
                    "port": e.smtp_port,
                    "username": e.smtp_host_user,
                    "password": "******", 
                    "encryption": e.encryption_type,
                    "from_email": e.from_email,
                    "type": e.action_type,
                    "added_on": e.created_at.strftime("%d %b %Y")
                })

            return Response({
                "status": "success",
                "message": "Email settings mil gaye",
                "data": {
                    "total": total,
                    "pages": total_pages,
                    "page": page,
                    "results": result
                }
            })

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        if 'otp' in request.data:
            return self.check_otp_and_save(request)
        else:
            return self.send_test_otp(request)

    def send_test_otp(self, request):
        try:
            smtp_id = request.data.get('id')
            if not smtp_id:
                return Response({"status": "fail", "message": "SMTP ID required"}, status=status.HTTP_400_BAD_REQUEST)

            email_setting = SmtpEmail.objects.get(smtp_id=smtp_id)
            otp = get_random_string(6, allowed_chars='0123456789')
            email_setting.verify_otp = otp
            email_setting.otp_expires_at = timezone.now() + timezone.timedelta(minutes=10)
            email_setting.save(update_fields=['verify_otp', 'otp_expires_at'])
            html_msg = f"""
            <!DOCTYPE html>
            <html>
            <body style="margin:0; padding:20px; font-family:Arial; background:#f7f9fc;">
                <center>
                    <table width="100%" style="max-width:600px; background:white; border-radius:12px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,0.1);">
                        <tr>
                            <td style="background:#4a6bdf; color:white; padding:30px; text-align:center;">
                                <h1>Email Verification</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:40px 30px; text-align:center;">
                                <p style="font-size:18px; color:#333;">Namaste <strong>Admin</strong>,</p>
                                <p style="font-size:16px; color:#555; margin:20px 0;">
                                    Aapka verification code hai:
                                </p>
                                <div style="background:#f0f2f5; padding:20px; border-radius:10px; font-size:36px; letter-spacing:10px; color:#4a6bdf; font-weight:bold;">
                                    {otp}
                                </div>
                                <p style="margin-top:30px; color:#e74c3c;">
                                    Yeh code <strong>10 minute</strong> mein expire ho jayega.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td style="background:#f8f9fa; padding:20px; text-align:center; color:#95a5a6; font-size:14px;">
                                © {timezone.now().year} Your Company • All rights reserved
                            </td>
                        </tr>
                    </table>
                </center>
            </body>
            </html>
            """

            text_msg = strip_tags(html_msg)
            response = requests.post(
                "http://127.0.0.1:8000/api/send-otp-email/",
                json={  
                    "email": request.data.get('from_email') or email_setting.from_email,
                    "subject": "Verify Email Settings - OTP Code",
                    "html": html_msg,
                    "text": text_msg,
                    "host": request.data.get('host') or email_setting.smtp_host,
                    "port": request.data.get('port') or email_setting.smtp_port,
                    "SMTP_USER": request.data.get('username') or email_setting.smtp_host_user,
                    "SMTP_PASS": request.data.get('password') or email_setting.smtp_host_password,
                    "from_email": request.data.get('from_email') or email_setting.from_email,
                },
                timeout=20  
            )

            if response.status_code == 200:
                return Response({
                    "status": "success",
                    "message": "OTP successfully sent to your email!"
                })
            else:
                return Response({
                    "status": "fail",
                    "message": f"Email send failed: {response.text}"
                }, status=500)

        except SmtpEmail.DoesNotExist:
            return Response({"status": "fail", "message": "Email setting not found"}, status=status.HTTP_404_NOT_FOUND)
        except requests.exceptions.RequestException as e:
            return Response({
                "status": "error",
                "message": f"Email service down hai: {str(e)}"
            }, status=503)
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=500)

    def check_otp_and_save(self, request):
        try:
            smtp_id = request.data.get('id')
            entered_otp = request.data.get('otp')
            setting = SmtpEmail.objects.get(smtp_id=smtp_id)

            if setting.verify_otp != entered_otp:
                return Response({"status": "fail", "message": "Galat OTP"}, status=status.HTTP_400_BAD_REQUEST)

            if setting.otp_expires_at < timezone.now():
                return Response({"status": "fail", "message": "OTP expire ho gaya"}, status=status.HTTP_400_BAD_REQUEST)

            if request.data.get('host'):         setting.smtp_host = request.data['host']
            if request.data.get('port'):         setting.smtp_port = request.data['port']
            if request.data.get('username'):     setting.smtp_host_user = request.data['username']
            if request.data.get('password'):     setting.smtp_host_password = request.data['password']
            if request.data.get('encryption'):   setting.encryption_type = request.data['encryption']
            if request.data.get('from_email'):   setting.from_email = request.data['from_email']
            setting.save()

            return Response({
                "status": "success",
                "message": "Email settings save ho gaye!"
            })

        except SmtpEmail.DoesNotExist:
            return Response({"status": "fail", "message": "Setting nahi mili"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)