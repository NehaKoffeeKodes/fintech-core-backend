import json
from datetime import datetime
import os

LOG_FOLDER = "logs/api_logs"

def save_api_log(request, source, req_data, res_data, service=None):
    try:
        user_id = getattr(request.user, "id", "Guest")
        platform = "Mobile App" if "dart" in request.META.get("HTTP_USER_AGENT", "").lower() else "Website"

        domain = request.META.get("HTTP_HOST", "unknown.com").split(":")[0]

        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_id,
            "from": source,
            "domain": domain,
            "device": platform,
            "service": service,
            "request": req_data,
            "response": res_data
        }

        folder = os.path.join(LOG_FOLDER, domain)
        os.makedirs(folder, exist_ok=True)

        file_name = f"{folder}/log_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(file_name, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    except Exception as e:
        print("Logging failed:", e)