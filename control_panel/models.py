from django.db import models
from django.core.validators import RegexValidator
from web_portal.models import*
from django.contrib.auth import get_user_model
from decimal import Decimal



class GSTCode(models.Model):
    gst_id = models.AutoField(primary_key=True)
    gst_code = models.CharField(max_length=20, unique=True)
    cgst = models.DecimalField(max_digits=5, decimal_places=2)
    sgst = models.DecimalField(max_digits=5, decimal_places=2)
    igst = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_hidden = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(AdminAccount, on_delete=models.PROTECT, related_name='gst_entries_added')
    updated_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,blank=True,related_name='gst_entries_updated')

    class Meta:
        db_table = 'tax_gst_codes'
        ordering = ['-gst_id']

    def __str__(self):
        return f"GST {self.gst_code} ({self.cgst}%)"
    
    
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
    


class SMSAccount(models.Model):
    sms_id = models.AutoField(primary_key=True)
    api_key = models.CharField(max_length=300, blank=True)
    sender = models.CharField(max_length=50, blank=True)
    action = models.CharField(max_length=100, blank=True)
    action_id = models.IntegerField(null=True, blank=True)
    pe_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sms_credentials'


class SMSTemplate(models.Model):
    template_id = models.AutoField(primary_key=True)
    te_id = models.CharField(max_length=100, blank=True)
    credentials = models.ForeignKey(SMSAccount, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sms_templates'



class Region(models.Model): 
    region_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120, unique=True, db_index=True)
    short_code = models.CharField(max_length=10, blank=True, null=True)
    status = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.PositiveIntegerField(null=True, blank=True)
    modified_on = models.DateTimeField(null=True, blank=True)
    modified_by = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'master_regions'
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'

    def __str__(self):
        return self.name

    def clean(self):
        if self.short_code:
            self.short_code = self.short_code.upper()


class Location(models.Model): 
    locality_id = models.AutoField(primary_key=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='localities')
    title = models.CharField(max_length=150)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'master_locations'
        unique_together = ('title', 'region')
        verbose_name = 'Locality'
        verbose_name_plural = ' Locations'
        indexes = [
            models.Index(fields=['title', 'region']),
        ]

    def __str__(self):
        return f"{self.title} ({self.region.name})"


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


class Admin(models.Model):
    GST_COMPOSITION = 'COMPOSITION'
    GST_REGULAR = 'REGULAR'
    GST_UNREGISTERED = 'UNREGISTERED'
    GST_SEZ = 'SEZ'
    GST_EXPORT = 'EXPORT'
    GST_ECOM = 'ECOMMERCE'

    GST_REGIME_CHOICES = [
        (GST_COMPOSITION, 'Composition'),
        (GST_REGULAR, 'Regular'),
        (GST_UNREGISTERED, 'Unregistered'),
        (GST_SEZ, 'SEZ'),
        (GST_EXPORT, 'Exports'),
        (GST_ECOM, 'E-Commerce'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    admin_id = models.AutoField(primary_key=True)
    entity_name = models.CharField(max_length=150, unique=True)
    mobile = models.CharField(max_length=10, unique=True)
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='entities/avatar/', null=True, blank=True)   
    pan = models.CharField(max_length=10, unique=True, null=True, blank=True)
    aadhaar = models.CharField(max_length=12, unique=True, null=True, blank=True)    
    is_pan_verified = models.BooleanField(default=False)
    is_gst_verified = models.BooleanField(default=False)
    company_title = models.CharField(max_length=255, null=True, blank=True)
    gst_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    gst_regime = models.CharField(max_length=20, choices=GST_REGIME_CHOICES, default=GST_COMPOSITION)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(null=True, blank=True)
    documents_uploaded = models.JSONField(default=list, blank=True)
    registered_state = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    registered_city = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    pin_code = models.CharField(max_length=6, null=True, blank=True)
    enabled_services = models.JSONField(default=list, blank=True)
    agreement_pdf = models.FileField(upload_to='agreements/', null=True, blank=True)
    db_name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_soft_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,related_name='entities_created_by')
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        if self.pan:
            self.pan = self.pan.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.entity_name} ({self.get_status_display()})"

    class Meta:
        db_table = 'admin'
        
  

class SaCoreService(models.Model):
    service_key = models.AutoField(primary_key=True)
    title = models.CharField(max_length=80, unique=True)
    routing_order = models.JSONField(null=True, blank=True) 
    details = models.TextField(blank=True, null=True)
    last_modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL, null=True)
    disabled = models.BooleanField(default=False)

    class Meta:
        db_table = 'core_services'
        verbose_name = "Core Service"

    def __str__(self):
        return self.title


class ServiceProvider(models.Model):
    TDS_WITH = 'WITH_TDS'
    TDS_WITHOUT = 'WITHOUT_TDS'
    TDS_OPTIONS = [(TDS_WITH, 'With TDS'), (TDS_WITHOUT, 'Without TDS')]
    admin_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(SaCoreService, on_delete=models.CASCADE, related_name='admins')
    admin_code = models.CharField(max_length=100, unique=True)
    display_label = models.CharField(max_length=200)
    api_credentials = models.JSONField(null=True, blank=True)
    required_params = models.JSONField(null=True, blank=True)
    hsn_code = models.ForeignKey(GSTCode, on_delete=models.SET_NULL, null=True, blank=True)
    tds_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tds_applicable = models.CharField(max_length=20, choices=TDS_OPTIONS, null=True, blank=True)
    wallet_type = models.CharField(max_length=30, null=True, blank=True)
    supports_balance_check = models.BooleanField(default=False)
    is_charge_service = models.BooleanField(default=False)
    platform_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    charge_type = models.CharField(max_length=10, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL, null=True)
    is_inactive = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'service_admins'

    def __str__(self):
        return f"{self.display_label} ({self.admin_code})"



User = get_user_model()

class AdminService(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    admin = models.ForeignKey(Admin,on_delete=models.CASCADE,related_name='assigned_services',null=True,blank=True)
    service = models.ForeignKey(SaCoreService,on_delete=models.PROTECT,related_name='admin_assignments')
    provider = models.ForeignKey(ServiceProvider,on_delete=models.PROTECT,related_name='admin_service_links')
    commission_structure = models.JSONField(default=dict,blank=True)
    commission_rate = models.DecimalField(max_digits=8,decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name='service_assignments_created')
    is_suspended = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'admin_service_assignments'
        unique_together = ('admin', 'service', 'provider')  
        verbose_name = 'admin Service Assignment'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admin} ← {self.service.name} ({self.provider})"
  
  

class AdminContract(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('TERMINATED', 'Terminated')
    ]

    contract_id = models.AutoField(primary_key=True)
    base_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    gst_component = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, editable=False)
    signed_document = models.FileField(upload_to='contracts/signed/', null=True, blank=True)
    contract_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contracts')
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='contracts', null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'admin_contracts'
        ordering = ['-created_at']
        verbose_name = 'admin Contract'
        verbose_name_plural = 'admin Contracts'

    def __str__(self):
        return f"Contract #{self.contract_id} - {self.admin.business_name if self.admin else 'N/A'}"
        

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
            
            


class DepositBankAccount(models.Model):
    account_id = models.AutoField(primary_key=True)
    enabled_channels = models.JSONField(default=list)
    bank_title = models.CharField(max_length=180, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11,validators=[RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$')],blank=True,null=True,unique=True)
    branch_location = models.CharField(max_length=200, blank=True, null=True)
    holder_name = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=30, unique=True, blank=True, null=True)
    account_kind = models.CharField(max_length=50, blank=True, null=True)  
    digital_transfer_fees = models.JSONField(default=dict, blank=True, null=True)      
    cdm_deposit_fees = models.JSONField(default=dict, blank=True, null=True)
    branch_counter_fees = models.JSONField(default=dict, blank=True, null=True)
    is_enabled = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(AdminAccount,on_delete=models.PROTECT,related_name='deposit_banks_created',null=True,blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,related_name='deposit_banks_updated',null=True,blank=True)

    class Meta:
        db_table = 'config_deposit_banks'
        verbose_name = 'Deposit Bank Account'
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.bank_title or 'Unnamed Bank'} - {self.account_number or 'N/A'}"




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
    
    



class AdditionalFee(models.Model):
    fee_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=150, blank=True, null=True)
    category = models.CharField(max_length=60, blank=True, null=True)  
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_code = models.ForeignKey(GSTCode, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_removed = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'master_extra_fees'
        ordering = ['-fee_id']
        verbose_name = "Extra Charge"
        verbose_name_plural = "Extra Charges"

    def __str__(self):
        return f"{self.title or 'No Title'} ({self.amount or 0})"
    
    

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
        



User = get_user_model()

class ChargeRule(models.Model):
    TYPE_CHOICES = (('CREDIT', 'Credit'), ('DEBIT', 'Debit'))
    RATE_MODE_CHOICES = (('FLAT', 'Flat Amount'), ('PERCENT', 'Percentage'))
    CATEGORY_CHOICES = (('OUR_SHARE', 'Our Share'), ('admin_SHARE', 'admin Share'))
    rule_id = models.AutoField(primary_key=True)
    service_provider = models.ForeignKey(ServiceProvider,on_delete=models.CASCADE,related_name='charge_rules')
    charge_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    rate_mode = models.CharField(max_length=15, choices=RATE_MODE_CHOICES)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    linked_identifier = models.PositiveIntegerField(null=True, blank=True, help_text="e.g., Operator ID, Biller ID")
    charge_beneficiary = models.CharField(max_length=20,choices=CATEGORY_CHOICES,default='OUR_SHARE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL,null=True,related_name='modified_charge_rules')
    is_disabled = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'provider_charge_rules'
        verbose_name = 'Charge Rule'
        verbose_name_plural = 'Charge Rules'
        ordering = ['-created_at']
        unique_together = ('service_provider', 'linked_identifier', 'charge_type', 'charge_beneficiary')

    def __str__(self):
        return f"Rule {self.rule_id} | {self.service_provider.label} | {self.get_charge_type_display()} | {self.rate_value or 0}"
    
    
class SaBillerGroup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'global_biller_groups'


class SaGlobalOperator(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    operator_type = models.CharField(max_length=50, blank=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        db_table = 'global_operators'


class SaAdditionalCharges(models.Model):
    fee_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=150, blank=True, null=True)
    category = models.CharField(max_length=60, blank=True, null=True)  
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_code = models.ForeignKey(GSTCode, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_removed = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'Sa_admin_fees'
        ordering = ['-fee_id']
        verbose_name = "Extra Charge"
        verbose_name_plural = "Extra Charges"

    def __str__(self):
        return f"{self.title or 'No Title'} ({self.amount or 0})"
    
from django.db import models


class Charges(models.Model):
    CREDIT = 'CR'
    DEBIT = 'DR'
    CHARGE_TYPE_CHOICES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    ]

    FLAT = 'is_flat'
    PERCENT = 'is_percent'
    RATE_TYPE_CHOICES = [
        (FLAT, 'Is Flat'),
        (PERCENT, 'Is Percent'),
    ]

    TO_US = 'to_us'
    TO_PROVIDE = 'to_provide'
    CATEGORY_CHOICES = [
        (TO_US, 'To Us'),
        (TO_PROVIDE, 'To Provide'),
    ]

    charges_id = models.AutoField(primary_key=True)
    service_provider = models.ForeignKey(
        ServiceProvider,  
        on_delete=models.CASCADE,
        related_name='charges'
    )
    charges_type = models.CharField(
        max_length=2,
        choices=CHARGE_TYPE_CHOICES,
        help_text="Type of charge: Credit or Debit"
    )
    rate_type = models.CharField(
        max_length=20,
        choices=RATE_TYPE_CHOICES,
        help_text="Whether rate is flat amount or percentage"
    )
    minimum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum transaction amount for this slab"
    )
    maximum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum transaction amount for this slab"
    )
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Charge rate (flat or percentage based on rate_type)"
    )
    identifier_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Used for identifier-based services"
    )
    charge_category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=TO_US,
        help_text="Who receives the charge: To Us or To Provide"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        AdminAccount, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='updated_by',
        related_name='updated_charges'
    )
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'sa_charges'
        verbose_name = 'Charge Slab'
        verbose_name_plural = 'Charge Slabs'
        ordering = ['minimum', 'charges_id']

    def __str__(self):
        provider = self.service_provider.label if hasattr(self.service_provider, 'label') else self.service_provider.sp_name
        return f"Charge {self.charges_id} - {provider} ({self.get_charges_type_display()})"

   
class DocumentTemplate(models.Model):
    template_id = models.AutoField(primary_key=True)
    display_name = models.CharField(max_length=100, help_text="Name shown to user")
    internal_code = models.CharField(max_length=100, unique=True, db_index=True)
    slug_key = models.SlugField(max_length=120, unique=True, db_index=True)
    mandatory = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    soft_deleted = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(
        AdminAccount, on_delete=models.SET_NULL, null=True,
        related_name='created_templates'
    )

    class Meta:
        db_table = 'master_document_templates'
        verbose_name = "Document Template"
        ordering = ['-template_id']

    def __str__(self):
        return f"{self.display_name} ({'Required' if self.mandatory else 'Optional'})"