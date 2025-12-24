from django.http import HttpResponse
from django.shortcuts import render
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from control_panel.serializer import *
from control_panel.models import *
from validation.superadmin_validation import*
from datetime import timezone
from web_portal.models import *
from authentication.customjwt_auth import *
from authentication.permissions import *
from django.db import connection, connections
from django.core.exceptions import ObjectDoesNotExist
import logging
from datetime import time
import datetime
from datetime import datetime, timedelta
import random
import string
from django.db import IntegrityError
from io import TextIOWrapper
from utils.Api.core_utils import*
import json
from decimal import InvalidOperation
import traceback
from utils.excel_files.bank_excel import create_template_excel
from utils.excel_files.export_excel import export_institutions_to_excel
from utils.excel_files.import_excel import process_bank_import_from_excel
from utils.log_file.log import save_api_log
from utils.Api.user_activity_record import record_member_activity
from validation.db_helper_function import get_database_from_domain, switch_to_database
from utils.Api.core_utils import *
from rest_framework_simplejwt.tokens import AccessToken
import os,requests,uuid
from django.conf import settings
from django.contrib.auth.hashers import check_password
from web_portal.serializers import *
from admin_hub.models import *
import csv
from rest_framework_simplejwt.backends import TokenBackend
from io import StringIO
import ast
from dotenv import load_dotenv, set_key
import math,base64
from django.utils.html import strip_tags
from django.utils.crypto import get_random_string
from admin_hub.models import*
from control_panel import apps
from django.utils.timezone import now
import decimal
from utils.Api.dynamic_label import super_admin_action_label
from site import abs_paths
from admin_hub.models import PortalUserLog
from control_panel.master_data import master_data
from utils.database.admin_database_manage import run_migrations_for_admin, setup_admin_database




def store_uploaded_document(file_obj, sub_folder: str = "documents"):
    if not file_obj:
        return None
    
    target_dir = os.path.join(settings.MEDIA_ROOT, sub_folder)
    os.makedirs(target_dir, exist_ok=True)
    safe_filename = os.path.basename(file_obj.name)
    destination_path = os.path.join(target_dir, safe_filename)
    relative_path = os.path.join(sub_folder, safe_filename)

    try:
        with open(destination_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        return relative_path
    except Exception as e:
        return None
    
 



class CreateOrderManager(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return self.process_order(request, action='create')

    def get(self, request):
        return self.process_order(request, action='fetch')

    def process_order(self, request, action):
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'x-api-version': '2023-08-01',
            'x-client-id': os.getenv('CASHFREE_ORDER_CLIENT_ID'),
            'x-client-secret': os.getenv('CASHFREE_ORDER_CLIENT_SECRET'),
        }

        if action == 'create':
            customer_id = request.data.get('customer_id')
            customer_phone = request.data.get('customer_phone')
            amount = request.data.get('order_amount')

            if not all([customer_id, customer_phone, amount]):
                return Response({
                    'status': 'fail',
                    'message': 'customer_id, customer_phone, and order_amount are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            payload = {
                "customer_details": {
                    "customer_id": customer_id,
                    "customer_phone": customer_phone
                },
                "order_currency": request.data.get('order_currency', 'INR'),
                "order_amount": amount
            }

            url = 'https://sandbox.cashfree.com/pg/orders'

        elif action == 'fetch':
            order_id = request.query_params.get('order_id')
            if not order_id:
                return Response({
                    'status': 'fail',
                    'message': 'order_id is required in query params'
                }, status=status.HTTP_400_BAD_REQUEST)

            url = f'https://sandbox.cashfree.com/pg/orders/{order_id}'
            payload = None

        try:
            if action == 'create':
                response = requests.post(url, json=payload, headers=headers)
            else:
                response = requests.get(url, headers=headers)

            response_data = response.json()

            return Response(response_data, status=response.status_code)

        except requests.RequestException as e:
            return Response({
                'status': 'error',
                'message': f'Failed to connect to payment gateway: {str(e)}'
            }, status=status.HTTP_502_BAD_GATEWAY)


class AuthView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            url = "https://payout-gamma.cashfree.com/payout/v1/authorize"
            headers = {
                "accept": "application/json",
                "x-client-id": os.getenv('CASHFREE_PAYOUT_CLIENT_ID'),
                "x-client-secret": os.getenv('CASHFREE_PAYOUT_CLIENT_SECRET'),
            }

            response = requests.post(url, headers=headers)

            return Response(
                response.json(),
                status=response.status_code
            )

        except requests.RequestException as e:
            return Response({
                'status': 'error',
                'message': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BeneficiaryManager(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            unique_code = uuid.uuid4().hex[:8].upper()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            beneficiary_id = f"BEN{timestamp}{unique_code}"
            required_fields = [
                'beneficiary_name', 'bank_account_number', 'bank_ifsc',
                'beneficiary_email', 'beneficiary_phone', 'beneficiary_country_code',
                'beneficiary_address', 'beneficiary_city', 'beneficiary_state',
                'beneficiary_postal_code', 'beneficiary_purpose'
            ]

            missing = [field for field in required_fields if not request.data.get(field)]
            if missing:
                return Response({
                    'status': 'error',
                    'message': f"Missing fields: {', '.join(missing)}"
                }, status=status.HTTP_400_BAD_REQUEST)

            if len(request.data['bank_ifsc']) != 11:
                return Response({
                    'status': 'error',
                    'message': 'IFSC code must be 11 characters'
                }, status=status.HTTP_400_BAD_REQUEST)

            payload = {
                "beneficiary_id": beneficiary_id,
                "beneficiary_name": request.data['beneficiary_name'],
                "beneficiary_instrument_details": {
                    "bank_account_number": request.data['bank_account_number'],
                    "bank_ifsc": request.data['bank_ifsc'],
                    "vpa": request.data.get('vpa')
                },
                "beneficiary_contact_details": {
                    "beneficiary_email": request.data['beneficiary_email'],
                    "beneficiary_phone": request.data['beneficiary_phone'],
                    "beneficiary_country_code": request.data['beneficiary_country_code'],
                    "beneficiary_address": request.data['beneficiary_address'],
                    "beneficiary_city": request.data['beneficiary_city'],
                    "beneficiary_state": request.data['beneficiary_state'],
                    "beneficiary_postal_code": request.data['beneficiary_postal_code']
                },
                "beneficiary_purpose": request.data['beneficiary_purpose']
            }

            url = "https://sandbox.cashfree.com/payout/beneficiary"
            headers = {
                "accept": "application/json",
                "x-api-version": "2024-01-01",
                "content-type": "application/json",
                "x-client-id": os.getenv('CASHFREE_PAYOUT_CLIENT_ID'),
                "x-client-secret": os.getenv('CASHFREE_PAYOUT_CLIENT_SECRET'),
            }

            response = requests.post(url, json=payload, headers=headers)
            return Response(response.json(), status=response.status_code)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FundTransferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            unique_suffix = uuid.uuid4().hex[:6].upper()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            transfer_id = f"TRF{timestamp}{unique_suffix}"

            transfer_type = request.data.get('transfer_type')
            amount = request.data.get('transfer_amount')

            if not transfer_type:
                return Response({
                    'status': 'error',
                    'message': "transfer_type is required. Choose from: with_beneficiary_id, with_beneficiary_details, with_card, with_fundsource"
                }, status=status.HTTP_400_BAD_REQUEST)

            if not amount:
                return Response({
                    'status': 'error',
                    'message': 'transfer_amount is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            url = "https://sandbox.cashfree.com/payout/transfers"
            headers = {
                "accept": "application/json",
                "x-api-version": "2024-01-01",
                "content-type": "application/json",
                "x-client-id": os.getenv('CASHFREE_PAYOUT_CLIENT_ID'),
                "x-client-secret": os.getenv('CASHFREE_PAYOUT_CLIENT_SECRET'),
            }

            if transfer_type == "with_beneficiary_id":
                beneficiary_id = request.data.get('beneficiary_id')
                if not beneficiary_id:
                    return Response({'status': 'error', 'message': 'beneficiary_id required'}, status=status.HTTP_400_BAD_REQUEST)
                payload = {
                    "beneficiary_details": {"beneficiary_id": beneficiary_id},
                    "transfer_id": transfer_id,
                    "transfer_amount": amount
                }

            elif transfer_type == "with_beneficiary_details":
                mode = request.data.get('transfer_mode')
                ifsc = request.data.get('bank_ifsc')
                account = request.data.get('bank_account_number')
                if not all([mode, ifsc, account]):
                    return Response({'status': 'error', 'message': 'transfer_mode, bank_ifsc, bank_account_number required'}, status=status.HTTP_400_BAD_REQUEST)
                payload = {
                    "beneficiary_details": {
                        "beneficiary_instrument_details": {
                            "bank_account_number": account,
                            "bank_ifsc": ifsc
                        }
                    },
                    "transfer_id": transfer_id,
                    "transfer_amount": amount,
                    "transfer_mode": mode
                }

            elif transfer_type == "with_card":
                token = request.data.get('card_token')
                network = request.data.get('card_network_type')
                expiry = request.data.get('card_token_expiry')
                card_type = request.data.get('card_type')
                pan_seq = request.data.get('card_token_PAN_sequence_number')
                if not all([token, network, expiry, card_type, pan_seq]):
                    return Response({'status': 'error', 'message': 'All card details required'}, status=status.HTTP_400_BAD_REQUEST)
                payload = {
                    "beneficiary_details": {
                        "beneficiary_instrument_details": {
                            "card_details": {
                                "card_token": token,
                                "card_network_type": network,
                                "card_cryptogram": "dummy_cryptogram_123", 
                                "card_token_expiry": expiry,
                                "card_type": card_type,
                                "card_token_PAN_sequence_number": pan_seq
                            }
                        }
                    },
                    "transfer_id": transfer_id,
                    "transfer_amount": amount,
                    "transfer_mode": request.data.get('transfer_mode', 'imps')
                }

            elif transfer_type == "with_fundsource":
                beneficiary_id = request.data.get('beneficiary_id')
                fundsource = request.data.get('fundsource_id')
                if not all([beneficiary_id, fundsource]):
                    return Response({'status': 'error', 'message': 'beneficiary_id and fundsource_id required'}, status=status.HTTP_400_BAD_REQUEST)
                payload = {
                    "beneficiary_details": {"beneficiary_id": beneficiary_id},
                    "transfer_id": transfer_id,
                    "transfer_amount": amount,
                    "transfer_mode": request.data.get('transfer_mode', 'imps'),
                    "fundsource_id": fundsource
                }

            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid transfer_type'
                }, status=status.HTTP_400_BAD_REQUEST)

            response = requests.post(url, json=payload, headers=headers)
            return Response(response.json(), status=response.status_code)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            

class DMTPPIView(View):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            context = {
                'page_title': 'Proceed to Payment',
                'submit_button_text': 'Continue to Payment Gateway'
            }
            return render(request, 'payment_redirect_template.html', context, status=status.HTTP_200_OK)
        except Exception as e:
            error_html = f"""
            <html>
                <head><title>Error</title></head>
                <body>
                    <h1>Page Load Error</h1>
                    <p>Something went wrong: {str(e)}</p>
                    <p>Please try again later.</p>
                </body>
            </html>
            """
            return HttpResponse(error_html, content_type="text/html", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            context = {
                'page_title': 'Payment Initiated',
                'message': 'Your request has been sent to the payment gateway.',
                'info': 'You will be redirected shortly...'
            }
            return render(request, 'payment_redirect_template.html', context, status=status.HTTP_200_OK)
        except Exception as e:
            error_html = f"""
            <html>
                <head><title>Processing Error</title></head>
                <body>
                    <h1>Request Processing Failed</h1>
                    <p>Error details: {str(e)}</p>
                </body>
            </html>
            """
            return HttpResponse(error_html, content_type="text/html", status=status.HTTP_500_INTERNAL_SERVER_ERROR)