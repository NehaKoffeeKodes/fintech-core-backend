from rest_framework import serializers
from .models import*


class AdminSerializer(serializers.ModelSerializer):
    account_status = serializers.SerializerMethodField()
    tax_category_label = serializers.CharField(source='get_tax_category_display', read_only=True)
    assigned_services = serializers.SerializerMethodField()
    document_bundle = serializers.SerializerMethodField(source='document_bundle', read_only=True)
    contract_value = serializers.SerializerMethodField()
    tax_on_contract = serializers.SerializerMethodField()
    net_payable = serializers.SerializerMethodField()
    contract_approval_status = serializers.SerializerMethodField()

    class Meta:
        model = Admin
        fields = '__all__'
        read_only_fields = ('joined_on', 'last_modified', 'created_by_user', 'modified_by_user')

    def get_account_status(self, obj):
        return "Enabled" if obj.is_active else "Disabled"

    def get_contract_value(self, obj):
        try:
            contract = AdminContract.objects.get(admin=obj)
            return AdminContractSerializer(contract).data.get('base_amount')
        except AdminContract.DoesNotExist:
            return None

    def get_tax_on_contract(self, obj):
        try:
            contract = AdminContract.objects.get(admin=obj)
            base = float(AdminContractSerializer(contract).data.get('base_amount', 0))
            gst = round(base * 0.18, 2)
            return str(gst)
        except AdminContract.DoesNotExist:
            return None

    def get_net_payable(self, obj):
        try:
            contract = AdminContract.objects.get(admin=obj)
            base = float(contract.base_amount or 0)
            total = base + (base * 0.18)
            return str(round(total, 2))
        except AdminContract.DoesNotExist:
            return None

    def get_contract_approval_status(self, obj):
        try:
            contract = AdminContract.objects.get(admin=obj)
            return AdminContractSerializer(contract).data.get('approval_status')
        except AdminContract.DoesNotExist:
            return None

    def get_assigned_services(self, obj):
        services = obj.services_offered.filter(is_active=True, is_deleted=False)
        return AdminServiceDetailSerializer(services, many=True, context=self.context).data

    def get_document_bundle(self, instance):
        request = self.context.get('request')
        if not request or not instance.document_bundle:
            return {}

        base_url = f"https://{request.get_host()}" if request.is_secure() else f"http://{request.get_host()}"
        media_root = settings.MEDIA_URL

        updated_docs = {}
        for key, file_path in instance.document_bundle.items():
            clean_path = str(file_path).replace('\\', '/')
            updated_docs[key] = f"{base_url}{media_root}{clean_path}"
        return updated_docs

    def validate_business_name(self, value):
        if 'test' in value.lower() or 'demo' in value.lower():
            raise serializers.ValidationError("Business name cannot contain restricted words like 'test' or 'demo'.")
        return value.strip()

    def validate(self, attrs):
        instance = self.instance
        is_create = not bool(instance)

        mandatory = ['business_name', 'mobile', 'email_id', 'firm_name', 'state', 'district', 'pin_code']
        errors = {}

        if is_create:
            for field in mandatory:
                if not attrs.get(field):
                    errors[field] = f"{field.replace('_', ' ').title()} is mandatory."
        else:
            for field in mandatory:
                if field in attrs and not attrs[field]:
                    errors[field] = f"{field.replace('_', ' ').title()} cannot be empty."

        if attrs.get('pan_number') and len(attrs['pan_number']) != 10:
            errors['pan_number'] = "PAN must be exactly 10 characters."

        if attrs.get('aadhaar_number') and len(attrs['aadhaar_number']) != 12:
            errors['aadhaar_number'] = "Aadhaar must be exactly 12 digits."

        uploaded_file = attrs.get('logo_image')
        if uploaded_file and uploaded_file.size > 15 * 1024 * 1024:
            errors['logo_image'] = "Logo size should not exceed 15MB."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        remove_keys = self.context.get('remove_fields', [])
        for key in remove_keys:
            data.pop(key, None)
        return data
    
    
class AdminContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminContract
        fields = '__all__'

    def validate_base_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Contract value must be positive.")
        return value

    def validate(self, data):
        if not self.instance:  
            if 'base_amount' not in data:
                raise serializers.ValidationError({"base_amount": "This field is required."})
        else: 
            current_amount = self.instance.base_amount or 0
            new_amount = data.get('base_amount', current_amount)
            current_gst = self.instance.gst_component or 0
            new_gst = data.get('gst_component', current_gst)

            if new_gst > new_amount:
                raise serializers.ValidationError("GST component cannot exceed base contract amount.")

        return data

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.gst_component = float(instance.base_amount) * 0.18
        instance.save(update_fields=['gst_component'])
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if 'base_amount' in validated_data:
            instance.gst_component = float(instance.base_amount) * 0.18
            instance.save(update_fields=['gst_component'])
        return instance

class ServiceProviderSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    service = serializers.PrimaryKeyRelatedField(
        queryset=SaCoreService.objects.all(),
        required=True,
        error_messages={'required': 'Service selection is mandatory.'}
    )
    hsn_sac = serializers.PrimaryKeyRelatedField(
        queryset=GSTCode.objects.all(),
        required=False,
        allow_null=True
    )
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=AdminAccount.objects.all(),
        required=False,
        allow_null=True
    )
    service_name = serializers.CharField(source='service.service_name', read_only=True)
    hsn_details = serializers.SerializerMethodField()
    charge_rules = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = '__all__'
        read_only_fields = ('provider_id', 'created_at', 'updated_at', 'is_deleted')

    def get_status(self, obj):
        return "Operational" if not obj.is_deactive else "Disabled"

    def get_hsn_details(self, obj):
        if not obj.hsn_sac:
            return None
        exclude = ["created_at", "updated_at", "created_by", "updated_by", "is_deleted", "description"]
        return GSTCodeManagerSerializer(
            obj.hsn_sac,
            context={'exclude_fields': exclude}
        ).data

    def get_charge_rules(self, obj):
        charges = ChargeRule.objects.filter(
            service_provider=obj,
            is_deleted=False
        )
        return ChargeRuleSerializer(
            charges,
            many=True,
            context={'exclude_fields': ["created_at", "updated_at", "updated_by", "is_deleted"]}
        ).data

    def validate(self, attrs):
        errors = {}
        required_on_create = ['provider_name', 'display_label', 'service', 'tds_rule']
        required_on_update = ['provider_name', 'display_label', 'service']

        if not self.instance:  
            for field in required_on_create:
                if not attrs.get(field):
                    errors[field] = f"{field.replace('_', ' ').title()} is required."
        else:  
            for field in required_on_update:
                if field in attrs and not attrs.get(field):
                    errors[field] = f"{field.replace('_', ' ').title()} cannot be blank."

        if attrs.get('hsn_sac') is None and not self.instance:
            errors['hsn_sac'] = "HSN/SAC code is required on creation."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def validate_service(self, value):
        if not SaCoreService.objects.filter(pk=value.pk, is_active=True).exists():
            raise serializers.ValidationError("Selected service is not available or inactive.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.service:
            data['service_name'] = instance.service.service_name

        if instance.hsn_sac:
            data['hsn_sac'] = self.get_hsn_details(instance)

        default_exclude = ['created_at', 'updated_at', 'updated_by', 'is_deleted']
        custom_exclude = self.context.get('exclude_fields', [])
        for field in set(default_exclude + custom_exclude):
            data.pop(field, None)

        return data
    
    
    
class SmtpEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmtpEmail
        fields = [
            'id', 'service_type', 'smtp_server', 'smtp_port', 'encryption',
            'sender_email', 'sender_password', 'is_active'
        ]
        read_only_fields = ('id',)
        extra_kwargs = {
            'sender_password': {'write_only': True},  
        }

    def validate_smtp_port(self, value):
        if value is None:
            raise serializers.ValidationError("SMTP port is required.")
        if not (1 <= value <= 65535):
            raise serializers.ValidationError("Port must be between 1 and 65535.")
        return value

    def validate_encryption(self, value):
        if value not in ['SSL', 'TLS']:
            raise serializers.ValidationError("Encryption must be either 'SSL' or 'TLS'.")
        return value

    def validate(self, data):
        instance_exists = self.instance is not None
        errors = {}

        required = ['smtp_server', 'smtp_port', 'sender_email', 'sender_password', 'encryption']

        for field in required:
            value = data.get(field)
            old_value = getattr(self.instance, field, None) if instance_exists else None

            if (not instance_exists and value in [None, '']) or \
               (instance_exists and field in data and value in [None, '']):
                errors[field] = f"{field.replace('_', ' ').title()} is required."

        if 'smtp_port' in data and (data['smtp_port'] < 1 or data['smtp_port'] > 65535):
            errors['smtp_port'] = "Invalid port range."

        if errors:
            raise serializers.ValidationError(errors)

        return data
    
    

class SaCoreServiceSerializer(serializers.ModelSerializer):
    service_status = serializers.SerializerMethodField()

    class Meta:
        model = SaCoreService
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'updated_by')

    def get_service_status(self, obj):
        return "Live" if obj.is_active else "Suspended"

    def validate(self, attrs):
        if self.instance and 'service_name' in attrs and not attrs['service_name'].strip():
            raise serializers.ValidationError({"service_name": "Service name cannot be empty."})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        for field in exclude:
            data.pop(field, None)
        return data
    


class AdminServiceDetailSerializer(serializers.ModelSerializer):
    service = serializers.PrimaryKeyRelatedField(
        queryset=SaCoreService.objects.all(),
        write_only=True
    )
    provider = serializers.PrimaryKeyRelatedField(
        queryset=ServiceProvider.objects.all(),
        write_only=True
    )
    service_details = SaCoreServiceSerializer(source='service', read_only=True)
    provider_info = ServiceProviderSerializer(source='provider', read_only=True)

    class Meta:
        model = AdminService
        fields = [
            'assignment_id', 'admin', 'service', 'provider',
            'commission_structure', 'commission_rate',
            'service_details', 'provider_info',
            'is_suspended', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = [
            'assignment_id', 'created_at', 'updated_at', 'created_by'
        ]

    def validate(self, attrs):
        required_fields = ['service', 'provider']
        errors = {}

        for field in required_fields:
            if not attrs.get(field):
                errors[field] = "This field is mandatory."

        if errors:
            raise serializers.ValidationError(errors)

        admin = self.context['request'].user.admin_profile  
        service = attrs['service']
        provider = attrs['provider']

        if self.instance is None:  # Only on create
            exists = AdminService.objects.filter(
                admin=admin,
                service=service,
                provider=provider,
                is_removed=False
            ).exists()
            if exists:
                raise serializers.ValidationError({
                    "non_field_errors": ["This service from this provider is already assigned."]
                })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [
            'created_at', 'updated_at', 'created_by', 'is_removed'
        ])

        for field in exclude:
            data.pop(field, None)
        data.pop('service', None)
        data.pop('provider', None)

        return data    
    


class GSTCodeManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GSTCode
        fields = '__all__'
        read_only_fields = ('gst_id', 'added_on', 'added_by', 'updated_at', 'updated_by')

    def validate_gst_code(self, value):
        value = value.strip().upper()
        if self.instance:
            if GSTCode.objects.filter(gst_code=value).exclude(gst_id=self.instance.gst_id).exists():
                raise serializers.ValidationError("This GST code already exists.")
        else:
            if GSTCode.objects.filter(gst_code=value).exists():
                raise serializers.ValidationError("This GST code already exists.")
        return value

    def validate(self, data):
        if not self.instance:  
            if not data.get('gst_code'):
                raise serializers.ValidationError("GST Code is required.")
            if 'cgst' not in data or data['cgst'] is None:
                raise serializers.ValidationError("CGST rate is required.")
        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        for f in exclude:
            ret.pop(f, None)
        return ret
    
   



class LocationDataSerializer(serializers.ModelSerializer):    
    class Meta:
        model = None 
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'added_on', 'modified_on')

    def __init__(self, *args, **kwargs):
        model = kwargs.pop('model', None)
        super().__init__(*args, **kwargs)
        if model:
            self.Meta.model = model

    def to_representation(self, instance):
        try:
            data = super().to_representation(instance)
            fields_to_remove = self.context.get('remove_fields', [])
            
            if isinstance(fields_to_remove, (list, tuple, set)):
                for field_name in fields_to_remove:
                    data.pop(field_name, None)
                    
            return data
            
        except Exception as e:
            return {"error": "Serialization failed", "detail": str(e)}
        
    
    


class FundRequestSerializer(serializers.ModelSerializer):
    bank_info = serializers.SerializerMethodField()
    proof_image_url = serializers.SerializerMethodField()

    class Meta:
        model = FundDepositRequest  
        exclude = ['is_removed', 'reviewed_by']

    def get_bank_info(self, obj):
        try:
            bank = obj.linked_bank
            return {
                "name": bank.bank_title,
                "account": bank.account_number,
                "ifsc": bank.ifsc_code
            }
        except:
            return None

    def get_proof_image_url(self, obj):
        proof = obj.proof_documents
        if not proof or not proof.get('payment_proof'):
            return None

        request = self.context.get('request')
        if not request:
            return None

        file_name = proof['payment_proof'].split('/')[-1]
        return f"{request.scheme}://{request.get_host()}/media/documents/{file_name}"
    
    


class ChargeRuleSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    provider_label = serializers.CharField(source='service_provider.label', read_only=True)
    service_name = serializers.CharField(source='service.service.service_name', read_only=True, allow_null=True)

    class Meta:
        model = ChargeRule
        fields = [
            'rule_id', 'service_provider', 'provider_label', 'service_name',
            'charge_type', 'rate_mode', 'rate_value',
            'min_amount', 'max_amount', 'linked_identifier',
            'charge_beneficiary', 'status',
            'created_at', 'updated_at', 'updated_by', 'is_disabled'
        ]
        read_only_fields = ('rule_id', 'created_at', 'updated_at', 'updated_by')

    def get_status(self, obj):
        if obj.is_deleted:
            return "Deleted"
        return "Active" if not obj.is_disabled else "Disabled"

    def validate(self, attrs):
        rate_value = attrs.get('rate_value')
        rate_mode = attrs.get('rate_mode')
        min_amount = attrs.get('min_amount')
        max_amount = attrs.get('max_amount')

        if rate_value is None or rate_value < 0:
            raise serializers.ValidationError({
                "rate_value": "Charge rate must be a positive number."
            })

        if rate_mode == 'PERCENT' and rate_value > 100:
            raise serializers.ValidationError({
                "rate_value": "Percentage rate cannot exceed 100%."
            })

        if min_amount and max_amount and min_amount > max_amount:
            raise serializers.ValidationError({
                "min_amount": "Minimum amount cannot be greater than maximum amount."
            })

        if rate_mode == 'FLAT' and min_amount and rate_value < min_amount:
            raise serializers.ValidationError({
                "rate_value": "Flat rate cannot be less than minimum cap."
            })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        default_exclude = ['updated_by', 'is_deleted']
        
        for field in set(exclude + default_exclude):
            data.pop(field, None)
            
        data['charge_type_label'] = instance.get_charge_type_display()
        data['rate_mode_label'] = instance.get_rate_mode_display()
        data['beneficiary_label'] = instance.get_charge_beneficiary_display()

        return data
    


class SaAdditionalChargesSerializer(serializers.ModelSerializer):
    tax_info = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_is_active_display', read_only=True)

    class Meta:
        model = AdditionalFee
        exclude = ['is_removed', 'added_on', 'added_by']

    def get_tax_info(self, obj):
        if obj.gst_code:
            return f"{obj.gst_code.code} ({obj.gst_code.rate}%)"
        return "No Tax"





class DocumentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = [
            'template_id', 'display_name', 'internal_code',
            'slug_key', 'mandatory', 'active', 'added_on'
        ]
        read_only_fields = ['template_id', 'added_on']

    def validate_internal_code(self, value):
        if self.instance and self.instance.internal_code == value:
            return value
        if DocumentTemplate.objects.filter(internal_code=value, soft_deleted=False).exists():
            raise ValidationError("This internal code already exists.")
        return value

    def validate_slug_key(self, value):
        if ' ' in value:
            raise ValidationError("Slug key cannot contain spaces.")
        if '-' not in value and '_' not in value:
            raise ValidationError("Slug should use hyphens (-) or underscores (_).")
        return value

    def validate(self, data):
        display_name = data.get('display_name')
        slug_key = data.get('slug_key')

        if display_name and not display_name.strip():
            raise ValidationError({"display_name": "Display name cannot be empty."})

        if not slug_key:
            raise ValidationError({"slug_key": "Slug key is mandatory."})

        if DocumentTemplate.objects.filter(slug_key=slug_key, soft_deleted=False)\
                                 .exclude(pk=getattr(self.instance, 'pk', None)).exists():
            raise ValidationError({"slug_key": "This slug is already taken."})

        return data

    def update(self, instance, validated_data):
        instance.display_name = validated_data.get('display_name', instance.display_name)
        instance.internal_code = validated_data.get('internal_code', instance.internal_code)
        instance.slug_key = validated_data.get('slug_key', instance.slug_key)
        instance.mandatory = validated_data.get('mandatory', instance.mandatory)
        instance.active = validated_data.get('active', instance.active)
        instance.modified_on = __import__('datetime').datetime.now()
        instance.save()
        return instance
