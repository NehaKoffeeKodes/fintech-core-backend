from rest_framework.response import Response
from rest_framework import status
from control_panel.models import*

def record_member_activity(activity_data: dict):
    """
    Log user activity with proper try-except and response
    Same logic as add_user_activity
    """
    try:
        MemberActionLog.objects.create(**activity_data)
        return Response({
            "status": "success",
            "message": "Activity recorded successfully"
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({
            "status": "error",
            "message": "Failed to record activity"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)