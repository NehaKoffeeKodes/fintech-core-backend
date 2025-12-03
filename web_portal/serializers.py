from rest_framework import serializers


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