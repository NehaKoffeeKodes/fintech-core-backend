from django.shortcuts import render
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage
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
import random
import string
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