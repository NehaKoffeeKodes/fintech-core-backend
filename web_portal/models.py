from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class AdminAccount(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    google_auth_key = models.CharField(max_length=100, blank=True, null=True)
    verify_code = models.CharField(max_length=255, blank=True, null=True)
    verify_code_expire_at = models.DateTimeField(null=True, blank=True)
    is_verify = models.BooleanField(default=False)
    has_changed_initial_password = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, db_index=True)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "super_admin_account"
        ordering = ['-date_joined']
        verbose_name = "Admin Account"
        verbose_name_plural = "Admin Accounts"

    def __str__(self):
        return f"{self.get_full_name().strip() or self.username} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class SmtpEmail(models.Model):
    service_type = models.CharField(max_length=100, unique=True, default="SUPERADMIN")
    smtp_server = models.CharField(max_length=255)
    smtp_port = models.IntegerField()
    encryption = models.CharField(max_length=10, choices=[('SSL', 'SSL'), ('TLS', 'TLS')])
    sender_email = models.EmailField()
    sender_password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "superadmin_smtp_mail"
        verbose_name = "SMTP Configuration"

    def __str__(self):
        return f"{self.service_type} - {self.sender_email}"


class AdminActivityLog(models.Model):
    user = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    action = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    request_data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "web_user_activity"
        ordering = ['-timestamp']
        verbose_name = "Admin Activity Log"

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp.strftime('%d %b %Y %I:%M %p')}"


class Superadminlogindetails(models.Model):
    user = models.ForeignKey(AdminAccount, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    browser_name = models.CharField(max_length=200, blank=True, null=True)
    device_info = models.CharField(max_length=300, blank=True, null=True)
    login_time = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "superadmin_login_details"
        ordering = ['-login_time']
        verbose_name = "Superadmin logind etails"

    def __str__(self):
        return f"{self.user} logged in from {self.ip_address} at {self.login_time.strftime('%d %b %Y %I:%M %p')}"