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
from fintech_backend.customjwt_auth import*
import logging
from utils.core_utils import*
import json
from utils.log_file.log import save_api_log
from utils.user_activity_record import record_member_activity
from validation.db_helper_function import get_database_from_domain, switch_to_database
from utils.core_utils import *
from rest_framework_simplejwt.tokens import AccessToken
import os,requests,uuid
from django.conf import settings
from django.contrib.auth.hashers import check_password
from web_portal.serializers import *

logger = logging.getLogger(__name__)

def store_uploaded_document(file_obj, sub_folder: str = "documents"):
    """
    Securely save uploaded file and return relative URL path
    Same logic as handle_uploaded_file but completely different style
    """
    if not file_obj:
        return None

    # Ensure upload directory exists
    target_dir = os.path.join(settings.MEDIA_ROOT, sub_folder)
    os.makedirs(target_dir, exist_ok=True)

    # Secure filename (prevent directory traversal)
    safe_filename = os.path.basename(file_obj.name)
    destination_path = os.path.join(target_dir, safe_filename)
    relative_path = os.path.join(sub_folder, safe_filename)

    try:
        with open(destination_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        logger.info(f"File saved successfully: {relative_path}")
        return relative_path
    except Exception as e:
        logger.error(f"Failed to save uploaded file {safe_filename}: {e}")
        return None