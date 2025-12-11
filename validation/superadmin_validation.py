import re
from typing import Any


def add_serial_numbers(data_list, page=1, page_size=10, order="desc"):
    total = len(data_list)
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 10)))
    
    start = (page - 1) * page_size
    end = start + page_size
    page_data = data_list[start:end]

    if page_data:
        start_sr = (page - 1) * page_size + 1
        if order.lower() == "desc":
            sr = start_sr + len(page_data) - 1
            step = -1
        else:
            sr = start_sr
            step = 1
        
        for item in page_data:
            item["sr_no"] = sr
            sr += step

    return {
        "total_items": total,
        "current_page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 1,
        "results": page_data
    }


def is_positive_integer(value: Any) -> bool:
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        return bool(re.fullmatch(r"[1-9]\d*", value.strip()))
    return False


def is_float(value):
    try:
        float(value)
        return True
    except:
        return False
    
    

#string validation

def contains_only_letters_spaces_underscore(text: str) -> bool:
    """Allow only A-Z, a-z, space and underscore"""
    return bool(re.fullmatch(r'[A-Za-z\s_]+', text or ''))


def is_valid_account_no(acc_no: str) -> bool:
    """Check if account number has 8 to 16 digits only"""
    return bool(re.match(r'^\d{8,16}$', str(acc_no).strip()))


def is_legitimate_ifsc(code: str) -> bool:
    """Validate Indian IFSC format: ABCD0123456"""
    if not code:
        return False
    pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
    return bool(re.match(pattern, code.strip().upper()))