from rest_framework import serializers
from .models import*

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
        if not self.instance:  # create
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
    
    
    


class CityLocationSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.district_name', read_only=True)

    class Meta:
        model = CityLocation
        fields = [
            'city_id',
            'city_name',
            'district',
            'district_name',
            'is_active',
            'pincode'
        ]
        read_only_fields = ('city_id',)

    def validate(self, data):
        city_name = data.get('city_name')
        district = data.get('district')

        if city_name and district:
            if CityLocation.objects.filter(
                city_name__iexact=city_name,
                district=district
            ).exists():
                raise serializers.ValidationError("City already exists in this district.")
        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        exclude = self.context.get('exclude_fields', [])
        for field in exclude:
            ret.pop(field, None)
        return ret
    
    
# serializers.py
from rest_framework import serializers

class FundRequestSerializer(serializers.ModelSerializer):
    bank_info = serializers.SerializerMethodField()
    proof_image_url = serializers.SerializerMethodField()

    class Meta:
        model = FundDepositRequest  # jo model humne banaya tha
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
    
    



class SaAdditionalFeeSerializer(serializers.ModelSerializer):
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
