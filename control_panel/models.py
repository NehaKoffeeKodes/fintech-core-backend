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
    region_name = models.CharField(max_length=120, unique=True, db_index=True)
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
        return self.region_name

    def clean(self):
        if self.short_code:
            self.short_code = self.short_code.upper()


class Location(models.Model): 
    locality_id = models.AutoField(primary_key=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='localities')
    city_name = models.CharField(max_length=150)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'master_locations'
        unique_together = ('city_name', 'region')
        verbose_name = 'Locality'
        verbose_name_plural = ' Locations'
        indexes = [
            models.Index(fields=['city_name', 'region']),
        ]

    def __str__(self):
        return f"{self.city_name} ({self.region.name})"



class Servicedispute(models.Model):
    complaint_id = models.AutoField(primary_key=True)
    provider_id = models.IntegerField(null=True, blank=True)                
    txn_ref = models.CharField(max_length=255, null=True, blank=True)       
    admin = models.IntegerField(null=True, blank=True)                      
    database_name = models.CharField(max_length=255, null=True, blank=True)
    txn_amount = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)  
    retailer_notes = models.TextField(null=True, blank=True)                
    admin_notes = models.TextField(null=True, blank=True)                   
    created_on = models.DateTimeField(auto_now_add=True)                    
    created_by_user = models.IntegerField(null=True, blank=True)           
    updated_on = models.DateTimeField(null=True, blank=True)               
    updated_by_user = models.IntegerField(null=True, blank=True)            

    class Meta:
        db_table = 'sa_service_complaint'         
        app_label = 'control_panel'               
        ordering = ['-created_on']

    def __str__(self):
        return f"Complaint {self.complaint_id} - {self.txn_ref or 'N/A'}"
  



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
    service_provider = models.ForeignKey(ServiceProvider,on_delete=models.CASCADE,related_name='charges')
    charges_type = models.CharField(max_length=2,choices=CHARGE_TYPE_CHOICES)
    rate_type = models.CharField(max_length=20,choices=RATE_TYPE_CHOICES)
    minimum = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    maximum = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    rate = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    identifier_id = models.IntegerField(null=True,blank=True,)
    charge_category = models.CharField(max_length=20,choices=CATEGORY_CHOICES,default=TO_US)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,blank=True,db_column='updated_by',related_name='updated_charges')
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
    name = models.CharField(max_length=150, unique=True)
    mobile_number = models.CharField(max_length=10, unique=True)
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
    charges = models.ManyToManyField(Charges,blank=True,related_name='admins')
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
        return f"{self.name} ({self.get_status_display()})"

    class Meta:
        db_table = 'admin'
        
  

class AdminService(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    admin = models.ForeignKey(Admin,on_delete=models.CASCADE,related_name='assigned_services',null=True,blank=True)
    service = models.ForeignKey(SaCoreService,on_delete=models.PROTECT,related_name='admin_assignments')
    provider = models.ForeignKey(ServiceProvider,on_delete=models.PROTECT,related_name='admin_service_links')
    commission_structure = models.JSONField(default=dict,blank=True)
    commission_rate = models.DecimalField(max_digits=8,decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,related_name='service_assignments_created')
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
    created_by = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL, null=True, related_name='created_contracts')
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
        


class SaCoreServiceIdentifier(models.Model):
    config_id = models.AutoField(primary_key=True)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    settings = models.JSONField(null=True, blank=True)  
    last_updated = models.DateTimeField(auto_now=True)  
    updated_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,blank=True,db_column='updated_by')
    disabled = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'sa_provider_config'
        app_label = 'control_panel'
        verbose_name = 'Provider Configuration'
        verbose_name_plural = 'Provider Configurations'
        ordering = ['-last_updated']

    def __str__(self):
        return f"Config for {self.provider.sp_name if self.provider else 'No Provider'} (ID: {self.config_id})"
    
    
            


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
    updated_by = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL,null=True,related_name='modified_charge_rules')
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




class ProductItemCategory(models.Model):
    cat_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    parent_cat = models.IntegerField(null=True, blank=True)  
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(AdminAccount,related_name='categories_added',on_delete=models.CASCADE,db_column='added_by')
    modified_on = models.DateTimeField(null=True, blank=True)
    modified_by = models.ForeignKey(AdminAccount,related_name='categories_modified',on_delete=models.CASCADE,null=True,blank=True,db_column='modified_by')
    inactive = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'sa_item_category'
        app_label = 'control_panel'
        verbose_name = 'Item Category'
        verbose_name_plural = 'Item Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_full_path(self):
        path = [self.name]
        parent = self.parent_cat
        while parent:
            try:
                parent_obj = ProductItemCategory.objects.get(cat_id=parent)
                path.append(parent_obj.name)
                parent = parent_obj.parent_cat
            except ProductItemCategory.DoesNotExist:
                break
        return ' > '.join(reversed(path))
    

class ProductItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(ProductItemCategory, on_delete=models.CASCADE)  # Assuming ProductCategory exists
    manufacturer = models.CharField(max_length=255)
    item_model = models.CharField(max_length=255)
    unique_serial = models.CharField(max_length=255, null=True, blank=True)
    purchase_date = models.DateField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_count = models.IntegerField()
    details = models.TextField(null=True, blank=True)
    images = models.JSONField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(AdminAccount, related_name='items_added', on_delete=models.CASCADE, db_column='added_by')
    modified_on = models.DateTimeField(null=True, blank=True)
    modified_by = models.ForeignKey(AdminAccount, related_name='items_modified', on_delete=models.CASCADE, null=True, blank=True, db_column='modified_by')
    removed = models.BooleanField(default=False)
    inactive = models.BooleanField(default=False)

    class Meta:
        db_table = 'sa_inventory_item'
        app_label = 'control_panel'

    def __str__(self):
        return f"{self.manufacturer} {self.item_model}"



class LimitConfig(models.Model):
    rule_id = models.AutoField(primary_key=True)
    admin = models.ForeignKey(Admin, on_delete=models.PROTECT, null=True, blank=True)
    provider = models.ForeignKey(ServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    
    max_per_transaction = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_daily_total = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    max_monthly_total = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    
    max_daily_transactions = models.PositiveIntegerField(null=True, blank=True)
    max_monthly_transactions = models.PositiveIntegerField(null=True, blank=True)
    
    is_enabled = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'limit_config'
        app_label = 'control_panel'


    def __str__(self):
        return f"Rule {self.rule_id} - User: {self.user_account} | Provider: {self.provider}"
    
  
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
    
    


class CostEntry(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Card Payment'),
        ('transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('digital', 'Digital Payment'),
        ('misc', 'Miscellaneous'),
    ]

    TAX_STATUS_CHOICES = [
        ('with_tax', 'With Tax'),
        ('without_tax', 'Without Tax'),
    ]

    entry_id = models.AutoField(primary_key=True)
    entry_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    tax_status = models.CharField(max_length=20, choices=TAX_STATUS_CHOICES)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    tax_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    vendor_name = models.CharField(max_length=200, blank=True, null=True)
    vendor_gst = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField()
    documents = models.JSONField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(AdminAccount, related_name='costs_created', on_delete=models.PROTECT)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(AdminAccount, related_name='costs_updated', on_delete=models.PROTECT, null=True, blank=True)
    is_removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'finance_cost_entries'
        ordering = ['-entry_date']

    def __str__(self):
        return f"Cost #{self.entry_id} - {self.entry_date.strftime('%d %b %Y')}"
    
    

class GadgetCategory(models.Model):
    cat_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    parent = models.IntegerField(null=True, blank=True)
    details = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.IntegerField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    inactive = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'sa_gadget_category'
        app_label = 'control_panel'

    def __str__(self):
        return self.name


class GadgetItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(GadgetCategory, on_delete=models.PROTECT, null=True, blank=True)
    title = models.CharField(max_length=100)
    info = models.TextField(blank=True, null=True)
    model_code = models.CharField(max_length=100, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    available_stock = models.IntegerField(blank=True, null=True)
    images = models.JSONField(blank=True, null=True)
    disabled = models.BooleanField(default=False)
    soft_deleted = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(blank=True, null=True)
    modified_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'sa_gadget_item'
        app_label = 'control_panel'

    def __str__(self):
        return self.title




class ChargeCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100, unique=True)
    added_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(AdminAccount,on_delete=models.SET_NULL,null=True,related_name='charge_categories_created')
    is_removed = models.BooleanField(default=False)

    class Meta:
        db_table = 'master_charge_categories'
        ordering = ['-category_id']
        verbose_name = 'Charge Category'
        verbose_name_plural = 'Charge Categories'

    def __str__(self):
        return self.category_name
    
    

class ItemSerial(models.Model):
    serial_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(GadgetItem, on_delete=models.PROTECT, null=True, blank=True)
    serial_code = models.CharField(max_length=255, unique=True)
    assigned_user = models.IntegerField(null=True, blank=True)
    deactivated = models.BooleanField(blank=True, null=True)
    deleted = models.BooleanField(default=False)
    created_by = models.IntegerField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'sa_item_serial'
        app_label = 'control_panel'

    def __str__(self):
        return self.serial_code


class GadgetPurchase(models.Model):
    purchase_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(GadgetItem, on_delete=models.PROTECT, null=True, blank=True)
    buyer_name = models.CharField(max_length=255, null=True, blank=True)
    buyer_phone = models.CharField(max_length=255, null=True, blank=True)
    per_unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    ordered_qty = models.IntegerField()
    remaining_qty = models.IntegerField(blank=True, null=True)
    allocated_serials = models.JSONField(null=True, blank=True)
    order_ref = models.CharField(max_length=100, unique=True)
    tracking_no = models.CharField(max_length=100, null=True, blank=True)
    shipping_partner = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'),
                                                     ('PARTIALLY APPROVED', 'Partially Approved'),
                                                     ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled')],
                              default='PENDING')
    expected_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    initiated_by = models.IntegerField(blank=True, null=True)
    initiated_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'sa_gadget_purchase'
        app_label = 'control_panel'

    def __str__(self):
        return self.order_ref