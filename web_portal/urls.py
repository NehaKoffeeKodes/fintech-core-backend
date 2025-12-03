from django.urls import path
from web_portal.superadmincreation.superadmin_manage import SuperAdminManage
from .APIs.login_flow.superadmin_login import (AdminSignInEndpoint,UpdateInitialPasswordEndpoint,TOTPVerificationEndpoint,ForgotPasswordRequestEndpoint,ConfirmResetCodeEndpoint,FinalizePasswordResetEndpoint,)

urlpatterns = [
    path('', SuperAdminManage.as_view(), name='manage-superadmins'),
    path('login/', AdminSignInEndpoint.as_view(), name='admin-login'),
    path('change-password/', UpdateInitialPasswordEndpoint.as_view(), name='change-initial-password'),
    path('verify-otp/', TOTPVerificationEndpoint.as_view(), name='verify-otp'),
    path('forgot-password/', ForgotPasswordRequestEndpoint.as_view(), name='forgot-password'),
    path('verify-reset-code/', ConfirmResetCodeEndpoint.as_view(), name='verify-reset-code'),
    path('reset-password/', FinalizePasswordResetEndpoint.as_view(), name='reset-password'),
]