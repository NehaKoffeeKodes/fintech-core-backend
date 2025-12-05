from django.urls import path
from web_portal.APIs.superadmincreation.superadmin_manage import *
from web_portal.APIs.superadmin_login_details.superadmin_login import *
from web_portal.APIs.banners.banner import *
from web_portal.APIs.about.aboutus import*
from web_portal.APIs.latest_announcement.latest_announcement import*
from web_portal.APIs.contactsupport.customer_contactsupport import*
from web_portal.APIs.contact_info.contact_info import*
from web_portal.APIs.latestnews_update.news_hub import*
from web_portal.APIs.latestnews_update.news_hub import*
from web_portal.APIs.sponsor.sponsors import *
from web_portal.APIs.siteconfig.site_configs import*
from web_portal.APIs.services_category.services import*

urlpatterns = [
    #Admin_LOGIN_DETAILS
    path('', SuperAdminManageView.as_view()),
    path('login/', AdminSignInView.as_view()),
    path('change-password/', UpdateInitialPasswordView.as_view()),
    path('verify-otp/', TOTPVerificationView.as_view()),
    path('forgot-password/', ForgotPasswordRequestView.as_view()),
    path('verify-reset-code/', ConfirmResetCodeView.as_view()),
    path('reset-password/', FinalizePasswordResetView.as_view()),
    
    #ADMIN_BANNER
    path('admin-banner/',AdminBannerView.as_view()),
    
    #ABOUT_US
    path('about-us/',AboutusView.as_view()),
    path('public-about-us/',PublicaboutusView.as_view()),
    
    #LATEST_ANNOUNCEMENT
    path('latest-announcement/',LatestAnnouncementView.as_view()),
    path('home-abous-us-page/',PublicaboutusView.as_view()),
    
    #CONTACT_SUPPORT
    path('customer-contact-support/',ContactSupportView.as_view()),
    path('add-contact/',AddContactSupportView.as_view()),
    
    #CONTACT_INFO
    path('contact-info/',ContactInfoView.as_view()),
    
    #LATESTNEWS_UPDATE
    path('news-hub/',NewsUpdateView.as_view()),
    
    #SPONSOR
    path('sponsor/',SponsorView.as_view()),
    path('public-sponsor/',PublicSponsorView.as_view()),
    
    #SITECONFIG
    path('site-config/',SiteConfigView.as_view()),
    path('public-site-config/',PublicSiteInfoView.as_view()),
    
    #SERVICE_CATEGORY
    path('service-category/',ServiceCategoryView.as_view()),
    path('public-category/',PublicCategoryView.as_view()),
    path('Public-category-products/',PublicCategoryWithProducts.as_view()),
]