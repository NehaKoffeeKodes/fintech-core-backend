from ...views import *

DIGITAP_CLIENT_ID = "76034597"
DIGITAP_CLIENT_SECRET = "jIzkvvBkEFvIYjde8O7lini65ghUk5Yo"
DIGITAP_BASE_URL = "https://api.digitap.ai/penny-drop/v2/"



class BankAccountVerificationView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsAdmin | IsSuperAdmin]

    def post(self, request):
        try:
            ifsc_code = request.data.get('ifsc_code')
            account_number = request.data.get('account_number')

            if not ifsc_code or not account_number:
                return Response({
                    "status": "error",
                    "message": "Both 'ifsc_code' and 'account_number' are required."
                }, status=status.HTTP_400_BAD_REQUEST)

            validation_error = self._validate_inputs(ifsc_code, account_number)
            if validation_error:
                return validation_error

            auth_string = f"{DIGITAP_CLIENT_ID}:{DIGITAP_CLIENT_SECRET}"
            auth_token = base64.b64encode(auth_string.encode()).decode('utf-8')

            url = f"{DIGITAP_BASE_URL}check-valid"
            payload = {
                "ifsc": ifsc_code.upper().strip(),
                "accNo": str(account_number).strip()
            }
            headers = {
                "ent_authorization": auth_token,
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers, timeout=20)

            if response.status_code == 200:
                data = response.json()
                verification_status = data.get("model", {}).get("status", "").upper()

                if verification_status == "SUCCESS":
                    return Response({
                        "status": "success",
                        "message": "Account verified successfully.",
                        "data": data
                    }, status=status.HTTP_200_OK)

                elif verification_status == "PENDING":
                    return Response({
                        "status": "pending",
                        "message": "Verification is in progress. Please try again after some time.",
                        "data": data
                    }, status=status.HTTP_202_ACCEPTED)

                else:
                    return Response({
                        "status": "failed",
                        "message": "Account verification failed. Please check the details and try again.",
                        "data": data
                    }, status=status.HTTP_400_BAD_REQUEST)

            else:
                try:
                    error_detail = response.json()
                except:
                    error_detail = response.text

                return Response({
                    "status": "error",
                    "message": "Third-party verification service error.",
                    "details": error_detail
                }, status=response.status_code)

        except requests.Timeout:
            return Response({
                "status": "error",
                "message": "Request timed out. The bank verification service is slow. Please try again later."
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "An internal server error occurred. Please try again later."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def _validate_inputs(self, ifsc: str, acc_no):
        if not is_valid_ifsc(ifsc):
            return Response({
                "status": "error",
                "message": "Invalid IFSC code format. Expected format: ABCD0123456 (11 characters)"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not is_positive_integer(acc_no):
            return Response({
                "status": "error",
                "message": "Account number must contain only digits."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not is_valid_account_no(acc_no):
            return Response({
                "status": "error",
                "message": "Account number must be between 6 and 20 digits long."
            }, status=status.HTTP_400_BAD_REQUEST)

        return None  