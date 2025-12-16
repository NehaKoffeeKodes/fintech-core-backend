from ...views import *

X_CLIENT_ID = os.getenv("X_CLIENT_ID")
X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
CASHFREE_BASE_URL = os.getenv("CASHFREE_BASE_URL")


class VerifyGSTApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        gstin = request.data.get('GSTIN', '').strip()

        save_api_log(
            request, "ThirdParty", request.data,
            {"status": "initiated"}, None,
            service_type="GST Verification",
            client_override="fintech_backend_db"
        )

        required = ['GSTIN']
        validation_error = enforce_required_fields(request.data, required)
        if validation_error:
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "validation_failed", "missing": required},
                None, service_type="GST Verification", client_override="fintech_backend_db"
            )
            return validation_error

        if len(gstin) != 15:
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "invalid_format", "gstin_length": len(gstin)},
                None, service_type="GST Verification", client_override="fintech_backend_db"
            )
            return Response({
                'valid': False,
                'message': 'GSTIN must be exactly 15 characters'
            }, status=status.HTTP_400_BAD_REQUEST)

        endpoint = f"{CASHFREE_BASE_URL}verification/gstin"
        payload = {"GSTIN": gstin}
        headers = {
            'x-client-id': X_CLIENT_ID,
            'x-client-secret': X_CLIENT_SECRET,
            'Content-Type': 'application/json'
        }

        save_api_log(
            request, "ThirdParty", payload,
            {"status": "calling_cashfree", "url": endpoint},
            None, service_type="GST Verification", client_override="fintech_backend_db"
        )

        try:
            api_response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=15
            )
            result = api_response.json()

            if api_response.status_code == 200 and result.get("message") == "GSTIN Exists":
                result['is_gst_verify'] = True
                result['verified_at'] = __import__('datetime').datetime.now().isoformat()

                save_api_log(
                    request, "ThirdParty", result,
                    {"status": "verified_success"}, None,
                    service_type="GST Verification", client_override="fintech_backend_db"
                )
                return Response(result, status=status.HTTP_200_OK)

            else:
                result['is_gst_verify'] = False
                save_api_log(
                    request, "ThirdParty", result,
                    {"status": "not_verified"}, None,
                    service_type="GST Verification", client_override="fintech_backend_db"
                )
                return Response(result, status=api_response.status_code)

        except requests.Timeout:
            error_msg = "GSTIN verification timed out"
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "timeout", "error": error_msg}, None,
                service_type="GST Verification", client_override="fintech_backend_db"
            )
            return Response({
                'valid': False,
                'message': error_msg
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except requests.ConnectionError:
            error_msg = "Unable to connect to verification service"
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "connection_error"}, None,
                service_type="GST Verification", client_override="fintech_backend_db"
            )
            return Response({
                'valid': False,
                'message': error_msg
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "exception", "error": str(e)}, None,
                service_type="GST Verification", client_override="fintech_backend_db"
            )
            return Response({
                'valid': False,
                'message': 'Verification service temporarily unavailable'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)