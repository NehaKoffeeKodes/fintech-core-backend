import openpyxl

from admin_hub.models import GlobalBankInstitution

def process_bank_import_from_excel(uploaded_file):
    column_mapping = {
        'Bank ID': 'institution_id',
        'Bank Name': 'full_name',
        'Bank Short Name': 'short_code',
        'Bank Global IFSC': 'universal_ifsc',
        'Fino ID': 'fino_mapping',
        'NSDL ID': 'nsdl_mapping',
        'Airtel ID': 'airtel_mapping',
        'Payout': 'supports_payout',
        'Fund Request': 'supports_funding',
        'Is Deactive': 'is_inactive',
    }

    workbook = openpyxl.load_workbook(uploaded_file)
    sheet = workbook.active

    headers_row = [cell.value.strip() if cell.value else '' for cell in sheet[1]]
    mapped_fields = [column_mapping.get(header) for header in headers_row]

    if None in mapped_fields:
        raise ValueError("Excel file has invalid or missing column headers.")

    imported_count = 0
    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_dict = dict(zip(mapped_fields, row))

        # Skip if updating existing (institution_id present)
        if row_dict.get('institution_id'):
            continue

        row_dict.pop('institution_id', None)

        # Convert TRUE/FALSE strings to boolean
        for bool_key in ['supports_payout', 'supports_funding', 'is_inactive']:
            value = row_dict.get(bool_key)
            if isinstance(value, str):
                cleaned = value.strip().upper()
                row_dict[bool_key] = (cleaned == "TRUE")
            elif value is None:
                row_dict[bool_key] = False

        # Save new institution
        GlobalBankInstitution.objects.create(**row_dict)
        imported_count += 1

    return imported_count