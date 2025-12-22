from django.db import models
from django.core.validators import RegexValidator
from control_panel.models import *
from decimal import Decimal

class PortalUser(models.Model):
    MEMBER_CATEGORY = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('DISTRIBUTOR', 'Distributor'),
        ('RETAILER', 'Retailer'),
    ]

    WORKFLOW_STATUS = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('KYC_IN_PROGRESS', 'KYC In Progress'),
    ]

    id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=200, db_index=True)
    email_address = models.EmailField(unique=True, db_index=True)
    mobile_number = models.CharField(max_length=10,validators=[RegexValidator(r'^\d{10}$', 'Enter a valid 10-digit mobile number')])
    access_pin = models.CharField(max_length=128, blank=True, null=True)
    member_type = models.CharField(max_length=30, choices=MEMBER_CATEGORY)
    otp_token = models.CharField(max_length=100, blank=True, null=True)
    otp_expiry = models.DateTimeField(blank=True, null=True) 
    email_confirmed = models.BooleanField(default=False)
    virtual_account_active = models.BooleanField(default=False)
    kyc_completed = models.BooleanField(default=False)
    aeps_service_status = models.CharField(max_length=50, default="NOT_STARTED")
    aeps_merchant_code = models.CharField(max_length=80, blank=True, null=True)
    rejection_note = models.TextField(blank=True, null=True)   
    service_config = models.JSONField(default=dict, blank=True, null=True)
    allowed_domains = models.JSONField(default=list, blank=True, null=True)
    active_modules = models.JSONField(default=list, blank=True, null=True)
    pinned_features = models.JSONField(default=dict, blank=True, null=True)
    extra_info = models.JSONField(default=dict, blank=True, null=True) 
    account_status = models.CharField(max_length=30,choices=WORKFLOW_STATUS,default='PENDING_REVIEW')
    two_factor_secret = models.CharField(max_length=80, blank=True, null=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey('self',on_delete=models.PROTECT,related_name='members_created_by_me',null=True,blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_suspended = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'core_system_members'
        ordering = ['-registered_at']
        verbose_name = 'System Member'
        verbose_name_plural = 'System Members'

    def clean(self):
        if self.email_address:
            self.email_address = self.email_address.lower().strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.member_type} ({self.get_account_status_display()})"
   


class PortalUserInfo(models.Model):
    profile_id = models.AutoField(primary_key=True)
    user_account = models.OneToOneField(PortalUser,on_delete=models.PROTECT, related_name='profile_details',null=True,blank=True)
    hierarchy_node = models.ForeignKey(PortalUser,on_delete=models.SET_NULL,null=True,blank=True)
    unique_member_code = models.CharField(max_length=12,blank=True, unique=True)
    aadhaar_number = models.CharField(max_length=12,validators=[RegexValidator(r'^\d{12}$', 'Aadhaar must be 12 digits')],null=True, blank=True)
    pan_number = models.CharField(max_length=10,validators=[RegexValidator(r'^[A-Z]{5}[0-9]{4}[A-Z]$', 'Invalid PAN format')],null=True, blank=True, unique=True)
    pan_verification_data = models.JSONField(null=True, blank=True)
    business_name = models.CharField(max_length=200, null=True, blank=True)
    outlet_photo = models.ImageField(upload_to='outlets/', null=True, blank=True)
    outlet_coordinates = models.JSONField(null=True, blank=True)  
    full_address = models.TextField(null=True, blank=True)
    state_ref = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, related_name='+')
    city_ref = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='+')
    pincode = models.CharField(max_length=6, validators=[RegexValidator(r'^\d{6}$')], null=True, blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)  
    gstin = models.CharField(max_length=15, null=True, blank=True, unique=True)
    business_category = models.CharField(max_length=20, null=True, blank=True)  
    secondary_mobile = models.CharField(max_length=10, null=True, blank=True)
    live_location_capture = models.JSONField(null=True, blank=True)
    created_by_user = models.ForeignKey(PortalUser,on_delete=models.SET_NULL,null=True,related_name='profiles_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_member_profiles'
        verbose_name = 'Member Profile'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.pan_number:
            self.pan_number = self.pan_number.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile: {self.user_account.full_name if self.user_account else 'N/A'} ({self.profile_id})" 



class AdService(models.Model):
    service_id = models.AutoField(primary_key=True)
    service_title = models.CharField(max_length=100, unique=True)
    display_order = models.JSONField(default=list, blank=True)  
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
        

class FundRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'

class TransactionMode(models.TextChoices):
    UPI = 'UPI', 'UPI'
    IMPS = 'IMPS', 'IMPS'
    NEFT = 'NEFT', 'NEFT'
    RTGS = 'RTGS', 'RTGS'
    CASH = 'CASH', 'Cash Deposit'
    CDM = 'CDM', 'CDM Deposit'

class FundDepositRequest(models.Model):
    request_ref = models.AutoField(primary_key=True)
    deposit_methods = models.JSONField(default=list)
    linked_bank = models.ForeignKey(DepositBankAccount,on_delete=models.PROTECT,related_name='deposit_requests')
    deposit_amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    utr_ref = models.CharField(max_length=50, unique=True, blank=True, null=True, db_index=True)
    transfer_mode = models.CharField(max_length=20,choices=TransactionMode.choices,blank=True,null=True)
    proof_documents = models.JSONField(default=list)
    user_remarks = models.TextField(blank=True, null=True)
    admin_reasons = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20,choices=FundRequestStatus.choices,default=FundRequestStatus.PENDING)
    is_void = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='fund_requests_made',null=True,blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(PortalUser,on_delete=models.SET_NULL,related_name='fund_requests_reviewed',null=True,blank=True)

    class Meta:
        db_table = 'txn_fund_deposit_requests'
        verbose_name = 'Fund Deposit Request'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['utr_ref']),
            models.Index(fields=['status']),
            models.Index(fields=['submitted_at']),
        ]

    def __str__(self):
        return f"Request #{self.request_ref} - ₹{self.deposit_amount} [{self.get_status_display()}]"


class PortalUserBalance(models.Model):
    balance_id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(PortalUser,on_delete=models.PROTECT,related_name='wallet_account',db_column='portal_user_id',null=True,blank=True)
    primary_balance = models.DecimalField(max_digits=20, decimal_places=3, default=0.000)
    earnings_balance = models.DecimalField(max_digits=20, decimal_places=3, default=0.000)
    deposit_balance = models.DecimalField(max_digits=20, decimal_places=3, default=0.000, null=True, blank=True)
    gateway_balance = models.DecimalField(max_digits=20, decimal_places=3, default=0.000, null=True, blank=True)
    outstanding_balance = models.DecimalField(max_digits=20, decimal_places=3, default=0.000, null=True, blank=True)
    hold_balance = models.DecimalField(max_digits=20, decimal_places=3, default=0.000, null=True, blank=True, help_text="Lien / Frozen amount")
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated_on = models.DateTimeField(null=True, blank=True)
    last_updated_by = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'portal_user_balances'
        verbose_name = 'User Wallet'
        verbose_name_plural = 'User Wallets'
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Wallet #{self.balance_id} - {self.user.get_full_name() or self.user.username or 'N/A'}"

    def total_available(self):
        return (
            self.primary_balance +
            self.earnings_balance +
            (self.deposit_balance or 0) +
            (self.gateway_balance or 0) +
            (self.outstanding_balance or 0)
        )
        
        
        
#useractivity

class MemberActionLog(models.Model):
    log_id = models.AutoField(primary_key=True)  
    record_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    module_name = models.CharField(max_length=100, db_index=True, null=True, blank=True)
    action_type = models.CharField(max_length=80, db_index=True) 
    action_details = models.TextField(blank=True, null=True)
    performed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    performed_by = models.ForeignKey(PortalUser,on_delete=models.SET_NULL,null=True,blank=True,related_name='action_logs')
    request_payload = models.JSONField(null=True, blank=True)   
    response_payload = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'core_activity_logs'
        ordering = ['-performed_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        user = self.performed_by.full_name if self.performed_by else "System"
        return f"{user} → {self.action_type} on {self.module_name or 'Unknown'}"



TRANSACTION_NATURE = [
    ('CR', 'Credit'),
    ('DR', 'Debit'),
]

class GlTrn(models.Model):
    entry_id = models.AutoField(primary_key=True)
    linked_service_id = models.BigIntegerField(null=True, blank=True)
    member = models.ForeignKey(PortalUser,on_delete=models.PROTECT,null=True,blank=True,related_name='ledger_entries')
    transaction_type = models.CharField(max_length=100, blank=True) 
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tds_percent = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0000'))
    gst_percent = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0000'))
    tds_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    source_table = models.CharField(max_length=100, blank=True)  
    wallet_type = models.CharField(max_length=30, blank=True)    
    final_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    entry_nature = models.CharField(max_length=6, choices=TRANSACTION_NATURE) 
    transaction_time = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_ledger_entries'
        ordering = ['-recorded_at']

    def __str__(self):
        return f"Ledger #{self.entry_id} | ₹{self.amount} | {self.get_entry_nature_display()}"


class WalletHistory(models.Model):
    history_id = models.AutoField(primary_key=True)
    reference_id = models.BigIntegerField(null=True, blank=True)   
    action_name = models.CharField(max_length=150)                 
    user = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='wallet_history')
    wallet_name = models.CharField(max_length=50)                 
    changed_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    change_type = models.CharField(max_length=6, choices=TRANSACTION_NATURE)  
    balance_after = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    remarks = models.CharField(max_length=500, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_wallet_history'
        ordering = ['-created_at']
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'

    def __str__(self):
        return f"{self.user} → {self.get_change_type_display()} ₹{self.changed_amount} ({self.action_name})"
    
    

class PaymentGatewayBank(models.Model):
    bank_id = models.AutoField(primary_key=True)
    supported_services = models.JSONField(default=list)
    bank_full_name = models.CharField(max_length=200, blank=True, null=True)
    ifsc = models.CharField(max_length=11,validators=[RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$', 'Enter valid IFSC code')],blank=True,null=True)
    branch = models.CharField(max_length=150, blank=True, null=True)
    account_holder_name = models.CharField(max_length=200, blank=True, null=True)
    account_no = models.CharField(max_length=30, blank=True, null=True)
    account_category = models.CharField(max_length=50, blank=True, null=True) 
    upi_imps_charges = models.JSONField(default=dict, blank=True, null=True)
    cash_deposit_machine_charges = models.JSONField(default=dict, blank=True, null=True)
    over_the_counter_charges = models.JSONField(default=dict, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='bank_accounts_added',null=True,blank=True)
    modified_on = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(PortalUser,on_delete=models.SET_NULL,related_name='bank_accounts_modified',null=True,blank=True)

    class Meta:
        db_table = 'gateway_banks_config'
        verbose_name = 'Payment Gateway Bank'
        verbose_name_plural = 'Payment Gateway Banks'
        ordering = ['-added_on']

    def __str__(self):
        return f"{self.bank_full_name or 'N/A'} - {self.account_no or 'No Account'} ({'Active' if self.is_active else 'Inactive'})"

    def clean(self):
        if self.ifsc:
            self.ifsc = self.ifsc.upper().strip()
        if self.account_no:
            self.account_no = ''.join(filter(str.isdigit, self.account_no))
            
                   

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
        
class AdGSTCode(models.Model):
    code_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)  
    details = models.TextField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,null=True,blank=True)
    updated_on = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_removed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} ({self.gst_rate}%)"

    class Meta:
        db_table = "master_tax_codes"
        app_label = 'admin_hub'
    
    
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
    
    

class SaOperatorCharge(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'platform_charge_heads'
        
        

class BillerGroup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'tenant_biller_groups'

class DmtTransferClient(models.Model):
    client_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(max_length=10, unique=True, blank=True)
    service_mode = models.CharField(max_length=10, choices=[('DMT1', 'DMT1'), ('DMT2', 'DMT2')], default='DMT1')
    full_address = models.TextField(blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    aadhaar_number = models.CharField(max_length=12, blank=True)
    is_registered = models.BooleanField(default=False)
    limits_fetched = models.BooleanField(default=False)
    registration_data = models.JSONField(default=dict, blank=True)
    daily_limits = models.JSONField(default=dict, blank=True)
    joined_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} ({self.mobile or 'No Mobile'})".strip()

    class Meta:
        db_table = 'client_money_transfer'
        app_label = 'admin_hub'
        ordering = ['-joined_on']
        
        


class UserLoginSession(models.Model):
    session_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(PortalUser, on_delete=models.CASCADE, related_name='sessions')
    device_name = models.CharField(max_length=200, blank=True, null=True)
    os_version = models.CharField(max_length=100, blank=True, null=True)
    app_version = models.CharField(max_length=50, blank=True, null=True)
    fcm_token = models.TextField(blank=True, null=True)
    access_token = models.CharField(max_length=600, unique=True)
    is_logged_out = models.BooleanField(default=False)
    logout_at = models.DateTimeField(null=True, blank=True)
    last_active_at = models.DateTimeField(default=timezone.now)
    platform = models.CharField(max_length=50, choices=[('ANDROID', 'Android'), ('IOS', 'iOS'), ('WEB', 'Web')])
    ip_location = models.JSONField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'track_user_sessions'
        ordering = ['-created_on']

    def __str__(self):
        return f"{self.user} - {self.platform}"
   


class GovernmentChargeLog(models.Model):
    entry_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='govt_charges')
    provider = models.ForeignKey(ServiceProvider,on_delete=models.PROTECT,null=True,blank=True)
    transaction_ref = models.CharField(max_length=150, blank=True)
    charge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    charge_type = models.CharField(max_length=20, blank=True) 
    applied_on = models.CharField(max_length=50, blank=True)   
    hierarchy_level = models.CharField(max_length=10, blank=True) 
    user_role = models.CharField(max_length=30, blank=True)      
    base_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    final_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    recorded_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'govt_charge_entries'
        app_label = 'admin_hub'
        ordering = ['-recorded_at']
        verbose_name = "Government Levy Entry"
        verbose_name_plural = "Government Levy Entries"

    def __str__(self):
        return f"{self.charge_type} ₹{self.final_charge} on {self.transaction_ref or 'Manual'}"
        

class GlobalBankList(models.Model):
    bank_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=200,unique=True)
    short_code = models.CharField(max_length=30,unique=True)
    master_ifsc = models.CharField(max_length=11,unique=True,blank=True,null=True)
    dmt_fino_config = models.JSONField(default=dict, blank=True, help_text="Fino DMT IDs")
    dmt_nsdl_config = models.JSONField(default=dict, blank=True, help_text="NSDL PAN IDs")
    dmt_airtel_config = models.JSONField(default=dict, blank=True, help_text="Airtel DMT IDs")
    payout_enabled = models.BooleanField(default=False)
    fd_enabled = models.BooleanField(default=False)  
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'master_banks'
        app_label = 'admin_hub'
        ordering = ['full_name']
        verbose_name = "Global Bank Master"
        verbose_name_plural = "Global Bank Masters"

    def __str__(self):
        status = "Active" if self.is_active else "Disabled"
        services = []
        if self.payout_enabled: services.append("Payout")
        if self.fd_enabled: services.append("FD")
        service_str = f" [{', '.join(services)}]" if services else ""
        return f"{self.full_name} ({self.short_code}){service_str} — {status}"
    



class RechargeTransaction(models.Model):
    recharge_id = models.AutoField(primary_key=True)
    request_txn_id = models.CharField(max_length=55, null=True, blank=True)          
    service_provider = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)  
    txn_reference = models.CharField(max_length=55, null=True, blank=True)         
    mobile_number = models.CharField(max_length=10, null=True, blank=True)         
    operator_name = models.CharField(max_length=55, null=True, blank=True)         
    recharge_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000) 
    circle = models.CharField(max_length=55, null=True, blank=True)                 
    api_response = models.JSONField(null=True, blank=True)                          
    recharge_status = models.CharField(max_length=255, null=True, blank=True)       
    transaction_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)  
    verification_code = models.CharField(max_length=128, blank=True, null=True)     
    verification_expiry = models.DateTimeField(blank=True, null=True)              
    initiated_by = models.IntegerField(null=True, blank=True)                      
    created_on = models.DateTimeField(auto_now_add=True)                            

    class Meta:
        db_table = 'ad_recharge_transaction'           
        app_label = 'admin_hub'
        verbose_name = 'Recharge Transaction'
        verbose_name_plural = 'Recharge Transactions'

    def __str__(self):
        return f"Recharge {self.request_txn_id or 'N/A'} - {self.mobile_number or 'N/A'}"
    
        
class DmtBankAccount(models.Model):
    bank_id = models.AutoField(primary_key=True)
    holder_name = models.CharField(max_length=200, blank=True)
    bank_name = models.CharField(max_length=150)
    bank_ref = models.ForeignKey(GlobalBankList, on_delete=models.PROTECT, null=True, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True)
    paysprint_info = models.JSONField(default=dict, blank=True)
    instantpay_info = models.JSONField(default=dict, blank=True)
    bankit_info = models.JSONField(default=dict, blank=True)
    noble_info = models.JSONField(default=dict, blank=True)
    upi_id = models.CharField(max_length=80, blank=True)
    deleted_from_provider = models.JSONField(default=dict, blank=True)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    is_added_to_system = models.BooleanField(default=False)
    is_verified_with_provider = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_removed = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.holder_name} - {self.bank_name} ({self.account_number[-4:] if self.account_number else 'XXXX'})"

    class Meta:
        db_table = 'bank_beneficiary'
        app_label = 'admin_hub'
        unique_together = ('account_number', 'ifsc_code')
        ordering = ['-added_on']
               
        
class OperatorList(models.Model):
    id = models.AutoField(primary_key=True)
    operator_name = models.CharField(max_length=100)
    op_code = models.CharField(max_length=20)
    operator_type = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.operator_name

    class Meta:
        db_table = 'tenant_operators'


class HierarchyLevel(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    prefix = models.CharField(max_length=10)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'tenant_hierarchy'
        

class MoneyTransferLog(models.Model):
    transfer_id = models.AutoField(primary_key=True)
    provider = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT)
    reference_code = models.CharField(max_length=80, unique=True)
    transfer_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    payment_mode = models.CharField(max_length=20, blank=True)
    api_response = models.JSONField(default=dict, blank=True)
    beneficiary_name = models.CharField(max_length=200, blank=True)
    beneficiary_aadhaar = models.CharField(max_length=12, blank=True)
    beneficiary_mobile = models.CharField(max_length=10, blank=True)
    transfer_status = models.CharField(max_length=50, default='PENDING')
    processed_at = models.DateTimeField(auto_now_add=True)
    initiated_by = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'txn_money_transfer'
        app_label = 'admin_hub'
        
        
class PaymentGatewayRecord(models.Model):
    gateway_txn_id = models.AutoField(primary_key=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    order_ref = models.CharField(max_length=100, unique=True, null=True)
    customer_ref = models.CharField(max_length=20, blank=True)
    txn_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    gateway_response = models.JSONField(default=dict)
    aadhaar_response = models.JSONField(default=dict, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_name = models.CharField(max_length=150, blank=True)
    customer_aadhaar = models.CharField(max_length=12, blank=True)
    customer_mobile = models.CharField(max_length=10, blank=True)
    otp_hash = models.CharField(max_length=200, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    txn_status = models.CharField(max_length=30, default='PENDING')
    txn_timestamp = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.customer_email:
            self.customer_email = self.customer_email.lower()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'txn_pg_gateway'
        app_label = 'admin_hub'
        
        
class RechargeHistory(models.Model):
    recharge_id = models.AutoField(primary_key=True)
    operator_txn = models.CharField(max_length=80, blank=True)
    service_partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    our_txn_id = models.CharField(max_length=80, blank=True)
    request_txn_id = models.CharField(max_length=80, blank=True)
    mobile_number = models.CharField(max_length=10, blank=True)
    operator_name = models.CharField(max_length=100, blank=True)
    recharge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    circle_code = models.CharField(max_length=50, blank=True)
    api_reply = models.JSONField(default=dict, blank=True)
    recharge_status = models.CharField(max_length=50, default='PENDING')
    recharge_time = models.DateTimeField(auto_now_add=True)
    otp_code = models.CharField(max_length=100, blank=True)
    otp_expiry = models.DateTimeField(null=True, blank=True)
    created_by = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'txn_mobile_recharge'
        app_label = 'admin_hub'
        
        
class FundTransferEntry(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    ]

    entry_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(DmtTransferClient, on_delete=models.PROTECT, null=True)
    bank_detail = models.ForeignKey(DmtBankAccount, on_delete=models.PROTECT, null=True)
    mobile_no = models.CharField(max_length=10, blank=True)
    beneficiary_name = models.CharField(max_length=200, blank=True)
    ref_number = models.CharField(max_length=70, blank=True)
    transfer_type = models.CharField(max_length=30, blank=True)
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2)
    charges_applied = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    provider_reply = models.JSONField(default=dict)
    transfer_time = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    initiated_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_fund_transfer'
        app_label = 'admin_hub'
        

class CashfreeKycProfile(models.Model):
    profile_id = models.AutoField(primary_key=True)
    kyc_documents = models.JSONField(default=dict,blank=True)
    mobile_number = models.CharField(max_length=10,unique=True,blank=True,null=True)
    pan_number = models.CharField(max_length=10,blank=True,null=True)
    verification_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    is_kyc_completed = models.BooleanField(default=False)
    added_by = models.PositiveIntegerField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"KYC Profile - {self.mobile_number or 'No Mobile'} (ID: {self.profile_id})"

    class Meta:
        db_table = 'kyc_cashfree_profiles'
        app_label = 'admin_hub'
        ordering = ['-added_on']
        verbose_name = "Cashfree KYC Customer"
        verbose_name_plural = "Cashfree KYC Customers"
        
    
class BillPaymentRecord(models.Model):
    bill_id = models.AutoField(primary_key=True)
    biller_ref = models.CharField(max_length=100, blank=True)
    service_partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    customer_mobile = models.CharField(max_length=10, blank=True)
    request_ref = models.CharField(max_length=100, blank=True)
    bill_fetch_data = models.JSONField(default=dict, blank=True)
    payment_data = models.JSONField(default=dict, blank=True)
    bill_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=50, default='PENDING')
    payment_date = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'txn_bbps_bill'
        app_label = 'admin_hub'
        
        
class CashfreePaymentLog(models.Model):
    cf_txn_id = models.AutoField(primary_key=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    cf_order_id = models.CharField(max_length=100, unique=True, null=True)
    customer_profile = models.ForeignKey(CashfreeKycProfile, on_delete=models.PROTECT, null=True)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    cf_response = models.JSONField(default=dict)
    customer_mobile = models.CharField(max_length=10, blank=True)
    payment_status = models.CharField(max_length=30, default='FAILED')
    settlement_status = models.CharField(max_length=30, default='PENDING')
    txn_time = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    updated_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_cashfree_pg'
        app_label = 'admin_hub'
        
        
class PhonePePaymentEntry(models.Model):
    pp_id = models.AutoField(primary_key=True)
    merchant_txn_id = models.CharField(max_length=80, blank=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    mobile = models.CharField(max_length=10, blank=True)
    payment_reply = models.JSONField(default=dict, blank=True)
    transaction_reply = models.JSONField(default=dict, blank=True)
    current_status = models.CharField(max_length=20, default='FAILED')
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'txn_phonepe'
        app_label = 'admin_hub'
        


class ElectricityCategory(models.Model):
    provider_id = models.AutoField(primary_key=True)
    board_name = models.CharField(max_length=200,unique=True)
    short_code = models.CharField(max_length=15,unique=True,blank=True,null=True)
    operator_code = models.CharField(max_length=50,blank=True,null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,null=True,blank=True,related_name='electricity_categories_added')

    class Meta:
        db_table = 'utility_electricity_boards'
        app_label = 'admin_hub'
        ordering = ['board_name']
        verbose_name = "Electricity Board Category"
        verbose_name_plural = "Electricity Board Categories"

    def __str__(self):
        return f"{self.board_name} ({self.short_code or 'No Code'})"
    
    
       
class AadhaarVerifyLog(models.Model):
    verify_id = models.AutoField(primary_key=True)
    request_id = models.CharField(max_length=80, unique=True, blank=True)
    request_payload = models.JSONField(default=dict)
    api_response = models.JSONField(default=dict)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    linked_bank = models.PositiveIntegerField(null=True)
    verify_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    initiated_by = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'txn_aadhaar_verify'
        app_label = 'admin_hub'
        
        
class ElectricityBillEntry(models.Model):
    bill_id = models.AutoField(primary_key=True)
    consumer_id = models.CharField(max_length=100, blank=True)
    consumer_name = models.CharField(max_length=200, blank=True)
    mobile_no = models.CharField(max_length=10, blank=True)
    bill_amount = models.CharField(max_length=20, blank=True)
    unique_ref = models.CharField(max_length=100, blank=True)
    rpid_number = models.CharField(max_length=100, blank=True)
    agent_code = models.CharField(max_length=50, blank=True)
    fetch_response = models.JSONField(default=dict)
    payment_response = models.JSONField(default=dict)
    bill_status = models.CharField(max_length=30, blank=True)
    category = models.ForeignKey(ElectricityCategory, on_delete=models.PROTECT, null=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_electricity'
        app_label = 'admin_hub'



class GasCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=250,unique=True)
    provider_key = models.CharField(max_length=20,unique=True,blank=True,null=True)
    gateway_code = models.CharField(max_length=30,blank=True,null=True) 
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,null=True,blank=True,related_name='gas_categories_created')

    class Meta:
        db_table = 'utility_gas_companies'
        app_label = 'admin_hub'
        ordering = ['company_name']
        verbose_name = "Gas Company Category"
        verbose_name_plural = "Gas Company Categories"

    def __str__(self):
        return f"{self.company_name} {self.provider_key and '(' + self.provider_key + ')' or ''}".strip()
          

class GasBillEntry(models.Model):
    bill_id = models.AutoField(primary_key=True)
    consumer_account = models.CharField(max_length=100, blank=True)
    customer_name = models.CharField(max_length=200, blank=True)
    contact_mobile = models.CharField(max_length=10, blank=True)
    due_amount = models.CharField(max_length=20, blank=True)
    transaction_ref = models.CharField(max_length=100, blank=True)
    rpid = models.CharField(max_length=100, blank=True)
    agent_ref = models.CharField(max_length=50, blank=True)
    bill_details = models.JSONField(default=dict)
    payment_details = models.JSONField(default=dict)
    payment_status = models.CharField(max_length=30, blank=True)
    gas_category = models.ForeignKey(GasCategory, on_delete=models.PROTECT, null=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_gas_bill'
        app_label = 'admin_hub'
        
        
class LicPremiumEntry(models.Model):
    premium_id = models.AutoField(primary_key=True)
    policy_number = models.CharField(max_length=100, blank=True)
    registered_mobile = models.CharField(max_length=10, blank=True)
    premium_amount = models.CharField(max_length=20, blank=True)
    lic_ref_id = models.CharField(max_length=100, blank=True)
    lic_rpid = models.CharField(max_length=100, blank=True)
    lic_agent_id = models.CharField(max_length=50, blank=True)
    bill_info = models.JSONField(default=dict)
    payment_info = models.JSONField(default=dict)
    premium_status = models.CharField(max_length=30, blank=True)
    lic_type = models.CharField(max_length=50, blank=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_lic_premium'
        app_label = 'admin_hub'
   
   
   

class AepsBankList(models.Model):
    bank_id = models.AutoField(primary_key=True)
    bank_code = models.CharField(max_length=20,unique=True)
    bank_name = models.CharField(max_length=150) 
    iin_number = models.CharField(max_length=10,unique=True,blank=True,null=True)
    aeps_success_rate = models.CharField(max_length=10,default="0%")
    aadhaar_pay_success_rate = models.CharField(max_length=10,default="0%")
    aeps_active = models.BooleanField(default=True)
    aadhaar_pay_active = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bank_aeps_list'
        app_label = 'admin_hub'
        ordering = ['bank_name']
        verbose_name = "AEPS Supported Bank"
        verbose_name_plural = "AEPS Supported Banks"

    def __str__(self):
        status = "AEPS"
        if self.aeps_active and self.aadhaar_pay_active:
            status = "AEPS + AP"
        elif self.aadhaar_pay_active:
            status = "AP Only"
        return f"{self.bank_name} ({self.bank_code}) — {status}"
    
    
         
        
class AepsCashLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    reference_no = models.CharField(max_length=40, unique=True, blank=True)
    customer_mobile = models.CharField(max_length=10, blank=True)
    outlet_code = models.CharField(max_length=20, blank=True)
    ipay_ref = models.CharField(max_length=50, blank=True)
    txn_type = models.CharField(max_length=30, blank=True)  
    api_reply = models.JSONField(default=dict, blank=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    bank = models.ForeignKey(AepsBankList, on_delete=models.PROTECT, null=True)
    txn_amount = models.CharField(max_length=15, blank=True)  
    current_status = models.CharField(max_length=20, default='PENDING')
    initiated_by = models.PositiveIntegerField(null=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'txn_aeps_cash'
        app_label = 'admin_hub'
        


class ServiceIdentifier(models.Model):
    mapping_id = models.AutoField(primary_key=True)
    provider = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    config_data = models.JSONField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True, null=True, blank=True)
    updated_by = models.ForeignKey(PortalUser, on_delete=models.PROTECT, db_column='updated_by', null=True)
    deactivated = models.BooleanField(default=False)
    soft_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"ProviderMapping {self.mapping_id}"

    class Meta:
        db_table = "service_identifier"
        app_label = 'admin_hub'
        



class GlobalBankInstitution(models.Model):
    institution_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    short_code = models.CharField(max_length=50, null=True, blank=True)
    universal_ifsc = models.CharField(max_length=15, null=True, blank=True)
    fino_mapping = models.JSONField(null=True, blank=True)
    nsdl_mapping = models.JSONField(null=True, blank=True)
    airtel_mapping = models.JSONField(null=True, blank=True)
    supports_payout = models.BooleanField(default=False)
    supports_funding = models.BooleanField(default=False)
    is_inactive = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'master_institutions'
        app_label = 'admin_hub'

    def __str__(self):
        return self.full_name or "Unnamed Bank"
          

class BulkPeClientInfo(models.Model):
    client_id = models.AutoField(primary_key=True)
    mobile = models.CharField(max_length=10, unique=True)
    full_name = models.CharField(max_length=200)
    pan_number = models.CharField(max_length=10, unique=True) 
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    is_registered = models.BooleanField(default=False)
    registered_on = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='bulkpe_clients')

    class Meta:
        db_table = 'bulkpe_clients'
        app_label = 'admin_hub'
        ordering = ['-registered_on']
        verbose_name = "Bulk PE Customer"

    def __str__(self):
        return f"{self.full_name} ({self.mobile})"


class BulkPeCardInfo(models.Model):
    card_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(BulkPeClientInfo, on_delete=models.PROTECT, related_name='cards')
    card_ref = models.CharField(max_length=50, unique=True, blank=True, null=True)
    sender_ref = models.CharField(max_length=80, blank=True, null=True)
    masked_card = models.CharField(max_length=20, help_text="XXXX-XXXX-XXXX-1234")
    cvv = models.CharField(max_length=4, blank=True) 
    expiry_mm_yy = models.CharField(max_length=5, help_text="MM/YY")
    holder_name = models.CharField(max_length=150)
    card_images = models.JSONField(default=dict,blank=True)
    card_network = models.CharField(max_length=20, blank=True) 
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='bulkpe_cards_added')

    class Meta:
        db_table = 'bulkpe_cards'
        app_label = 'admin_hub'
        ordering = ['-added_on']

    def __str__(self):
        return f"{self.masked_card} - {self.holder_name}"


class BulkPeBeneficiaryInfo(models.Model):
    beneficiary_id = models.AutoField(primary_key=True)
    unique_ref = models.CharField(max_length=80, unique=True)
    owner = models.ForeignKey(BulkPeClientInfo, on_delete=models.PROTECT, related_name='beneficiaries')
    card_used = models.ForeignKey(BulkPeCardInfo, on_delete=models.PROTECT, null=True, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)
    account_holder = models.CharField(max_length=200)
    account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=11)
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=20, default='PENDING')  
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,related_name='bulkpe_beneficiaries')

    class Meta:
        db_table = 'bulkpe_beneficiaries'
        app_label = 'admin_hub'
        unique_together = ('owner', 'account_number', 'ifsc_code')
        ordering = ['-added_on']

    def __str__(self):
        return f"{self.account_holder} - {self.bank_name} (...{self.account_number[-4:]})"

        
class BulkPayoutRecord(models.Model):
    payout_id = models.AutoField(primary_key=True)
    payout_ref = models.CharField(max_length=120, blank=True)
    batch_ref = models.CharField(max_length=80, blank=True)
    markup_fee = models.CharField(max_length=20, blank=True)
    card_used = models.ForeignKey(BulkPeCardInfo, on_delete=models.PROTECT, null=True)
    beneficiary = models.ForeignKey(BulkPeBeneficiaryInfo, on_delete=models.PROTECT, null=True)
    client = models.ForeignKey(BulkPeClientInfo, on_delete=models.PROTECT, null=True)
    admin = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    transfer_amount = models.CharField(max_length=20, blank=True)
    utr_number = models.CharField(max_length=50, blank=True)
    payout_result = models.CharField(max_length=30, default='PROCESSING')
    batch_result = models.CharField(max_length=30, default='PROCESSING')
    payout_mode = models.CharField(max_length=15, blank=True)
    admin_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    initiated_by = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True)

    class Meta:
        db_table = 'txn_bulk_payout'
        app_label = 'admin_hub'
        
        
class AirtelBillEntry(models.Model):
    entry_id = models.AutoField(primary_key=True)
    cms_ref = models.CharField(max_length=80, blank=True)
    airtel_txn_id = models.CharField(max_length=80, blank=True)
    biller_code = models.CharField(max_length=100, blank=True)
    biller_name = models.CharField(max_length=200, blank=True)
    mobile_no = models.CharField(max_length=10, blank=True)
    utr_ref = models.CharField(max_length=100, blank=True)
    ack_number = models.CharField(max_length=100, blank=True)
    unique_ref = models.CharField(max_length=80, unique=True)
    bill_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    api_response = models.JSONField(default=dict, blank=True)
    admin = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    bill_status = models.CharField(max_length=30, default='PENDING')
    bill_time = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_airtel_cms'
        app_label = 'admin_hub'
        
    
class BankItAepsRecord(models.Model):
    record_id = models.AutoField(primary_key=True)
    bankit_txn = models.CharField(max_length=100, blank=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    mobile = models.CharField(max_length=10, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rrn_no = models.CharField(max_length=50, blank=True)
    aadhaar_uid = models.CharField(max_length=12, blank=True)
    operation_type = models.CharField(max_length=30, blank=True)
    api_reply = models.JSONField(default=dict)
    txn_status = models.CharField(max_length=30, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_bankit_aeps'
        app_label = 'admin_hub'
        
        
class MicroAtmEntry(models.Model):
    entry_id = models.AutoField(primary_key=True)
    txn_ref = models.CharField(max_length=100, blank=True)
    admin = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    mobile_no = models.CharField(max_length=10, blank=True)
    txn_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    card_last6 = models.CharField(max_length=20, blank=True)
    api_response = models.JSONField(default=dict)
    current_status = models.CharField(max_length=30, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_micro_atm'
        app_label = 'admin_hub'
        
        
class PpiTransferLog(models.Model):
    transfer_id = models.AutoField(primary_key=True)
    event_name = models.CharField(max_length=50, blank=True)
    customer_mobile = models.CharField(max_length=10, blank=True)
    partner = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    txn_status = models.CharField(max_length=30, default='PENDING')
    txn_ref_id = models.CharField(max_length=100, blank=True)
    utr_ref = models.CharField(max_length=50, blank=True)
    ack_ref = models.CharField(max_length=100, blank=True)
    merchant_id = models.CharField(max_length=50, blank=True)
    provider_reply = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_ppi_transfer'
        app_label = 'admin_hub'
  
 

class KhataClient(models.Model):
    client_id = models.AutoField(primary_key=True)
    client_code = models.CharField(max_length=80, unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=200)
    mobile = models.CharField(max_length=10, unique=True)
    pincode = models.CharField(max_length=6, blank=True)
    account_opened = models.BooleanField(default=False)
    in_progress = models.BooleanField(default=False)
    application_no = models.CharField(max_length=100, blank=True)
    kyc_mode = models.CharField(max_length=30, blank=True) 
    limits_fetched = models.BooleanField(default=False)
    bank_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    wallet_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    aadhaar_verified = models.BooleanField(default=False)
    pan_verified = models.BooleanField(default=False)
    joined_on = models.DateTimeField(auto_now_add=True)
    added_by = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'khata_clients'
        app_label = 'admin_hub'
        ordering = ['-joined_on']

    def __str__(self):
        return f"{self.full_name} ({self.mobile})"
    

class KhataBankAccount(models.Model):
    account_id = models.AutoField(primary_key=True)
    holder_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=40)
    ifsc_code = models.CharField(max_length=11)
    bank_name = models.CharField(max_length=150)
    provider_data = models.JSONField(default=dict, blank=True)  
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    deleted_info = models.JSONField(default=dict, blank=True)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    is_removed = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.PositiveIntegerField(null=True, blank=True)
    modified_on = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'khata_bank_accounts'
        app_label = 'admin_hub'
        unique_together = ('account_number', 'ifsc_code')

    def __str__(self):
        return f"{self.holder_name} - {self.bank_name} (XXXX{self.account_number[-4:]})"
  
        
        
class KhataTransferEntry(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    ]

    entry_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(KhataClient, on_delete=models.PROTECT, null=True)
    bank_account = models.ForeignKey(KhataBankAccount, on_delete=models.PROTECT, null=True)
    mobile_no = models.CharField(max_length=10, blank=True)
    client_name = models.CharField(max_length=200, blank=True)
    reference_no = models.CharField(max_length=80, blank=True)
    transfer_mode = models.CharField(max_length=20, blank=True)
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    api_response = models.JSONField(default=dict)
    transfer_time = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    initiated_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_digikhata'
        app_label = 'admin_hub'
        
        


class AdGadgetCategory(models.Model):
    cat_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    parent = models.IntegerField(null=True, blank=True)
    info = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.IntegerField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    inactive = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'ad_gadget_category'

    def __str__(self):
        return self.name


class AdGadgetItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(AdGadgetCategory, on_delete=models.PROTECT, null=True, blank=True)
    title = models.CharField(max_length=100)
    info = models.TextField(blank=True, null=True)
    model_code = models.CharField(max_length=100, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(blank=True, null=True)
    images = models.JSONField(blank=True, null=True)
    self_managed = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    soft_deleted = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(blank=True, null=True)
    modified_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'ad_gadget_item'

    def __str__(self):
        return self.title


class AdItemSerial(models.Model):
    serial_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(AdGadgetItem, on_delete=models.PROTECT, null=True, blank=True)
    serial_code = models.CharField(max_length=255, unique=True)
    assigned_user = models.IntegerField(null=True, blank=True)
    deactivated = models.BooleanField(blank=True, null=True)
    deleted = models.BooleanField(default=False)
    created_by = models.IntegerField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'ad_item_serial'

    def __str__(self):
        return self.serial_code
    
    
class HoldTransaction(models.Model):
    hold_id = models.AutoField(primary_key=True)
    provider = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    ref_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True, blank=True)
    hold_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.000, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, null=True, blank=True)
    lien_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.000, null=True, blank=True)
    recorded_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_hold_amount'
        app_label = 'admin_hub'