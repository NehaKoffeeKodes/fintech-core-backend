import psycopg2
from django.conf import settings
from django.db import connections
from django.core.management import call_command

def setup_admin_database(db_identifier):
    try:
        conn = psycopg2.connect(
            dbname='postgres',
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT']
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", [db_identifier])
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_identifier}"')
            cursor.execute(f'GRANT ALL ON DATABASE "{db_identifier}" TO {settings.DATABASES["default"]["USER"]};')

        cursor.close()
        conn.close()

        settings.DATABASES[db_identifier] = {
            **settings.DATABASES['default'],
            'NAME': db_identifier,
        }
        connections.databases = settings.DATABASES  

        if not hasattr(settings, 'TENANT_DATABASES'):
            settings.TENANT_DATABASES = []
        if db_identifier not in settings.TENANT_DATABASES:
            settings.TENANT_DATABASES.append(db_identifier)

        return True, "Database ready"
    except Exception as exc:
        return False, str(exc)


def run_migrations_for_admin(db_name):
    try:
        call_command('migrate', database=db_name, verbosity=0)
        return True
    except Exception as e:
        print(f"Migration error: {e}")
        return False