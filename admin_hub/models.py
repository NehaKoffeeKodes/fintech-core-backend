from django.db import models
from control_panel.models import*



class AdService(models.Model):
    service_id = models.AutoField(primary_key=True)
    service_title = models.CharField(max_length=100, unique=True)
    display_order = models.JSONField(default=list, blank=True)  # jaise [1,2,3] for priority
    short_info = models.TextField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(PortalUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='services_updated')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_title

    class Meta:
        db_table = 'platform_services'
        app_label = 'admin_hub'
        ordering = ['service_title']
        
        

class AdServiceProvider(models.Model):
    SERVICE_NATURE_CHOICES = [
        ('RECHARGE', 'Mobile/DTH'),
        ('BILLPAY', 'Bill Payment'),
        ('AEPS', 'AEPS'),
        ('DMT', 'Money Transfer'),
        ('PAN', 'PAN Card'),
        ('UTI', 'UTI PSA'),
        ('OTHERS', 'Others')
    ]

    provider_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(AdService,on_delete=models.CASCADE,related_name='providers')
    name = models.CharField(max_length=180, db_index=True)
    display_name = models.CharField(max_length=200, unique=True)
    short_code = models.CharField(max_length=15, unique=True, blank=True, null=True)
    sort_key = models.CharField(max_length=10, blank=True, null=True)
    hsn_sac = models.ForeignKey(GSTCode,on_delete=models.PROTECT,null=True,blank=True)   
    tds_percent = models.DecimalField(max_digits=8, decimal_places=4, default=0.000)
    parent_provider = models.PositiveIntegerField(null=True, blank=True)
    mapped_to = models.PositiveIntegerField(null=True, blank=True)
    api_credentials = models.JSONField(default=dict, blank=True)
    required_params = models.JSONField(default=list, blank=True)
    self_managed = models.BooleanField(default=False)
    uses_identifier = models.BooleanField(default=False, help_text="Does this provider use charge_identifier?")
    nature = models.CharField(max_length=20, choices=SERVICE_NATURE_CHOICES, blank=True, null=True)
    wallet_type = models.CharField(max_length=30, blank=True, null=True)
    platform_fee_mode = models.CharField(max_length=10, choices=[('FLAT', 'Flat'), ('PERCENT', '%')], blank=True, null=True)
    platform_fee_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    system_ref_id = models.PositiveIntegerField(null=True, blank=True)
    balance_endpoint = models.CharField(max_length=100, blank=True, null=True)
    can_fetch_balance = models.BooleanField(default=False)
    auth_token = models.TextField(blank=True, null=True) 
    config_key = models.CharField(max_length=100, blank=True, null=True)  
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,null=True,blank=True,related_name='updated_providers')

    class Meta:
        db_table = 'service_providers'
        app_label = 'admin_hub'
        ordering = ['name']
        verbose_name = 'Service Provider'
        unique_together = ['display_name', 'service']

    def __str__(self):
        return f"{self.display_name or self.name} ({self.service.service_name})"
    
    
    
    
class Adcharges(models.Model):
    TYPE_CHOICES = (('CREDIT', 'Credit'), ('DEBIT', 'Debit'))
    MODE_CHOICES = (('FLAT', 'Flat'), ('PERCENT', 'Percent'))
    BENEFICIARY_CHOICES = (('PLATFORM', 'Platform Share'), ('PROVIDER', 'Provider Share'))
    rule_id = models.AutoField(primary_key=True)
    provider = models.ForeignKey(AdServiceProvider,on_delete=models.CASCADE,related_name='commission_rules')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    charge_mode = models.CharField(max_length=10, choices=MODE_CHOICES)  
    identifier_value = models.PositiveIntegerField(null=True,blank=True)
    min_txn_amount = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    max_txn_amount = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    charge_amount = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    beneficiary = models.CharField(max_length=15, choices=BENEFICIARY_CHOICES, default='PLATFORM')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(PortalUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='created_commission_rules')
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_disabled = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'provider_commission_rules'
        app_label = 'admin_hub'
        verbose_name = 'Commission Rule'
        unique_together = ('provider', 'identifier_value', 'transaction_type', 'beneficiary')

    def __str__(self):
        return f"{self.provider.display_name} | {self.get_transaction_type_display()} | {self.charge_amount}"

    def clean(self):
        if self.charge_mode == 'PERCENT' and self.charge_amount > 100:
            raise ValidationError("Percentage charge cannot exceed 100%")
        if self.min_txn_amount > self.max_txn_amount:
            raise ValidationError("Min amount cannot be greater than max amount")
        
    
    
class PortalUserLog(models.Model):
    session_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='login_sessions',null=True,blank=True)
    role = models.CharField(max_length=50, db_index=True)
    auth_token = models.CharField(max_length=500, blank=True, null=True)
    token_expired = models.BooleanField(default=False)
    token_expiry_time = models.DateTimeField(null=True, blank=True)
    browser = models.CharField(max_length=200, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True) 
    login_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portal_user_log'
        app_label = 'admin_hub'
        ordering = ['-login_time']
        verbose_name = 'User Login Session'

    def __str__(self):
        return f"{self.user.email if self.user else 'Unknown'} - {self.login_time.strftime('%d %b %Y %H:%M')}"