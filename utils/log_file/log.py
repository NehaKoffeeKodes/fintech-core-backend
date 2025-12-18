import json
import os
from datetime import datetime
from pathlib import Path
from loguru import logger
from django.core.files.uploadedfile import UploadedFile
from dotenv import load_dotenv

load_dotenv()

DB_DOMAIN_MAPPING = os.getenv("DB_DOMAIN_MAPPING", "{}")

try:
    domain_to_client_map = json.loads(DB_DOMAIN_MAPPING)
except json.JSONDecodeError as exc:
    print(f"Failed to parse DB_DOMAIN_MAPPING JSON: {exc}")
    domain_to_client_map = {}


LOG_BASE_DIRECTORY = "application_logs"
logger.remove()


def extract_client_from_domain(host_domain: str):
    host_domain = host_domain.lower().replace("https://", "").replace("http://", "").strip("/")

    for client_key, domain_list in domain_to_client_map.items():
        if any(host_domain == d.lower() for d in domain_list):
            return client_key.split("_")[-1] 
    
    return "unknown_client"


def clean_old_logs(log_path: Path):
    if log_path.suffix == ".log":
        log_path.unlink(missing_ok=True)
    elif log_path.suffix == ".zip":
        try:
            file_age_days = (datetime.now() - datetime.fromtimestamp(log_path.stat().st_mtime)).days
            if file_age_days > 30:
                log_path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass


def make_serializable(data):
   
    if isinstance(data, dict):
        return {k: make_serializable(v) for k, v in data.items()}
    
    if isinstance(data, list):
        return [make_serializable(item) for item in data]
    
    if isinstance(data, UploadedFile):
        return {
            "file_name": data.name,
            "type_hint": "DjangoUploadedFile",
        }
    
    if hasattr(data, "__dict__"):
        return make_serializable(data.__dict__)
    try:
        json.dumps(data)
        return data
    except (TypeError, ValueError):
        return str(data)

active_loggers = {}


def get_or_create_logger(client_identifier: str):
    if client_identifier in active_loggers:
        return active_loggers[client_identifier]

    client_log_dir = Path(LOG_BASE_DIRECTORY) / client_identifier / "api_calls"
    client_log_dir.mkdir(parents=True, exist_ok=True)
    current_date = datetime.now().strftime("%Y_%m_%d")
    log_file_path = client_log_dir / f"api_log_{current_date}.log"

    client_logger = logger.bind(client_id=client_identifier)

    client_logger.add(sink=str(log_file_path),rotation="00:00",retention=clean_old_logs,compression="zip",level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        enqueue=True,                    
        filter=lambda record: record["extra"].get("client_id") == client_identifier
    )

    active_loggers[client_identifier] = client_logger
    return client_logger



def save_api_log(request,endpoint_source: str,input_payload,output_response,service_provider_id=None,service_type=None,client_override=None):
    try:
        current_user_id = getattr(request.user, "id", None) or "guest_user"
        user_agent_header = request.META.get("HTTP_USER_AGENT", "").lower()
        device_platform = "MobileApp" if "dart" in user_agent_header else "Browser"

        domain = (
            request.META.get("HTTP_DOMAIN") or
            request.META.get("HTTP_ORIGIN") or
            request.META.get("HTTP_HOST") or
            ""
        )
        domain = domain.replace("https://", "").replace("http://", "").strip("/")
        if client_override == "fintach_backend_db":
            client_name = "fintach_backend_db"
        else:
            client_name = extract_client_from_domain(domain)
            
        safe_input_data = make_serializable(input_payload)

        log_entry = {
            "event_time": datetime.now().isoformat(),
            "response_status": output_response.get("status", "unknown") if isinstance(output_response, dict) else "unknown",
            "source_endpoint": endpoint_source,
            "client": client_name,
            "request_domain": domain,
            "platform": device_platform,
            "user_id": current_user_id,
            "sp_id": service_provider_id,
            "category": service_type,
            "request_data": safe_input_data,
            "response_data": output_response
        }
        api_logger = get_or_create_logger(client_name)
        is_error = False

        if isinstance(output_response, str):
            error_keywords = ["exception", "traceback", "internal server", "error"]
            if any(keyword in output_response.lower() for keyword in error_keywords):
                is_error = True
        elif isinstance(output_response, dict):
            if str(output_response.get("status", "")).lower() in ["error", "failed"]:
                is_error = True

        serialized_log = json.dumps(log_entry, indent=2, ensure_ascii=False)

        if is_error:
            api_logger.error(serialized_log)
        else:
            api_logger.info(serialized_log)

    except Exception as unexpected_error:
        print(f"Critical failure in API logging system: {unexpected_error}")