from ...views import*


class CredentialSettingsView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        raw_credentials = request.data.get('credentials_data')
        fee_type_input = request.data.get('plateform_fee_type')
        fee_value_input = request.data.get('plateform_fee')
        provider_code = request.data.get('sp_id')

        save_api_log(
            request=request,
            endpoint_source="OwnAPI",
            input_payload=request.data,
            output_response={"status": "processing"},
            service_provider_id=provider_code,
            service_type="Service Provider Update",
            client_override="fintech_backend_db"
        )

        try:
            if not provider_code:
                return Response(
                    {"status": "fail", "message": "sp_id is mandatory and cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            provider = ServiceProvider.objects.get(admin_code=provider_code)
            credentials_data = provider.api_credentials or {}
            params_data = provider.required_params or {}

            if raw_credentials is not None:
                if str(raw_credentials).strip() == "":
                    credentials_data['credentials_json'] = {}
                else:
                    try:
                        parsed_credentials = json.loads(raw_credentials)
                        if not isinstance(parsed_credentials, dict):
                            raise ValidationError("credentials_data must be a valid JSON object")
                        credentials_data['credentials_json'] = parsed_credentials
                    except json.JSONDecodeError:
                        return Response(
                            {"status": "fail", "message": "credentials_data contains invalid JSON format."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                        
            if fee_type_input is not None:
                params_data['plateform_fee_type'] = fee_type_input

            if fee_value_input is not None:
                try:
                    if isinstance(fee_value_input, str) and fee_value_input.strip():
                        float(fee_value_input)
                    params_data['plateform_fee'] = fee_value_input
                except ValueError:
                    return Response(
                        {"status": "fail", "message": "plateform_fee must be a valid number."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            provider.api_credentials = credentials_data
            provider.required_params = params_data
            provider.save(update_fields=['api_credentials', 'required_params'])

            try:
                load_dotenv()
                env_file_path = os.path.join(os.path.dirname(__file__), '../../.env')
                if os.path.exists(env_file_path):
                    env_key = provider.admin_code.upper()
                    full_config = {
                        'credentials': credentials_data,
                        'platform_settings': params_data
                    }
                    set_key(env_file_path, env_key, json.dumps(full_config))
            except Exception as e:

                save_api_log(
                    request=request,
                    endpoint_source="OwnAPI",
                    input_payload=request.data,
                    output_response={"status": "success"},
                    service_provider_id=provider_code,
                    service_type="Service Provider Update",
                    client_override="fintech_backend_db"
                )

            return Response({
                "status": "success",
                "message": "Provider settings updated successfully.",
                "data": {
                    "sp_id": provider.admin_code,
                    "provider_name": provider.display_label,
                    "credentials_preview": credentials_data.get('credentials_json', {}),
                    "fee_type": params_data.get('plateform_fee_type'),
                    "fee_value": params_data.get('plateform_fee')
                }
            }, status=status.HTTP_200_OK)

        except ServiceProvider.DoesNotExist:
            save_api_log(
                request=request,
                endpoint_source="OwnAPI",
                input_payload=request.data,
                output_response={"status": "fail", "message": "Provider not found"},
                service_provider_id=provider_code,
                service_type="Service Provider Update",
                client_override="fintech_backend_db"
            )
            return Response(
                {"status": "fail", "message": "No Service Provider found with the given sp_id."},
                status=status.HTTP_400_BAD_REQUEST
            )

        except ValidationError as ve:
            save_api_log(
                request=request,
                endpoint_source="OwnAPI",
                input_payload=request.data,
                output_response={"status": "fail", "message": str(ve)},
                service_provider_id=provider_code,
                service_type="Service Provider Update",
                client_override="fintech_backend_db"
            )
            return Response({"status": "fail", "message": str(ve)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            save_api_log(
                request=request,
                endpoint_source="OwnAPI",
                input_payload=request.data,
                output_response={"status": "error", "message": str(e)},
                service_provider_id=provider_code,
                service_type="Service Provider Update",
                client_override="fintech_backend_db"
            )
            return Response(
                {"status": "error", "message": "An internal server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )