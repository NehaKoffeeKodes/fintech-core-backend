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
        db_table = "admin_activity_log"
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
    
    


class Adminbanner(models.Model):
    client_name = models.CharField(max_length=150, unique=False)
    designation = models.CharField(max_length=200, blank=True)
    review_text = models.TextField()
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5
    profile_photo = models.ImageField(upload_to='Testimonials/Profile/')
    is_inactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    added_by = models.ForeignKey(AdminAccount, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.client_name} - {self.rating or 'No rating'} stars"

    class Meta:
        db_table = 'Admin_banners'
        ordering = ['-created_at']
        

class aboutus(models.Model):
    overview_id = models.AutoField(primary_key=True)
    company_story = models.TextField(blank=True, null=True)
    core_values = models.TextField(blank=True, null=True)
    leadership_message = models.TextField(blank=True, null=True)
    future_goals = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        AdminAccount, on_delete=models.PROTECT, related_name='company_overviews'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'about_us'
        verbose_name = 'Aboutus'
        verbose_name_plural = 'Aboutus'

    def __str__(self):
        return "Aboutus"

    def save(self, *args, **kwargs):
        if self.pk:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)
        


class NewsUpdate(models.Model):
    news_id = models.AutoField(primary_key=True)
    headline = models.CharField(max_length=300, blank=False)
    details = models.TextField()
    external_url = models.URLField(max_length=500, blank=True, null=True)
    publish_date = models.DateTimeField(default=timezone.now)
    is_hidden = models.BooleanField(default=False) 
    is_removed = models.BooleanField(default=False) 
    documents = models.JSONField(default=list, blank=True)  
    posted_by = models.ForeignKey(AdminAccount, on_delete=models.PROTECT)
    posted_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'hub_latest_news'
        ordering = ['-publish_date', '-news_id']
        verbose_name = 'Latest News Update'

    def save(self, *args, **kwargs):
        if self.pk:
            self.last_modified = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.headline[:50]
    
    


class ContactSupport(models.Model):
    TICKET_STATUS = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed')
    ]

    ticket_id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    phone_number = models.CharField(max_length=15, blank=True)
    issue_title = models.CharField(max_length=300)
    issue_description = models.TextField()
    current_status = models.CharField(max_length=20, choices=TICKET_STATUS, default='open')
    submitted_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(
        AdminAccount, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handled_tickets'
    )
    is_archived = models.BooleanField(default=False)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-submitted_at']

    def save(self, *args, **kwargs):
        if self.pk:
            self.last_updated = timezone.now()
        if self.customer_email:
            self.customer_email = self.customer_email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket #{self.ticket_id} - {self.customer_name}"