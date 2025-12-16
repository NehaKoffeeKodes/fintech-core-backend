from ...views import*

load_dotenv()

def generate_random_string(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_current_timestamp_ms():
    return str(int(time.time() * 1000))


def generate_paysprint_jwt():
    secret = os.getenv("PAYSPRINT_JWT_SECRET")
    partner_id = os.getenv("PAYSPRINT_PARTNER_ID")

    if not secret or not partner_id:
        raise ValueError("PAYSPRINT_JWT_SECRET or PAYSPRINT_PARTNER_ID missing in environment")

    request_id = generate_random_string()
    timestamp = get_current_timestamp_ms()

    payload = {
        "timestamp": timestamp,
        "partnerId": partner_id,
        "reqid": request_id
    }

    token = jwt.encode(payload, secret.encode(), algorithm="HS256")
    return token


def get_instantpay_headers():
    return {
        "X-Ipay-Auth-Code": os.getenv("INSTANTPAY_AUTH_CODE"),
        "X-Ipay-Client-Id": os.getenv("INSTANTPAY_CLIENT_ID"),
        "X-Ipay-Client-Secret": os.getenv("INSTANTPAY_CLIENT_SECRET"),
        "X-Ipay-Endpoint-Ip": os.getenv("INSTANTPAY_ENDPOINT_IP"),
        "X-Ipay-Outlet-Id": os.getenv("INSTANTPAY_OUTLET_ID"),
    }


class GatewayBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    PROVIDER_HANDLERS = {
        "cashfree": "fetch_cashfree_balance",
        "paysprint": "fetch_paysprint_balance",
        "nobal": "fetch_nobal_balance",
        "instantpay": "fetch_instantpay_balance",
        "utilityxchange": "fetch_utilityxchange_balance",
        "sankalppe": "fetch_sankalppe_balance",
    }

    def get(self, request):
        try:
            gateways = ServiceProvider.objects.filter(is_deleted=False)

            gateway_data = gateways.values(
                'gateway_id',
                'gateway_name',
                'provider_name',
                'current_balance',
                'supports_balance_check'
            ).order_by('provider_name')

            response = {
                "results": list(gateway_data)
            }

            return Response({
                'status': 'success',
                'message': 'Gateway balances retrieved successfully',
                'data': response
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        provider_key = request.data.get("provider_name", "").strip().lower()

        if not provider_key:
            return Response({
                "status": "error",
                "message": "provider_name is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        handler_name = self.PROVIDER_HANDLERS.get(provider_key)
        if not handler_name:
            return Response({
                "status": "error",
                "message": f"Provider '{provider_key}' is not supported"
            }, status=status.HTTP_400_BAD_REQUEST)

        handler_method = getattr(self, handler_name)
        return handler_method(request)



    def fetch_cashfree_balance(self, request):
        try:
            client_id = os.getenv("CASHFREE_CLIENT_ID")
            client_secret = os.getenv("CASHFREE_CLIENT_SECRET")

            if not client_id or not client_secret:
                return Response({
                    "status": "error",
                    "message": "Cashfree credentials not configured"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            auth_url = "https://api.cashfree.com/payout/v1/authorize"
            auth_headers = {
                'X-Client-Id': client_id,
                'X-Client-Secret': client_secret
            }
            auth_resp = requests.post(auth_url, headers=auth_headers)
            auth_data = auth_resp.json()

            token = auth_data.get('data', {}).get('token')
            if not token:
                return Response({
                    "status": "error",
                    "message": "Failed to authenticate with Cashfree",
                    "details": auth_data
                }, status=status.HTTP_400_BAD_REQUEST)

            balance_url = "https://api.cashfree.com/payout/v1/getBalance"
            balance_resp = requests.get(balance_url, headers={'Authorization': f'Bearer {token}'})
            balance_data = balance_resp.json()

            if balance_data.get("subCode") == "200":
                balance = balance_data.get("data", {}).get("availableBalance", 0)

                ServiceProvider.objects.filter(provider_name__iexact="CashFree").update(current_balance=balance)

                return Response({
                    'status': 'success',
                    'message': 'Cashfree balance updated successfully',
                    'data': {
                        'provider_name': 'CashFree',
                        'current_balance': balance
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "error",
                "message": "Failed to fetch Cashfree balance",
                "details": balance_data
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_paysprint_balance(self, request):
        try:
            url = "https://api.paysprint.in/api/v1/service/balance/balance/cashbalance"
            headers = {
                "accept": "application/json",
                "Token": generate_paysprint_jwt(),
                "AuthorisedKey": os.getenv("PAYSPRINT_AUTHORISED_KEY"),
                "Content-Type": "application/json"
            }

            response = requests.post(url, headers=headers)
            data = response.json()

            if data.get("status") is True and data.get("response_code") == 1:
                balance = data.get("cdwallet", 0)

                ServiceProvider.objects.filter(provider_name__iexact="paysprint").update(current_balance=balance)

                return Response({
                    'status': 'success',
                    'message': 'Paysprint balance updated',
                    'data': {
                        'provider_name': 'Paysprint',
                        'current_balance': balance
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "error",
                "message": "Failed to fetch Paysprint balance",
                "details": data
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_nobal_balance(self, request):
        try:
            token = request.data.get('token')
            if not token:
                return Response({
                    "status": "error",
                    "message": "Authentication token is required for Nobal"
                }, status=status.HTTP_400_BAD_REQUEST)

            url = "https://service.noblewebstudio.in/api/v1.0/airtel_dmt/partner_balance"
            headers = {
                'Authorization': f'Bearer {token}',
                'X-Timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers)
            data = response.json()

            if data.get("status") is True and data.get("response_code") == 1:
                balance = data.get("data", {}).get("balance", 0)  

                ServiceProvider.objects.filter(provider_name__iexact="Nobal").update(current_balance=balance)

                return Response({
                    'status': 'success',
                    'message': 'Nobal balance updated',
                    'data': {
                        'provider_name': 'Nobal',
                        'current_balance': balance
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "error",
                "message": "Failed to fetch Nobal balance",
                "details": data
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_instantpay_balance(self, request):
        try:
            headers = get_instantpay_headers()
            if not all(headers.values()):
                return Response({
                    "status": "error",
                    "message": "InstantPay credentials not configured"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            url = "https://api.instantpay.in/accounts/balance"
            payload = {
                "bankProfileId": 0,
                "accountNumber": "9377858000",
                "externalRef": "TRANSACTION12334",
                "latitude": "21.143929",
                "longitude": "72.750800"
            }

            response = requests.post(url, json=payload, headers=headers)
            data = response.json()

            if data.get("status") is True and data.get("response_code") == 1:
                balance = data.get("data", {}).get("balance", 0)  

                ServiceProvider.objects.filter(provider_name__iexact="InstantPay").update(current_balance=balance)

                return Response({
                    'status': 'success',
                    'message': 'InstantPay balance updated',
                    'data': {
                        'provider_name': 'InstantPay',
                        'current_balance': balance
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "error",
                "message": "Failed to fetch InstantPay balance",
                "details": data
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_utilityxchange_balance(self, request):
        try:
            user_id = os.getenv("UTILITYXCHANGE_USER_ID")
            token = os.getenv("UTILITYXCHANGE_TOKEN")

            if not user_id or not token:
                return Response({
                    "status": "error",
                    "message": "UtilityXchange credentials missing"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            url = f"https://utilityxchange.com/API/Balance?UserID={user_id}&Token={token}&Format=1"
            response = requests.get(url)
            data = response.json()

            if data.get("data", {}).get("status") == 2 and data.get("data", {}).get("errorcode") == "200":
                balance = data["data"].get("bal", 0)

                ServiceProvider.objects.filter(provider_name__iexact="utilityxchange").update(current_balance=balance)

                return Response({
                    'status': 'success',
                    'message': 'UtilityXchange balance updated',
                    'data': {
                        'provider_name': 'UtilityXchange',
                        'current_balance': balance
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "error",
                "message": "Failed to fetch UtilityXchange balance",
                "details": data
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_sankalppe_balance(self, request):
        try:
            access_token = os.getenv("SANKALPPE_ACCESS_TOKEN")
            if not access_token:
                return Response({
                    "status": "error",
                    "message": "SankalpPE access token missing"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            url = f"https://sankalppe.com/Api/Service/Balance?at={access_token}"
            response = requests.get(url)
            data = response.json()

            if data.get("STATUS") == 1 and data.get("ERRORCODE") == "0":
                balance = data.get("BALANCE", "0")

                ServiceProvider.objects.filter(provider_name__iexact="sankalppe").update(current_balance=balance)

                return Response({
                    'status': 'success',
                    'message': 'SankalpPE balance updated',
                    'data': {
                        'provider_name': 'SankalpPE',
                        'current_balance': balance
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "error",
                "message": "Failed to fetch SankalpPE balance",
                "details": data
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)