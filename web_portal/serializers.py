from rest_framework import serializers
from .models import*
from django.conf import settings


class EmailInputSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class OTPInputSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, min_length=6, required=True)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        min_length=8,
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate_new_password(self, value):
        if value.isdigit():
            raise serializers.ValidationError("Password cannot be entirely numeric.")
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

    # new_password_confirm = serializers.CharField(write_only=True)
    #
    # def validate(self, data):
    #     if data['new_password'] != data['new_password_confirm']:
    #         raise serializers.ValidationError("Passwords do not match.")
    #     return data
    
    

class AdminbannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adminbanner
        exclude = ['is_deleted', 'added_by', 'created_at', 'modified_at']
        


class AboutusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aboutus
        fields = [
            'overview_id', 'company_story', 'core_values',
            'leadership_message', 'future_goals',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['overview_id', 'created_at', 'updated_at']

    def validate(self, attrs):
        if not self.instance and Aboutus.objects.exists():
            raise serializers.ValidationError({
                "error": "Only one Company Overview entry is allowed. Use update instead."
            })

        meaningful_fields = ['company_story', 'core_values', 'leadership_message', 'future_goals']
        filled = any(attrs.get(field) for field in meaningful_fields if attrs.get(field))

        if not filled and not self.instance:
            raise serializers.ValidationError({
                "error": "At least one section (story, values, message, goals) must be provided."
            })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and getattr(request, 'public_view', False):
            for field in ['created_at', 'updated_at', 'is_active']:
                data.pop(field, None)
        return data
    

class LatestAnnouncementSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    document_links = serializers.SerializerMethodField()

    class Meta:
        model = Latest_announcement
        fields = [
            'news_id', 'headline', 'details', 'external_url',
            'publish_date', 'is_hidden', 'documents', 'document_links',
            'posted_by', 'posted_at', 'last_modified', 'status_label'
        ]
        read_only_fields = ['news_id', 'posted_at', 'last_modified', 'posted_by', 'status_label']

    def get_document_links(self, obj):
        request = self.context.get('request')
        if not obj.documents or not request:
            return []
        base_url = request.build_absolute_uri(settings.MEDIA_URL)
        return [base_url.rstrip('/') + '/' + path.lstrip('/') for path in obj.documents]

    def get_status_display(self, obj):
        return "Live" if not obj.is_hidden else "Archived"

    def validate_headline(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("News headline is mandatory.")
        if len(value) > 300:
            raise serializers.ValidationError("Headline cannot exceed 300 characters.")
        return value.strip()

    def validate_details(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("News details must be at least 10 characters.")
        return value.strip()
    
    

class ContactSupportSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_current_status_display', read_only=True)
    days_old = serializers.SerializerMethodField()

    class Meta:
        model = ContactSupport
        fields = [
            'ticket_id', 'customer_name', 'customer_email', 'phone_number',
            'issue_title', 'issue_description', 'current_status', 'status_display',
            'submitted_at', 'last_updated', 'handled_by', 'days_old'
        ]
        read_only_fields = ['ticket_id', 'submitted_at', 'last_updated', 'handled_by', 'days_old']

    def get_days_old(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.submitted_at
        return delta.days

    def validate(self, attrs):
        name = attrs.get('customer_name', '').strip()
        email = attrs.get('customer_email')
        title = attrs.get('issue_title', '').strip()
        desc = attrs.get('issue_description', '').strip()

        if not name:
            raise serializers.ValidationError("Customer name is required.")
        if len(name) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")

        if not email:
            raise serializers.ValidationError("Valid email address is required.")

        if not title:
            raise serializers.ValidationError("Issue title cannot be empty.")
        if len(title) > 300:
            raise serializers.ValidationError("Title too long (max 300 chars).")

        if not desc or len(desc) < 10:
            raise serializers.ValidationError("Please describe your issue in detail (min 10 chars).")

        phone = attrs.get('phone_number', '')
        if phone and (not phone.isdigit() or len(phone) not in [10, 11, 12]):
            raise serializers.ValidationError("Enter a valid phone number.")

        return attrs
    
    

class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = '__all__'
        read_only_fields = ('info_id', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def validate_support_phone(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError("Support phone must contain only digits.")
        if len(value) not in [10, 11, 12]:
            raise serializers.ValidationError("Support phone must be 10-12 digits.")
        return value

    def validate_pincode(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError("Pincode must contain only digits.")
        if len(value) != 6:
            raise serializers.ValidationError("Pincode must be exactly 6 digits.")
        return value

    def validate(self, data):
        if not self.instance:  # Create
            required = ['company_name', 'support_email', 'support_phone', 'address_line_1', 'city', 'state', 'pincode']
            for field in required:
                if not data.get(field) or not str(data[field]).strip():
                    raise serializers.ValidationError({field: f"{field.replace('_', ' ').title()} is required."})
        else:  # Update
            if 'support_phone' in data and data['support_phone'] and not str(data['support_phone']).strip():
                raise serializers.ValidationError({"support_phone": "Support phone cannot be empty."})
            if 'pincode' in data and data['pincode'] and len(str(data['pincode']).strip()) != 6:
                raise serializers.ValidationError({"pincode": "Pincode must be 6 digits."})

        return data
    
    


class NewsUpdateRecordSerializer(serializers.ModelSerializer):
    account_status = serializers.SerializerMethodField()

    class Meta:
        model = NewsUpdateRecord
        fields = [
            'record_id', 'full_name', 'subscriber_email', 'joined_on',
            'is_suspended', 'is_removed', 'account_status'
        ]
        read_only_fields = ['joined_on', 'record_id']

    def get_account_status(self, obj):
        return "Suspended" if obj.is_suspended else "Active"

    def validate_subscriber_email(self, value):
        if value:
            value = value.strip().lower()
            EmailValidator()(value)
        return value
    
    


class SponsorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        exclude = ['added_by', 'added_on', 'last_updated', 'is_archived']
        
        


class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at')

    def validate(self, data):
        if not self.instance and SiteConfig.objects.exists():
            raise serializers.ValidationError(
                "Site configuration already exists. Only one record is permitted."
            )

        content_fields = ['about_us_content', 'refund_policy_text', 'shipping_policy_text']
        filled_fields = [field for field in content_fields if data.get(field)]

        if not filled_fields:
            raise serializers.ValidationError(
                "At least one policy or content field must be provided."
            )

        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        for field in exclude:
            ret.pop(field, None)
        return ret


class ProductInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['product_id', 'name', 'thumbnail', 'details', 'is_hidden', 'added_on', 'last_updated', 'added_by', 'is_removed']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        for field in exclude:
            data.pop(field, None)
        if data.get('thumbnail'):
            request = self.context.get('request')
            if request:
                data['thumbnail'] = request.build_absolute_uri(data['thumbnail'])
        return data


class CategoryDetailSerializer(serializers.ModelSerializer):
    products = ProductInfoSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ['category_id', 'category_title', 'short_info', 'is_hidden', 'added_on',
                  'last_updated', 'added_by', 'is_removed', 'products']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        for field in exclude:
            data.pop(field, None)
        return data


class ServiceCategorySerializer(serializers.ModelSerializer):
    visibility = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = '__all__'
        read_only_fields = ('added_on', 'added_by', 'last_updated', 'is_removed')
        extra_kwargs = {
            'short_info': {'required': True},
        }

    def get_visibility(self, obj):
        return "Visible" if not obj.is_hidden else "Hidden"

    def validate_category_title(self, value):
        if value.lower().strip() == 'test':
            raise serializers.ValidationError("Category title cannot be 'test'.")
        return value.strip().title()

    def validate(self, data):
        title = data.get('category_title')
        info = data.get('short_info')
        if not title:
            raise serializers.ValidationError({"category_title": "This field is mandatory."})
        if not info:
            raise serializers.ValidationError({"short_info": "Category info is mandatory."})
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        for field in exclude:
            data.pop(field, None)
        return data