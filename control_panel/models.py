from django.db import models
from django.core.validators import RegexValidator
from web_portal.models import*


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
    
    


class State(models.Model):
    state_id = models.AutoField(primary_key=True)
    state_name = models.CharField(max_length=100, unique=True)
    state_code = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'master_state'

    def __str__(self):
        return self.state_name


class District(models.Model):
    district_id = models.AutoField(primary_key=True)
    district_name = models.CharField(max_length=150, unique=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    is_removed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(AdminAccount,on_delete=models.PROTECT,null=True,blank=True,related_name='districts_created')

    class Meta:
        db_table = 'master_district'
        ordering = ['district_name']

    def __str__(self):
        return f"{self.district_name}, {self.state.state_name}"


class CityLocation(models.Model):
    city_id = models.AutoField(primary_key=True)
    city_name = models.CharField(max_length=150)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='cities')
    pincode = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    is_removed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,blank=True,related_name='cities_created')
    updated_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,blank=True,related_name='cities_updated')

    class Meta:
        db_table = 'master_city_location'
        unique_together = ('city_name', 'district')
        ordering = ['city_name']

    def __str__(self):
        return f"{self.city_name}, {self.district.district_name}"
    
    
#admin_info model


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

    member_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=200, db_index=True)
    email_address = models.EmailField(unique=True, db_index=True)
    mobile_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d{10}$', 'Enter a valid 10-digit mobile number')]
    )
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
    
    account_status = models.CharField(
        max_length=30,
        choices=WORKFLOW_STATUS,
        default='PENDING_REVIEW'
    )
    
    two_factor_secret = models.CharField(max_length=80, blank=True, null=True)
    
    registered_at = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='members_created_by_me',
        null=True,
        blank=True
    )
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
    
    # Relations
    user_account = models.OneToOneField(
        PortalUser, 
        on_delete=models.PROTECT, 
        related_name='profile_details',
        null=True,
        blank=True
    )
    hierarchy_node = models.ForeignKey(
        PortalUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    # KYC Fields
    unique_member_code = models.CharField(max_length=12,blank=True, unique=True)
    aadhaar_number = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{12}$', 'Aadhaar must be 12 digits')],
        null=True, blank=True
    )
    pan_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^[A-Z]{5}[0-9]{4}[A-Z]$', 'Invalid PAN format')],
        null=True, blank=True, unique=True
    )
    pan_verification_data = models.JSONField(null=True, blank=True)

    # Business Info
    business_name = models.CharField(max_length=200, null=True, blank=True)
    outlet_photo = models.ImageField(upload_to='outlets/', null=True, blank=True)
    outlet_coordinates = models.JSONField(null=True, blank=True)  # {lat, lng}
    full_address = models.TextField(null=True, blank=True)
    state_ref = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, related_name='+')
    city_ref = models.ForeignKey(CityLocation, on_delete=models.SET_NULL, null=True, related_name='+')
    pincode = models.CharField(max_length=6, validators=[RegexValidator(r'^\d{6}$')], null=True, blank=True)

    # Documents & GST
    supporting_documents = models.JSONField(default=list, blank=True)  # list of file paths
    gstin = models.CharField(max_length=15, null=True, blank=True, unique=True)
    business_category = models.CharField(max_length=20, null=True, blank=True)  # Retail, Wholesale etc.
    secondary_mobile = models.CharField(max_length=10, null=True, blank=True)

    # Current location during KYC
    live_location_capture = models.JSONField(null=True, blank=True)

    # Audit
    created_by_user = models.ForeignKey(
        PortalUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='profiles_created'
    )
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

# models.py

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

    entity_id = models.AutoField(primary_key=True)
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
    registered_state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True)
    registered_city = models.ForeignKey(CityLocation, on_delete=models.SET_NULL, null=True)
    pin_code = models.CharField(max_length=6, null=True, blank=True)
    
    enabled_services = models.JSONField(default=list, blank=True)
    agreement_pdf = models.FileField(upload_to='agreements/', null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_soft_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entities_created_by'
    )
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
        db_table = 'platform_business_entities'
        

class PaymentGatewayBank(models.Model):
    """
    Stores bank account details used for deposits & withdrawals with service-wise charges
    """
    bank_id = models.AutoField(primary_key=True)
    
    # JSON field to store which services/deposit methods this bank supports
    supported_services = models.JSONField(
        default=list,
        help_text="Example: ['UPI', 'IMPS', 'NEFT', 'Cash Deposit']"
    )
    
    bank_full_name = models.CharField(max_length=200, blank=True, null=True)
    ifsc = models.CharField(
        max_length=11,
        validators=[RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$', 'Enter valid IFSC code')],
        blank=True,
        null=True
    )
    branch = models.CharField(max_length=150, blank=True, null=True)
    account_holder_name = models.CharField(max_length=200, blank=True, null=True)
    account_no = models.CharField(max_length=30, blank=True, null=True)
    account_category = models.CharField(max_length=50, blank=True, null=True)  # Savings/Current etc.

    # Charge configuration per channel
    upi_imps_charges = models.JSONField(default=dict, blank=True, null=True)
    cash_deposit_machine_charges = models.JSONField(default=dict, blank=True, null=True)
    over_the_counter_charges = models.JSONField(default=dict, blank=True, null=True)

    # Status & Audit
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        PortalUser,
        on_delete=models.PROTECT,
        related_name='bank_accounts_added',
        null=True,
        blank=True
    )
    modified_on = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        PortalUser,
        on_delete=models.SET_NULL,
        related_name='bank_accounts_modified',
        null=True,
        blank=True
    )

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
    
    # Which deposit methods this bank supports (UPI, IMPS, Cash, etc.)
    enabled_channels = models.JSONField(
        default=list,
        help_text="List of allowed deposit channels e.g. ['UPI', 'NEFT', 'Cash Deposit']"
    )

    bank_title = models.CharField(max_length=180, blank=True, null=True)
    ifsc_code = models.CharField(
        max_length=11,
        validators=[RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$')],
        blank=True,
        null=True,
        unique=True
    )
    branch_location = models.CharField(max_length=200, blank=True, null=True)
    holder_name = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=30, unique=True, blank=True, null=True)
    account_kind = models.CharField(max_length=50, blank=True, null=True)  # Current/Savings

    # Channel-wise charges
    digital_transfer_fees = models.JSONField(default=dict, blank=True, null=True)      # UPI/IMPS/NEFT
    cdm_deposit_fees = models.JSONField(default=dict, blank=True, null=True)
    branch_counter_fees = models.JSONField(default=dict, blank=True, null=True)

    is_enabled = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)

    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        PortalUser,
        on_delete=models.PROTECT,
        related_name='deposit_banks_created',
        null=True,
        blank=True
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        PortalUser,
        on_delete=models.SET_NULL,
        related_name='deposit_banks_updated',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'config_deposit_banks'
        verbose_name = 'Deposit Bank Account'
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.bank_title or 'Unnamed Bank'} - {self.account_number or 'N/A'}"



# models.py (same file ya alag rakh sakte ho)

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
    
    deposit_methods = models.JSONField(
        default=list,
        help_text="Which methods used: ['UPI', 'Cash Deposit']"
    )
    
    linked_bank = models.ForeignKey(
        DepositBankAccount,
        on_delete=models.PROTECT,
        related_name='deposit_requests'
    )
    
    deposit_amount = models.DecimalField(max_digits=15, decimal_places=2)
    reference_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    utr_ref = models.CharField(max_length=50, unique=True, blank=True, null=True, db_index=True)
    
    transfer_mode = models.CharField(
        max_length=20,
        choices=TransactionMode.choices,
        blank=True,
        null=True
    )
    
    proof_documents = models.JSONField(
        default=list,
        help_text="List of uploaded proof URLs or file keys"
    )
    
    user_remarks = models.TextField(blank=True, null=True)
    admin_reasons = models.TextField(blank=True, null=True)

    status = models.CharField(
    max_length=20,
    choices=FundRequestStatus.choices,
    default=FundRequestStatus.PENDING
    )


    is_void = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(
        PortalUser,
        on_delete=models.PROTECT,
        related_name='fund_requests_made',
        null=True,
        blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        PortalUser,
        on_delete=models.SET_NULL,
        related_name='fund_requests_reviewed',
        null=True,
        blank=True
    )

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

from django.db import models

class MemberActionLog(models.Model):
    """
    Tracks all user actions across the platform
    Same logic as UserActivity but completely fresh & clean
    """
    log_id = models.AutoField(primary_key=True)
    
    record_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    module_name = models.CharField(max_length=100, db_index=True, null=True, blank=True)
    
    action_type = models.CharField(max_length=80, db_index=True)  # LOGIN, CREATE, UPDATE, DELETE, APPROVE etc.
    action_details = models.TextField(blank=True, null=True)
    
    performed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    performed_by = models.ForeignKey(PortalUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_logs'
    )
    
    request_payload = models.JSONField(null=True, blank=True)   # Better than TextField
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


# models.py

from django.db import models
from decimal import Decimal

# Choices (same logic as MrkTyChoice)
TRANSACTION_NATURE = [
    ('CR', 'Credit'),
    ('DR', 'Debit'),
]

class GlTrn(models.Model):
    """
    Global Ledger - Har transaction ka master record (jaise GL)
    """
    entry_id = models.AutoField(primary_key=True)
    
    linked_service_id = models.BigIntegerField(null=True, blank=True)
    member = models.ForeignKey(
       PortalUser,
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='ledger_entries'
    )

    transaction_type = models.CharField(max_length=100, blank=True)  # Fund Request, Payout, Refund etc.
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    tds_percent = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0000'))
    gst_percent = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.0000'))
    tds_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    source_table = models.CharField(max_length=100, blank=True)  # jahan se transaction aaya
    wallet_type = models.CharField(max_length=30, blank=True)     # MAIN, BONUS, etc.
    
    final_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    entry_nature = models.CharField(max_length=6, choices=TRANSACTION_NATURE)  # CR / DR

    transaction_time = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_ledger_entries'
        ordering = ['-recorded_at']

    def __str__(self):
        return f"Ledger #{self.entry_id} | ₹{self.amount} | {self.get_entry_nature_display()}"


class WalletHistory(models.Model):
    """
    Wallet ka har credit/debit ka record
    """
    history_id = models.AutoField(primary_key=True)
    
    reference_id = models.BigIntegerField(null=True, blank=True)   # kisi service se linked
    action_name = models.CharField(max_length=150)                 # "Fund Added", "Commission", "Payout"

    user = models.ForeignKey(
        PortalUser,
        on_delete=models.PROTECT,
        related_name='wallet_history'
    )

    wallet_name = models.CharField(max_length=50)                  # MAIN_WALLET, REWARD_WALLET
    changed_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    change_type = models.CharField(max_length=6, choices=TRANSACTION_NATURE)  # CR or DR

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
    # oc_name
    category = models.CharField(max_length=60, blank=True, null=True)   # charge_type
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
    """Stores multiple wallet balances for each portal user"""
    
    balance_id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        PortalUser,
        on_delete=models.PROTECT,
        related_name='wallet_account',
        db_column='portal_user_id',
        null=True,
        blank=True
    )

    # Main wallets
    primary_balance = models.DecimalField(
        max_digits=20, decimal_places=3, default=0.000, help_text="Main usable wallet"
    )
    earnings_balance = models.DecimalField(
        max_digits=20, decimal_places=3, default=0.000, help_text="Commission / Referral earnings"
    )

    # Optional / special purpose wallets
    deposit_balance = models.DecimalField(
        max_digits=20, decimal_places=3, default=0.000, null=True, blank=True
    )
    gateway_balance = models.DecimalField(
        max_digits=20, decimal_places=3, default=0.000, null=True, blank=True
    )
    outstanding_balance = models.DecimalField(
        max_digits=20, decimal_places=3, default=0.000, null=True, blank=True
    )
    hold_balance = models.DecimalField(
        max_digits=20, decimal_places=3, default=0.000, null=True, blank=True, help_text="Lien / Frozen amount"
    )

    # Audit fields
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
        """Helper to calculate total usable balance"""
        return (
            self.primary_balance +
            self.earnings_balance +
            (self.deposit_balance or 0) +
            (self.gateway_balance or 0) +
            (self.outstanding_balance or 0)
        )
        




class SaAdditionalFee(models.Model):
    fee_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=150, blank=True, null=True)
    # oc_name
    category = models.CharField(max_length=60, blank=True, null=True)   # charge_type
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
    




class SaCoreService(models.Model):
    service_key = models.AutoField(primary_key=True)
    title = models.CharField(max_length=80, unique=True)
    routing_order = models.JSONField(null=True, blank=True)  # same as priority
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

    vendor_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(SaCoreService, on_delete=models.CASCADE, related_name='vendors')
    vendor_code = models.CharField(max_length=100, unique=True)
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
        db_table = 'service_vendors'

    def __str__(self):
        return f"{self.display_label} ({self.vendor_code})"




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