from django.urls import path
from web_portal.APIs.superadmincreation.superadmin_manage import *
from web_portal.APIs.login_flow.superadmin_login import *
from web_portal.APIs.banners.banner import *
from web_portal.APIs.about.aboutus import*
from web_portal.APIs.lattest_news.lattestnewshub import*
from web_portal.APIs.contactsupport.customer_contactsupport import*

urlpatterns = [
    path('', SuperAdminManageView.as_view()),
    path('login/', AdminSignInView.as_view()),
    path('change-password/', UpdateInitialPasswordView.as_view()),
    path('verify-otp/', TOTPVerificationView.as_view()),
    path('forgot-password/', ForgotPasswordRequestView.as_view()),
    path('verify-reset-code/', ConfirmResetCodeView.as_view()),
    path('reset-password/', FinalizePasswordResetView.as_view()),
    
    #adminbanner
    path('admin-banner/',AdminBannerView.as_view()),
    
    #aboutus
    path('about-us/',AboutusView.as_view()),
    
    #Latestnewshubview
    path('latest-news-hub/',LatestnewshubView.as_view()),
    path('home-abous-us-page/',PublicaboutusView.as_view()),
    
    #contactsupport
    path('customer-contact-support/',ContactSupportView.as_view()),
    path('add-contact/',AddContactSupportView.as_view()),
]