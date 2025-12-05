from requests import request
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.db import transaction
from datetime import timedelta
import jwt
from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
from django.conf import settings

from web_portal.models import *
from web_portal.APIs.authentication.customjwt_auth import *
from web_portal.APIs.utils.notify_service import *
from django.contrib.auth.hashers import check_password, make_password
from .serializers import*
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from uuid import uuid4
from io import BytesIO
import pyotp
import qrcode


import math
from django.db.models import Q
from web_portal.APIs.permissions.superadmin_permissions import IsSuperAdmin
from web_portal.APIs.validation.superadmin_validation import add_serial_numbers

import random
import string
import re

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import exceptions

import logging
from typing import Optional, Tuple

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.request import Request

from rest_framework_simplejwt.exceptions import InvalidToken



from rest_framework import status
from web_portal.models import AdminAccount
from web_portal.APIs.utils.helpers import *

import os
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated, AllowAny
from web_portal.models import Adminbanner
from web_portal.APIs.validation.superadmin_validation import *
from web_portal.models import AdminActivityLog
from django.core.paginator import Paginator
from django.core.paginator import EmptyPage
from django.utils.timezone import now
