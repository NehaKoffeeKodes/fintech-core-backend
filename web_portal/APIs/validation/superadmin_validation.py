from ...views import*

# def add_serial_numbers(queryset_or_list, page: int, page_size: int, ordering: str = "asc"):
#     try:
#         page = int(page)
#         page_size = int(page_size)
#     except (TypeError, ValueError):
#         return False, JsonResponse({"error": "Invalid page or page_size"}, status=400)

#     if page < 1 or page_size < 1:
#         return False, JsonResponse({"error": "page and page_size must be positive integers"}, status=400)

#     if not isinstance(queryset_or_list, (list, tuple)) or len(queryset_or_list) == 0:
#         return False, JsonResponse({"error": "Invalid or empty data"}, status=400)

#     ordering = str(ordering).lower().strip()
#     if ordering not in ["asc", "desc"]:
#         return False, JsonResponse({"error": "ordering must be 'asc' or 'desc'"}, status=400)

#     page = max(page, 1)
#     page_size = max(page_size, 1)
#     base_index = (page - 1) * page_size + 1
#     if ordering == "desc":
#         for idx, item in enumerate(queryset_or_list):
#             item["serial_no"] = base_index + (len(queryset_or_list) - 1 - idx)
#     else:
#         for idx, item in enumerate(queryset_or_list):
#             item["serial_no"] = base_index + idx
#     return True, queryset_or_list 


import re
from typing import List, Dict, Any


def is_positive_integer(value: Any) -> bool:
    """
    Safely validate if value is a positive integer (as string or int).
    Used for page_number, page_size, IDs etc.
    """
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        return bool(re.fullmatch(r"[1-9]\d*", value.strip()))
    return False


def add_serial_number(
    data: List[Dict[str, Any]],
    page_number: int,
    page_size: int,
    field_name: str = "sr_no",
    order: str = "desc"
) -> None:
    """
    Adds a serial number (1, 2, 3...) to paginated results.
    Works perfectly with latest-first (descending) ordering.

    Example:
        Page 2, size 10 → items will get sr_no: 20, 19, 18...11 (if desc)
                                    or 11, 12, 13...20 (if asc)

    Args:
        data: List of dicts (serializer.data)
        page_number: Current page (1-based)
        page_size: Items per page
        field_name: Key name for serial number (default: "sr_no")
        order: "asc" or "desc" (default desc - matches your admin panel style)
    """
    if not data or page_size <= 0 or page_number < 1:
        return

    start_index = (page_number - 1) * page_size + 1
    total_items_in_page = len(data)

    if order.lower() == "desc":
        current = start_index + total_items_in_page - 1
        step = -1
    else:
        current = start_index
        step = 1

    for item in data:
        item[field_name] = current
        current += step 