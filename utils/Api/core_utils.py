from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import localtime
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

def enforce_required_fields(payload: dict, mandatory: list):
    absent = [key for key in mandatory if not payload.get(key)]
    if absent:
        return Response(
            {
                "status": "error",
                "message": "Required fields missing",
                "missing": absent
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    return None




def validate_paging_inputs(page: str, size: str):
    """Validate and sanitize pagination parameters"""
    errors = []

    if not page:
        errors.append("page parameter is mandatory")
    elif not page.isdigit() or int(page) < 1:
        errors.append("page must be a positive integer")

    if not size:
        errors.append("size parameter is mandatory")
    elif not size.isdigit() or int(size) < 1:
        errors.append("size must be a positive integer")

    if errors:
        return Response(
            {
                "status": "fail",
                "message": "Invalid pagination parameters",
                "details": errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    return None




def apply_date_range_filter(request_data, queryset, date_field='created_at'):
    """
    Apply today/weekly/monthly/yearly/custom date filter
    Same logic, totally different implementation
    """
    filter_type = request_data.get('filter_type')
    start = request_data.get('start_date')
    end = request_data.get('end_date')

    if not filter_type and not (start and end):
        return queryset

    today = localtime().date()

    try:
        if filter_type == 'today':
            start_dt = localtime().replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1)
            return queryset.filter(**{f"{date_field}__gte": start_dt, f"{date_field}__lt": end_dt})

        elif filter_type == 'week':
            week_start = today - timedelta(days=today.weekday())
            return queryset.filter(**{f"{date_field}__gte": week_start})

        elif filter_type == 'month':
            month_start = today.replace(day=1)
            return queryset.filter(**{f"{date_field}__gte": month_start})

        elif filter_type == 'year':
            year_start = today.replace(month=1, day=1)
            return queryset.filter(**{f"{date_field}__gte": year_start})

        elif filter_type == 'custom' and start and end:
            s = datetime.strptime(start, "%Y-%m-%d").date()
            e = datetime.strptime(end, "%Y-%m-%d").date() + timedelta(days=1)
            return queryset.filter(**{f"{date_field}__gte": s, f"{date_field}__lt": e})

    except (ValueError, TypeError):
        raise ValidationError("Invalid date format. Expected YYYY-MM-DD.")

    return queryset