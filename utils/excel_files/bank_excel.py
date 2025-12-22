import os
from openpyxl import Workbook
from django.conf import settings
from datetime import datetime

def create_template_excel(column_titles):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Bank_Template"
    sheet.append(column_titles)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"bank_template_blank_{timestamp}.xlsx"
    export_dir = os.path.join(settings.MEDIA_ROOT, 'templates')
    os.makedirs(export_dir, exist_ok=True)

    full_path = os.path.join(export_dir, filename)
    workbook.save(full_path)

    return f"{settings.MEDIA_URL}templates/{filename}"