from django.db import models
from control_panel.models import*



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
        app_label = 'customers'
        ordering = ['-joined_on']
   


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
        app_label = 'charges'
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
        app_label = 'master'
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
        app_label = 'customers'
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
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'
        

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
        app_label = 'customers'
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
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'
        


class ElectricityCategory(models.Model):
    provider_id = models.AutoField(primary_key=True)
    board_name = models.CharField(max_length=200,unique=True)
    short_code = models.CharField(max_length=15,unique=True,blank=True,null=True)
    operator_code = models.CharField(max_length=50,blank=True,null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,null=True,blank=True,related_name='electricity_categories_added')

    class Meta:
        db_table = 'utility_electricity_boards'
        app_label = 'utilities'
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
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'



class GasCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=250,unique=True)
    provider_key = models.CharField(max_length=20,unique=True,blank=True,null=True)
    gateway_code = models.CharField(max_length=30,blank=True,null=True) 
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(PortalUser,on_delete=models.PROTECT,null=True,blank=True,related_name='gas_categories_created')

    class Meta:
        db_table = 'utility_gas_companies'
        app_label = 'utilities'
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
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'
   
   
   

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
        app_label = 'banks'
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
        app_label = 'transactions'
        



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
        app_label = 'bulkpe'
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
        app_label = 'bulkpe'
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
        app_label = 'bulkpe'
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
    vendor = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    transfer_amount = models.CharField(max_length=20, blank=True)
    utr_number = models.CharField(max_length=50, blank=True)
    payout_result = models.CharField(max_length=30, default='PROCESSING')
    batch_result = models.CharField(max_length=30, default='PROCESSING')
    payout_mode = models.CharField(max_length=15, blank=True)
    vendor_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    initiated_by = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True)

    class Meta:
        db_table = 'txn_bulk_payout'
        app_label = 'transactions'
        
        
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
    vendor = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    bill_status = models.CharField(max_length=30, default='PENDING')
    bill_time = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_airtel_cms'
        app_label = 'transactions'
        
    
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
        app_label = 'transactions'
        
        
class MicroAtmEntry(models.Model):
    entry_id = models.AutoField(primary_key=True)
    txn_ref = models.CharField(max_length=100, blank=True)
    vendor = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    mobile_no = models.CharField(max_length=10, blank=True)
    txn_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    card_last6 = models.CharField(max_length=20, blank=True)
    api_response = models.JSONField(default=dict)
    current_status = models.CharField(max_length=30, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_micro_atm'
        app_label = 'transactions'
        
        
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
        app_label = 'transactions'
  
 

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
        app_label = 'digikhata'
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
        app_label = 'digikhata'
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
    vendor = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    api_response = models.JSONField(default=dict)
    transfer_time = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    initiated_by = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = 'txn_digikhata'
        app_label = 'transactions'