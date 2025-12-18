from ...views import*


class DmtFixChargeView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def _safe_parse_json_or_literal(self, raw_value):
        if not raw_value:
            return {}

        value = raw_value.strip()

        if len(value) >= 2 and value[0] in ['"', "'"] and value[-1] in ['"', "'"]:
            value = value[1:-1]

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
        
        value = re.sub(r"(\w+):\s*", r"'\1': ", value)

        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

        return {}

    def get(self, request):
        try:
            config_keys = [
                'pg_slab_one',
                'pg_slab_two',
                'pg_slab_three',
                'pg_slab_four'
            ]

            configurations = []

            for key in config_keys:
                raw_value = os.getenv(key)

                parsed_config = self._safe_parse_json_or_literal(raw_value)

                configurations.append(parsed_config)

            return Response({
                "success": True,
                "message": "Payment gateway configurations retrieved successfully",
                "data": configurations
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                "success": False,
                "message": "Failed to load configurations due to server error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
       
        try:
            env_file_path = '.env'
            valid_keys = {
                'pg_slab_one',
                'pg_slab_two',
                'pg_slab_three',
                'pg_slab_four'
            }

            current_env = load_dotenv(env_file_path)
            updated_count = 0

            for key in valid_keys:
                incoming_data = request.data.get(key)

                if incoming_data is None:
                    continue

                if isinstance(incoming_data, str):
                    try:
                        parsed = json.loads(incoming_data)
                    except json.JSONDecodeError:
                        continue  
                elif isinstance(incoming_data, list):
                    if incoming_data and isinstance(incoming_data[0], dict):
                        parsed = incoming_data[0]
                    else:
                        continue
                else:
                    parsed = incoming_data

                if not isinstance(parsed, dict):
                    continue
                json_string = json.dumps(parsed, separators=(',', ':'))
                set_key(env_file_path, key, json_string)
                os.environ[key] = json_string
                updated_count += 1

            if updated_count == 0:
                return Response({
                    "success": False,
                    "message": "No valid configuration data provided or all updates failed"
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "success": True,
                "message": f"Successfully updated {updated_count} configuration slab(s)"
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                "success": False,
                "message": "Update failed due to internal server error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)