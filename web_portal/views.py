from requests import request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.db import transaction
from datetime import timedelta
import jwt
from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
from django.conf import settings

from web_portal.models import *
from web_portal.authentication.customjwt_auth import generate_jwt_token, SecureJWTAuthentication, SuperAdminOnlyPermission
from web_portal.utils.notify_service import *
from django.contrib.auth.hashers import check_password, make_password
from .serializers import (EmailInputSerializer,OTPInputSerializer,PasswordChangeSerializer)
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from uuid import uuid4
from io import BytesIO
import pyotp
import qrcode


import math
from django.db.models import Q
from web_portal.authentication.customjwt_auth import SecureJWTAuthentication
from web_portal.permissions.superadmin_permissions import IsSuperAdmin
# from web_portal.utils.helpers import generate_secure_password, validate_email_format, validate_phone_format
from web_portal.validation.superadmin_validation import add_serial_numbers

from web_portal.models import Superadminlogindetails
import random
import string
import re

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import exceptions

import logging
from typing import Optional, Tuple

from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from rest_framework.request import Request

from .permissions.superadmin_permissions import IsSuperAdmin
from rest_framework_simplejwt.exceptions import InvalidToken
from django.http import JsonResponse
from .utils.notify_service import send_qr_code_via_smtp

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from web_portal.models import AdminAccount
from web_portal.authentication.customjwt_auth import SecureJWTAuthentication
from web_portal.permissions.superadmin_permissions import IsSuperAdmin
from web_portal.utils.helpers import (validate_email_format,validate_phone_format,generate_secure_password,add_serial_numbers)
from web_portal.utils.notify_service import send_welcome_email_direct_smtp
