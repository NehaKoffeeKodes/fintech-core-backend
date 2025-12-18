# # utils/database_router.py or wherever you keep this

import os
import json
from django.conf import settings
from django.db import connections
from admin_hub.models import Adcharges, AdServiceProvider
from admin_hub.thread_local import get_current_request  # adjust import if needed

# DATABASE_MAPPING = json.loads(os.getenv("ALLOWED_DOMAINS", "[]"))

# def get_database_from_domain():
#     request = get_current_request()
#     if not request:
#         return None  
    
#     coming_from = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_HOST') or ""
#     domain_only = coming_from.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0].strip()

#     for item in DATABASE_MAPPING:
#         db_name = list(item.keys())[0]
#         allowed_list = item[db_name]

#         if domain_only in allowed_list:
#             switch_to_database(db_name)
#             print(f"Connected to database: {db_name}")
#             return db_name

#     print("No database found for this domain:", domain_only)
#     return None


# def switch_to_database(db_name: str):
#     if db_name in connections.databases:
#         return db_name
    
#     new_db_config = settings.DATABASES['default'].copy()
#     new_db_config['NAME'] = db_name
#     settings.DATABASES[db_name] = new_db_config
#     connections.close_all()
#     return db_name


# utils/api_helpers.py

import os
import json
from dotenv import load_dotenv
from django.conf import settings
from django.db import connections, connection
from django.db.utils import ConnectionHandler
from user_agents import parse

from utils.log_file.log import save_api_log



load_dotenv()

# Load domain-to-database mapping from environment
DOMAIN_DB_MAPPING_JSON = os.getenv("DOMAIN_DB_MAPPING", "[]")

try:
    domain_database_map = json.loads(DOMAIN_DB_MAPPING_JSON)
except json.JSONDecodeError as err:
    print(f"Error parsing DOMAIN_DB_MAPPING JSON: {err}")
    domain_database_map = []


def get_database_from_domain():
    """
    Determines the correct tenant database based on request domain/origin.
    Connects to it dynamically if found.
    Returns database alias or None.
    """
    try:
        request = get_current_request()
        if not request:
            return None

        # Extract clean domain
        raw_domain = (
            request.META.get("HTTP_DOMAIN") or
            request.META.get("HTTP_ORIGIN") or
            request.META.get("HTTP_HOST") or
            ""
        )
        clean_domain = raw_domain.replace("https://", "").replace("http://", "").strip("/").lower()

        for entry in domain_database_map:
            for db_alias, allowed_domains in entry.items():
                if clean_domain in [d.lower() for d in allowed_domains]:
                    switch_to_database(db_alias)
                    return db_alias

        return None
    except Exception as exc:
        print(f"Failed to resolve database from domain: {exc}")
        return None


def validate_app_version(request):
    """
    Checks if the incoming request version matches the allowed version (for mobile apps).
    Returns True if version is acceptable or if not applicable (web).
    """
    try:
        allowed_version = os.getenv("APP_VERSION")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        if "Dart/" in user_agent:  # Mobile app request
            incoming_version = request.META.get("HTTP_VERSION")
            return incoming_version == allowed_version if allowed_version else False
        return True  # Web requests always pass
    except Exception:
        return False


def verify_service_provider_access(sp_id: int, provider_env_key: str) -> bool:
    """
    Validates if the given service provider ID is active and matches the expected one from env.
    """
    try:
        provider = AdServiceProvider.objects.get(sp_id=sp_id)
        if provider.is_deactive:
            return False

        expected_id = os.getenv(provider_env_key)
        return str(sp_id) == expected_id if expected_id else False
    except AdServiceProvider.DoesNotExist:
        return False
    except Exception as e:
        print(f"Error verifying service provider {sp_id}: {e}")
        return False


def is_service_assigned_to_user(request, service_provider_id: int) -> bool:
    """
    Checks if the logged-in portal user has the given service provider assigned.
    """
    try:
        current_user = request.user
        portal_user = current_user.portaluser  # Assuming related name or proper access
        assigned_services = portal_user.assign_service or []

        return int(service_provider_id) in assigned_services
    except Exception as e:
        print(f"Error checking assigned service {service_provider_id}: {e}")
        return False


def switch_to_database(db_alias: str) -> str:
    """
    Dynamically adds a new database connection to Django settings if not already present.
    Reuses default DB credentials.
    """
    if db_alias in settings.DATABASES:
        return db_alias

    settings.DATABASES[db_alias] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_alias,
        'USER': settings.DATABASES['default']['USER'],
        'PASSWORD': settings.DATABASES['default']['PASSWORD'],
        'HOST': settings.DATABASES['default']['HOST'],
        'PORT': settings.DATABASES['default']['PORT'],
        'ATOMIC_REQUESTS': True,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'OPTIONS': {},
        'TIME_ZONE': None,
    }

    # Refresh connection handler
    connections._connections = ConnectionHandler(settings.DATABASES)
    return db_alias


def calculate_and_apply_charges(
    request,
    provider_instance,
    provider_id: int,
    service_type_id,
    txn_amount: float,
    source_table: str,
    wallet_label: str,
    customer_contact: str,
    customer_name: str,
    api_response_payload,
    category_id,
    charge_tier: str,
    txn_reference_id,
    sub_service_id=None,
    portal_user_id=None
) -> bool:
    """
    Core function to calculate admin commission, GST, and trigger charge processing.
    Returns True on success, False on failure.
    """
    try:
        save_api_log(
            request, "InternalAPI", request.data,
            {"status": "processing", "step": "charge_calculation_start"},
            sp_id=provider_id, api_category="Charge Processing"
        )

        gst_percentage = float(provider_instance.hsn_sac.tax_rate or 0)

        # Find applicable admin charge slab
        charge_slabs = Adcharges.objects.filter(service_provider_id=provider_id)
        selected_charge = None

        if charge_slabs.exists():
            for slab in charge_slabs:
                if slab.minimum <= txn_amount <= slab.maximum:
                    selected_charge = slab
                    break
            if not selected_charge:
                selected_charge = charge_slabs.first()  # fallback to first

        # Default values if no charge found
        if selected_charge:
            charge_rate = selected_charge.rate
            rate_is_percent = selected_charge.rate_type == "is_percent"
            charge_nature = selected_charge.charges_type
        else:
            charge_rate = 0.0
            rate_is_percent = False
            charge_nature = None

        # Calculate commission
        base_commission = (txn_amount * charge_rate / 100) if rate_is_percent else charge_rate

        # Calculate GST amount on commission (inclusive GST logic)
        gst_amount_on_commission = base_commission - (base_commission / (1 + (gst_percentage / 100)))

        save_api_log(
            request, "InternalAPI", request.data,
            {
                "status": "processing",
                "charges": {
                    "base_commission": round(base_commission, 2),
                    "gst_on_commission": round(gst_amount_on_commission, 2),
                    "rate_type": "percent" if rate_is_percent else "flat"
                }
            },
            sp_id=provider_id, api_category="Charge Processing"
        )

        # Prepare payload for external charge calculation function
        charge_payload = {
            "service_id": service_type_id,
            "amount": float(txn_amount),
            "table_name": source_table,
            "wl_label": wallet_label,
            "gst_rate": float(gst_percentage),
            "admin_tax_amt": float(gst_amount_on_commission),
            "char_comm_amt": float(base_commission),
            "admin_charges_type": charge_nature,
            "sp_id": provider_id,
            "contact_number": customer_contact,
            "name": customer_name,
            "response_data": api_response_payload,
            "label": provider_instance.label,
            "category": category_id,
            "ss_id": sub_service_id,
            "is_self_config": provider_instance.is_self_config,
            "charge_level": charge_tier,
            "transaction_id": txn_reference_id,
            "user_id": portal_user_id
        }

        save_api_log(
            request, "ThirdParty", request.data,
            {"status": "success", "payload_sent": charge_payload},
            sp_id=provider_id, api_category="Charge Processing"
        )

        # Trigger actual charge deduction/credit logic
        # charges_calculation_function(request, charge_payload)

        return True

    except Exception as error:
        print(f"Charge calculation failed: {error}")
        save_api_log(
            request, "InternalAPI", request.data,
            {"status": "error", "message": str(error)},
            sp_id=provider_id, api_category="Charge Processing"
        )
        return False


def extract_device_information(request) -> dict:
    """
    Parses User-Agent string to extract device, OS, browser details.
    Returns structured dictionary.
    """
    user_agent_str = request.META.get("HTTP_USER_AGENT", "")
    parsed_ua = parse(user_agent_str)

    device_info = {
        "operating_system": parsed_ua.os.family,
        "os_version": parsed_ua.os.version_string,
        "device_model": parsed_ua.device.family,
        "browser_name": parsed_ua.browser.family,
        "is_mobile_device": parsed_ua.is_mobile,
        "is_tablet_device": parsed_ua.is_tablet,
        "is_desktop": parsed_ua.is_pc,
    }

    print(f"Device Info Extracted: {device_info}")
    return device_info