import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json

@method_decorator(csrf_exempt, name='dispatch')
class SendOTPEmailAPI(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            to_email = data.get('email')
            subject = data.get('subject', 'Your Verification Code')
            html_content = data.get('html')
            text_content = data.get('text', 'Your OTP code is inside the email.')
            SMTP_HOST = data.get('host', 'smtp.gmail.com')
            SMTP_PORT = int(data.get('port', 587))
            SMTP_USER = data.get('SMTP_USER')
            SMTP_PASS = data.get('SMTP_PASS')
            FROM_EMAIL = data.get('from_email', SMTP_USER)

            if not all([to_email, SMTP_USER, SMTP_PASS, html_content]):
                return JsonResponse({
                    "status": "fail",
                    "message": "Missing required fields"
                }, status=400)

            msg = MIMEMultipart("alternative")
            msg["From"] = FROM_EMAIL
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(FROM_EMAIL, to_email, msg.as_string())

            return JsonResponse({
                "status": "success",
                "message": "OTP email sent successfully"
            })

        except smtplib.SMTPAuthenticationError:
            return JsonResponse({
                "status": "error",
                "message": "Invalid SMTP username or password"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)