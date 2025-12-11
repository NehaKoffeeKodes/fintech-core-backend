import os
import json
from django.conf import settings
from django.db import connections
from django.conf import settings
from django.db import connections

def switch_to_database(db_name):
    if db_name in connections.databases:
        return db_name  
    
    settings.DATABASES[db_name] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_name,
        'USER': settings.DATABASES['default']['USER'],
        'PASSWORD': settings.DATABASES['default']['PASSWORD'],
        'HOST': settings.DATABASES['default']['HOST'],
        'PORT': settings.DATABASES['default']['PORT'],
    }

    connections.close_all()
    connections.databases = settings.DATABASES
    return db_name

ALLOWED_DOMAINS = json.loads(os.getenv("ALLOWED_DOMAINS", "[]"))

def get_database_from_domain():
    request = get_current_request()

    if not request:
        return None
    
    full_url = (
        request.META.get("HTTP_ORIGIN") or
        request.META.get("HTTP_HOST") or
        ""
    )

    clean_domain = (
        full_url.replace("http://", "")
                .replace("https://", "")
                .split("/")[0]
                .strip()
    )

    for entry in ALLOWED_DOMAINS:
        db_name = list(entry.keys())[0]
        domain_list = entry[db_name]

        if clean_domain in domain_list:
            switch_to_database(db_name)
            return db_name

    return None