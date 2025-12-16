import csv
import json
import os
from openpyxl import Workbook
from datetime import datetime
from django.conf import settings
from django.utils.timezone import localtime

def export_institutions_to_excel(data_qs, column_mapping, file_prefix):
    """
    Exports queryset to Excel with proper formatting.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Institutions"

    headers = list(column_mapping.values())
    fields = list(column_mapping.keys())
    ws.append(headers)

    for record in data_qs:
        row_data = []
        for field in fields:
            val = getattr(record, field, '')

            # Boolean to TRUE/FALSE
            if field in ['supports_payout', 'supports_funding', 'is_inactive']:
                val = 'TRUE' if val else 'FALSE'

            # JSON fields to string
            if isinstance(val, (dict, list)):
                val = json.dumps(val)

            row_data.append(str(val) if val is not None else '')
        ws.append(row_data)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{file_prefix}_{timestamp}.xlsx"
    export_folder = os.path.join(settings.MEDIA_ROOT, 'downloads')
    os.makedirs(export_folder, exist_ok=True)

    save_path = os.path.join(export_folder, filename)
    wb.save(save_path)

    return f"{settings.MEDIA_URL}downloads/{filename}"


def flatten_json_data(nested_dict, prefix="", delimiter="_"):
    flat = {}
    for key, value in nested_dict.items():
        new_key = f"{prefix}{delimiter}{key}" if prefix else key
        if isinstance(value, dict) and len(value) == 1:
            inner_k, inner_v = next(iter(value.items()))
            flat[new_key] = inner_v
        elif isinstance(value, dict):
            flat.update(flatten_json_data(value, new_key, delimiter))
        else:
            flat[new_key] = value
    return flat


def generate_csv_export(request, records_list, prefix_name):
    if not records_list:
        return None

    flat_records = [flatten_json_data(r) for r in records_list]
    column_names = list(flat_records[0].keys())

    timestamp = localtime().strftime("%Y%m%d%H%M%S")
    csv_filename = f"{prefix_name}_{timestamp}.csv"
    file_location = os.path.join(settings.MEDIA_ROOT, csv_filename)

    with open(file_location, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=column_names, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for entry in flat_records:
            safe_entry = {k: str(entry.get(k, "")) for k in column_names}
            writer.writerow(safe_entry)

    return f"http://{request.get_host()}{settings.MEDIA_URL}{csv_filename}"