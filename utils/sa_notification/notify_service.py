import qrcode
from io import BytesIO
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings
from email.mime.image import MIMEImage
import pyotp


def send_qr_code_via_smtp(to_email, username, qr_secret=None):
    if qr_secret is None:
        qr_secret = pyotp.random_base32()

    missing_padding = len(qr_secret) % 8
    if missing_padding:
        qr_secret += '=' * (8 - missing_padding)

    totp_uri = f"otpauth://totp/Superadmin%20Portal:{username}?secret={qr_secret}&issuer=Superadmin%20Portal"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_image_data = buffer.getvalue()
    buffer.close()

    subject = "Superadmin Portal – Set Up Two-Factor Authentication (2FA)"

    html_content = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; background: #f9f9f9; border-radius: 16px;">
        <h2 style="color: #1a5fb4; text-align:center;">Secure Your Account</h2>
        <p style="text-align:center; color:#555;">Two-Factor Authentication (2FA) Setup</p>

        <div style="background:white; padding:35px; border-radius:14px; text-align:center;">
            <p>Hello <strong>{username}</strong>,<br><br>
               Scan the QR code below with <strong>Google Authenticator</strong> or Authy:
            </p>

            <div style="margin:40px 0; padding:20px; background:#f8fbff; border-radius:12px;">
                <img src="cid:qr_code_inline" alt="2FA QR Code" style="width:240px; height:240px;" />
            </div>

            <p>Can't scan? Enter this key manually:</p>
            <div style="background:#eef5ff; padding:18px; border-radius:10px; font-family:monospace; font-size:20px; letter-spacing:3px; word-break:break-all;">
                <strong>{qr_secret}</strong>
            </div>

            <div style="margin-top:25px; padding:15px; background:#fff3cd; border-radius:8px; border-left:5px solid #ff9800;">
                <strong>Keep this secret safe and private!</strong>
            </div>
        </div>
    </div>
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=strip_tags(html_content),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    email.attach("2FA_QR_Code.png", qr_image_data, "image/png")

    inline_img = MIMEImage(qr_image_data)
    inline_img.add_header('Content-ID', '<qr_code_inline>')
    inline_img.add_header('Content-Disposition', 'inline', filename='qr_code_inline.png')
    email.attach(inline_img)

    email.send(fail_silently=False)
    return qr_secret


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