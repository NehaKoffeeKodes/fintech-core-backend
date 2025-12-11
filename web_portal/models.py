from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db import models
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class AdminAccount(AbstractUser):
    email = models.EmailField(db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
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
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  
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
        

class Aboutus(models.Model):
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
        


class Latest_announcement(models.Model):
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
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
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
    handled_by = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL, null=True, blank=True,related_name='handled_tickets')
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
    

class ContactInfo(models.Model):
    info_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300, blank=True)
    support_email = models.EmailField()
    support_phone = models.CharField(max_length=15)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    gst_number = models.CharField(max_length=20, blank=True, null=True)
    cin_number = models.CharField(max_length=30, blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(AdminAccount, on_delete=models.PROTECT,related_name='contactinfo_created')
    updated_by = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL, null=True, blank=True,related_name='contactinfo_updated')

    class Meta:
        db_table = "contact_info"
        verbose_name = "Contact Info"
        verbose_name_plural = "Contact Info"

    def save(self, *args, **kwargs):
        if self.support_email:
            self.support_email = self.support_email.lower().strip()
        if self.pk is not None:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name or "Contact Info"
    
    

class NewsUpdateRecord(models.Model):
    record_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    subscriber_email = models.EmailField(max_length=254, unique=True)
    joined_on = models.DateTimeField(auto_now_add=True)
    modified_by = models.ForeignKey(
        AdminAccount, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_suspended = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)

    def clean(self):
        if self.subscriber_email:
            try:
                EmailValidator()(self.subscriber_email)
            except ValidationError:
                raise ValidationError({"subscriber_email": "Enter a valid email address."})

    def save(self, *args, **kwargs):
        if self.subscriber_email:
            self.subscriber_email = self.subscriber_email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.subscriber_email or "No Email"

    class Meta:
        db_table = "news_update_record"
        verbose_name = "News Update Record"
        verbose_name_plural = "News Update Record"
        

class Sponsor(models.Model):
    sponsor_code = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, unique=True)
    banner_image = models.CharField(max_length=500, null=True, blank=True)  
    details = models.TextField(blank=True)
    is_hidden = models.BooleanField(default=True)   
    is_archived = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='added_sponsors')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'core_sponsors'
   
   

class SiteConfig(models.Model):
    config_id = models.AutoField(primary_key=True)
    about_us_content = models.TextField(blank=True, null=True)
    refund_policy_text = models.TextField(blank=True, null=True)
    shipping_policy_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='site_settings_created')

    class Meta:
        db_table = 'core_site_configuration'
        verbose_name = 'Site Configuration'
        verbose_name_plural = 'Site Configuration'

    def __str__(self):
        return "Global Site Settings"
    

class ServiceCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_title = models.CharField(max_length=200, unique=True)
    short_info = models.TextField(blank=True, null=True)
    is_hidden = models.BooleanField(default=False) 
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(AdminAccount, on_delete=models.PROTECT, related_name='added_categories')
    is_removed = models.BooleanField(default=False)

    def __str__(self):
        return self.category_title

    class Meta:
        db_table = 'store_product_category'
        verbose_name_plural = "Product Categories"


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300)
    thumbnail = models.ImageField(upload_to='products/thumbnails/')
    details = models.TextField()
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    is_hidden = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='added_products')
    is_removed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'store_product'
        


class Customer_Testimonial(models.Model):
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField()
    is_approved = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,blank=True,related_name='Customer_Testimonial')

    class Meta:
        db_table = "Customer_Testimonial"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} - {self.rating} star"
        
        

class YouTubeVideo(models.Model):
    title = models.CharField(max_length=300)
    link = models.URLField()
    thumbnail = models.ImageField(upload_to='youtube/thumbnails/')
    is_active = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(AdminAccount, on_delete=models.PROTECT)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "web_youtube_video"
        ordering = ['-id']

    def __str__(self):
        return self.title