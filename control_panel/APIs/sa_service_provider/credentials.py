from ...views import*


class UpdateProviderSettingsView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        raw_credentials = request.data.get('credentials_data')
        fee_type_input = request.data.get('plateform_fee_type')
        fee_value_input = request.data.get('plateform_fee')
        provider_id = request.data.get('sp_id')
        
        save_api_log(
            request, "OwnAPI", request.data,
            {"status": "processing"}, None,
            service_type="Service Provider Update",
            client_override="tcpl_db"
        )

        try:
            if not provider_id:
                return Response(
                    {"status": "fail", "message": "sp_id is mandatory and cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                provider = ServiceProvider.objects.get(sp_id=provider_id)
            except ServiceProvider.DoesNotExist:
                return Response(
                    {"status": "fail", "message": "No Service Provider found with the given sp_id."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            current_settings = provider.service_json or {}
            if raw_credentials is not None:
                if raw_credentials.strip() == "":
                    current_settings['credentials_json'] = {}
                else:
                    try:
                        parsed_credentials = json.loads(raw_credentials)
                        if not isinstance(parsed_credentials, dict):
                            raise ValidationError("credentials_data must be a valid JSON object")
                        current_settings['credentials_json'] = parsed_credentials
                    except json.JSONDecodeError:
                        return Response(
                            {"status": "fail", "message": "credentials_data contains invalid JSON format."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            if fee_type_input is not None:
                current_settings['plateform_fee_type'] = fee_type_input

            if fee_value_input is not None:
                try:
                    if isinstance(fee_value_input, str) and fee_value_input.strip():
                        float(fee_value_input)  
                    current_settings['plateform_fee'] = fee_value_input
                except ValueError:
                    return Response(
                        {"status": "fail", "message": "plateform_fee must be a valid number."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            provider.service_json = current_settings
            provider.save(update_fields=['service_json'])

            try:
                load_dotenv()
                env_file_path = os.path.join(os.path.dirname(__file__), '../.env')
                set_key(env_file_path, provider.sp_name.upper(), json.dumps(current_settings))
            except Exception as env_error:
               print(f"Warning: Failed to update .env file: {str(env_error)}")

            
            save_api_log(
                request, "OwnAPI", request.data,
                {"status": "success"}, None,
                service_type="Service Provider Update",
                client_override="tcpl_db"
            )

            return Response(
                {
                    "status": "success",
                    "message": "Provider settings updated successfully.",
                    "data": {
                        "sp_id": provider.sp_id,
                        "provider_name": provider.sp_name
                    }
                },
                status=status.HTTP_200_OK
            )

        except ValidationError as ve:
            save_api_log(
                request, "OwnAPI", request.data,
                {"status": "error", "message": str(ve)}, None,
                service_type="Service Provider Update",
                client_override="tcpl_db"
            )
            return Response(
                {"status": "fail", "message": str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as unexpected_error:
            error_message = str(unexpected_error)
            save_api_log(
                request, "OwnAPI", request.data,
                {"status": "error", "message": f"Server error: {error_message}"}, None,
                service_type="Service Provider Update",
                client_override="tcpl_db"
            )
            return Response(
                {"status": "error", "message": "An internal server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )