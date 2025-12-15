# utils/database_router.py or wherever you keep this

import os
import json
from django.conf import settings
from django.db import connections
from admin_hub.thread_local import get_current_request  # adjust import if needed

DATABASE_MAPPING = json.loads(os.getenv("ALLOWED_DOMAINS", "[]"))

def get_database_from_domain():
    request = get_current_request()
    if not request:
        return None  
    
    coming_from = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_HOST') or ""
    domain_only = coming_from.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0].strip()

    for item in DATABASE_MAPPING:
        db_name = list(item.keys())[0]
        allowed_list = item[db_name]

        if domain_only in allowed_list:
            switch_to_database(db_name)
            print(f"Connected to database: {db_name}")
            return db_name

    print("No database found for this domain:", domain_only)
    return None


def switch_to_database(db_name: str):
    if db_name in connections.databases:
        return db_name
    
    new_db_config = settings.DATABASES['default'].copy()
    new_db_config['NAME'] = db_name
    settings.DATABASES[db_name] = new_db_config
    connections.close_all()
    return db_name