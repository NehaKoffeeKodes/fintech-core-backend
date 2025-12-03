import qrcode
from io import BytesIO
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings


def send_qr_code_via_smtp(to_email, username, qr_secret):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"otpauth://totp/Superadmin Portal:{username}?secret={qr_secret}&issuer=Superadmin Portal")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_image_data = buffer.getvalue()
        buffer.close()

        subject = "Superadmin Portal – Set Up Two-Factor Authentication (2FA)"

        html_content = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; background: #f9f9f9; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
            <h2 style="color: #1a5fb4; text-align:center; margin-bottom:10px;">Secure Your Account</h2>
            <p style="text-align:center; color:#555; margin-bottom:30px;">Two-Factor Authentication (2FA) Setup</p>

            <div style="background:white; padding:35px; border-radius:14px; text-align:center;">
                <p style="font-size:17px; color:#333; margin-bottom:30px;">
                    Hello <strong>{username}</strong>,<br><br>
                    Please scan the QR code below with <strong>Google Authenticator</strong> or Authy app:
                </p>

                <div style="margin:40px 0; padding:20px; background:#f8fbff; border-radius:12px; border:3px solid #1a5fb4;">
                    <img src="cid:qr_code_inline" alt="2FA QR Code" style="width:230px; height:230px;" />
                </div>

                <p style="color:#666; margin:25px 0 10px;">Can't scan the QR code?</p>
                <div style="background:#eef5ff; padding:18px; border-radius:10px; font-family:monospace; font-size:18px; letter-spacing:2px; border-left:6px solid #1a5fb4;">
                    <strong>{qr_secret}</strong>
                </div>

                <div style="margin-top:30px; padding:18px; background:#fff8e1; border-radius:10px; border-left:5px solid #ff9800;">
                    <p style="margin:0; color:#d32f2f; font-weight:bold; font-size:15px;">
                        Keep this QR code and secret key private and secure.
                    </p>
                </div>
            </div>

            <p style="text-align:center; color:#888; font-size:13px; margin-top:30px;">
                © 2025 Superadmin Portal – Enterprise Grade Security
            </p>
        </div>
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(html_content),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")

        email.attach("Qr_code.png", qr_image_data, "image/png")

        from email.mime.image import MIMEImage
        inline_image = MIMEImage(qr_image_data)
        inline_image.add_header('Content-ID', '<qr_code_inline>')
        inline_image.add_header('Content-Disposition', 'inline', filename='qr_code_inline')
        email.attach(inline_image)

        email.send(fail_silently=False)
    
    except Exception as e:
        raise


def send_welcome_email_direct_smtp(to_email, full_name, username, password):
    try:
        subject = "Welcome to Superadmin Portal – Your Account is Ready"

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 620px; margin: auto; padding: 30px; background: white; border: 1px solid #ddd; border-radius: 12px;">
            <h2 style="color: #0066cc; text-align:center;">Welcome to Superadmin Portal</h2>
            <p>Hello <strong>{full_name}</strong>,</p>
            <p>Your Super Administrator account has been created successfully.</p>
            
            <div style="background:#f0f8ff; padding:20px; border-radius:10px; margin:25px 0; border-left:5px solid #0066cc;">
                <p><strong>Login Details:</strong></p>
                <p>Username: <code style="background:#e3f2fd; padding:4px 8px; border-radius:4px;">{username}</code></p>
                <p>Temporary Password: 
                    <span style="background:#0066cc; color:white; padding:8px 16px; border-radius:6px; font-size:18px; letter-spacing:1px;">
                        <strong>{password}</strong>
                    </span>
                </p>
            </div>
            
            <p style="background:#fff3cd; padding:15px; border-radius:8px;">
                <strong>Important:</strong> You will be asked to change this password on first login.
            </p>
            
            <p>Thank you,<br><strong>Superadmin Security Team</strong></p>
            <hr>
            <p style="font-size:12px; color:#888; text-align:center;">
                This is an automated message. Please do not reply.
            </p>
        </div>
        """

        email = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(html_content),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

    except Exception as e:
        raise