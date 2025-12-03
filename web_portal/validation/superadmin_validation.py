from ..views import*

def add_serial_numbers(queryset_or_list, page: int, page_size: int, ordering: str = "asc"):
    try:
        page = int(page)
        page_size = int(page_size)
    except (TypeError, ValueError):
        return False, JsonResponse({"error": "Invalid page or page_size"}, status=400)

    if page < 1 or page_size < 1:
        return False, JsonResponse({"error": "page and page_size must be positive integers"}, status=400)

    if not isinstance(queryset_or_list, (list, tuple)) or len(queryset_or_list) == 0:
        return False, JsonResponse({"error": "Invalid or empty data"}, status=400)

    ordering = str(ordering).lower().strip()
    if ordering not in ["asc", "desc"]:
        return False, JsonResponse({"error": "ordering must be 'asc' or 'desc'"}, status=400)

    page = max(page, 1)
    page_size = max(page_size, 1)
    base_index = (page - 1) * page_size + 1
    if ordering == "desc":
        for idx, item in enumerate(queryset_or_list):
            item["serial_no"] = base_index + (len(queryset_or_list) - 1 - idx)
    else:
        for idx, item in enumerate(queryset_or_list):
            item["serial_no"] = base_index + idx
    return True, queryset_or_list  