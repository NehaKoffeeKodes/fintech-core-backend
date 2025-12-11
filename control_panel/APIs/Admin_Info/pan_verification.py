from ...views import *
import os
from dotenv import load_dotenv
load_dotenv()

X_CLIENT_ID = os.getenv("X_CLIENT_ID")
X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
CASHFREE_BASE_URL = os.getenv("CASHFREE_BASE_URL")


class PanVerificationView(APIView):
    """
    Advanced PAN verification with name matching via Cashfree
    Generates unique verification_id like TCPL20250405123045A1B2C3
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pan_number = request.data.get('pan', '').strip().upper()
        full_name = request.data.get('name', '').strip()

        save_api_log(
            request, "ThirdParty", request.data,
            {"status": "started"}, None,
            service_type="PAN Verification", client_override="fintech_backend_db"
        )

        if not pan_number or not full_name:
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "validation_error", "error": "PAN and name are mandatory"},
                None, service_type="PAN Verification", client_override="fintech_backend_db"
            )
            return Response({
                'valid': False,
                'message': 'Both PAN number and full name are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            random_hex = uuid.uuid4().hex[:6].upper()
            timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
            verification_ref = f"TCPL{timestamp_str}{random_hex}"

        payload = {
            "pan": pan_number,
            "name": full_name,
            "verification_id": verification_ref
        }

        headers = {
            'x-client-id': X_CLIENT_ID,
            'x-client-secret': X_CLIENT_SECRET,
            'Content-Type': 'application/json'
        }

        api_url = f"{CASHFREE_BASE_URL}verification/pan/advance"

      
        save_api_log(
            request, "ThirdParty", payload,
            {"status": "request_sent", "url": api_url},
            None, service_type="PAN Verification", client_override="fintech_backend_db"
        )

        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=20)
            result = resp.json()

           
            if resp.status_code == 200 and result.get('status') == 'VALID':
                result['is_pan_verify'] = True
                result['verification_id'] = verification_ref
                result['verified_at'] = datetime.now().isoformat()

                save_api_log(
                    request, "ThirdParty", result,
                    {"status": "success", "message": "PAN verified & name matched"},
                    None, service_type="PAN Verification", client_override="fintech_backend_db"
                )
                return Response(result, status=status.HTTP_200_OK)

          
            else:
                result['is_pan_verify'] = False
                result['verification_id'] = verification_ref

                save_api_log(
                    request, "ThirdParty", result,
                    {"status": "failed", "reason": result.get('message', 'Unknown')},
                    None, service_type="PAN Verification", client_override="fintech_backend_db"
                )
                return Response(result, status=resp.status_code)

        except requests.Timeout:
            error_resp = {
                'valid': False,
                'message': 'PAN verification service timeout',
                'verification_id': verification_ref
            }
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "timeout"}, None,
                service_type="PAN Verification", client_override="fintech_backend_db"
            )
            return Response(error_resp, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except requests.ConnectionError:
            error_resp = {
                'valid': False,
                'message': 'Unable to reach verification server'
            }
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "connection_failed"}, None,
                service_type="PAN Verification", client_override="fintech_backend_db"
            )
            return Response(error_resp, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            error_resp = {
                'valid': False,
                'message': 'PAN verification failed due to server error'
            }
            save_api_log(
                request, "ThirdParty", request.data,
                {"status": "exception", "error": str(e)}, None,
                service_type="PAN Verification", client_override="fintech_backend_db"
            )
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)