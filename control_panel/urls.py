from django.urls import path
from control_panel.APIs.AdminReports.admin_report import *
from control_panel.APIs.Admin_Info.a_credentials import *
from control_panel.APIs.Admin_Info.admin_static import *
from control_panel.APIs.Admin_Info.bank_verification import *
from control_panel.APIs.Admin_Info.change_pass_word import *
from control_panel.APIs.Admin_Info.create_admin import *
from control_panel.APIs.Admin_Info.dmt_priority import *
from control_panel.APIs.Admin_Info.manual_credit_debit import *
from control_panel.APIs.Admin_Transaction.admin_dispute import *
from control_panel.APIs.Admin_service_charges.admin_service_charge import *
from control_panel.APIs.City.city import*
from control_panel.APIs.HSNSAC.hsn_sac import*
from control_panel.APIs.Admin_Info.admin_login_log_details import *
from control_panel.APIs.Admin_Info.admin_session_pass import*
from control_panel.APIs.Admin_Info.pan_verification import*
from control_panel.APIs.Admin_Info.block_admin import*
from control_panel.APIs.Admin_Info.bank_details import*
from control_panel.APIs.Admin_Info.change_pass_word import*
from control_panel.APIs.Admin_Info.fund_request import*
from control_panel.APIs.Admin_Info.gst_tax_verification import*
from control_panel.APIs.Admin_Info.s_admin_other_charges import *
from control_panel.APIs.Admin_Info.required_documents_list import *
from control_panel.APIs.State.state_create import StateAPIView
from control_panel.APIs.Device_booking.device import *
from control_panel.APIs.Product_Item.product import *
from control_panel.APIs.Product_category.productitem_category import *
from control_panel.APIs.Sa_service.service import *
from control_panel.APIs.admin_charges.charges import *
from control_panel.APIs.admin_limit_config.limitconfig import *
from control_panel.send_otp import *


urlpatterns = [
    #CREATE_ADMIN
    path('create-admin/',AdminManagementAPIView.as_view()),
    
    #HSNSAC
    path('gst-code-manage/',GSTCodeManagerView.as_view()),
    
    path('city/', CityAPIView.as_view()),
    
    path('state/',StateAPIView.as_view()),
    
    #CHANGE_PASSWORD
    path('change-password/',UpdatePasswordView.as_view()),
    
    #pan_verification
    path('pan-verification/',PanVerificationView.as_view()),
    
    #ADMIN_BLOCK
    path('admin-block/',AdminBlockView.as_view()),
    
    #ADMIN_LOGIN_DETAILS 
    path('admin-login-detail/',AdminLoginDetailView.as_view()),
    
    #ADMIN_SESSION_BY_PASS
    path('admin-session-bypass/',AdminSessionByPassView.as_view()),
    path('verify-session-bypass/',VerifySessionBypass.as_view()),
    
    #Fund_REQUEST
    path('manage-fund-requests/',ManageFundRequestsView.as_view()),
    
    #ADMIN_CHARGES
    path('charge-management/',ChargeManagementAPIView.as_view()),
    
    #credentials
    path('sms-settings/',SMSSettingsView.as_view()),
    path('email-settings/',EmailSettingsView.as_view()),
    
    #bank_account_verification
    path('bankaccount-verification/',BankAccountVerificationView.as_view()),
    
    #BANK_DETAILS
    path('manage-bank-deposite/',ManageDepositBanksAPIView.as_view()),
    
    #manual_credit_debit
    path('admin-wallet-adjustment/',AdminWalletAdjustmentView.as_view()),
    
    #GST_TAX_VERIFICATION
    path('verify-gst/',VerifyGSTApiView.as_view()),
    
    #DMT_PRIORITY
    path('dmt-priority/',DmtPriorityView.as_view()),
    
    #SUPER_ADMIN_OTHER_CHARGES
    path('sa-manage-charges/',SaManageChargesView.as_view()),
    
    #admin_limit_config
    path('limit-config-rule/',LimitConfigRuleView.as_view()),
    
    #ADMIN_SERVICE_CHARGES
    path('service-charges-management/',ServiceChargesManagementView.as_view()),
    
    #ADMIN_TRANSACTION
    path('admin-dispute-records/',AdminDisputeRecordsView.as_view()),
    
    #ADMIN_REPORTS
    path('transaction-report/',SuperAdminTransactionReportView.as_view()),
    
    #REQUIRED_DOCUMENT_LIST
    path('manage-document/',ManageDocumentTemplatesView.as_view()),
    
    #send-otp
    path('api/send-otp-email/', SendOTPEmailAPI.as_view(), name='send-otp-email'),
    
    #ADMIN_STATIC
    path('admin-static/',DashboardSummaryView.as_view()),
    
    #PRODUCT_CATEGORY
    path('category-management/',CategoryManagementView.as_view()),
    
    #product_item
    path("product-management/",ProductManagementView.as_view()),
    
    #service_provider
    path('service-config-management/',ServiceConfigManagementView.as_view()),
    
    #device
    path('gadget-purchase/',GadgetPurchaseAPIView.as_view()),
    
    #views
    path('create-order',CreateOrderManager.as_view()),
    path('auth/',AuthView.as_view()),
    path('beneficiary-manage/',BeneficiaryManager.as_view()),
    path('fund-transfer/',FundTransferView.as_view()),
    path('dmt-ppi/',DMTPPIView.as_view()),
    
    
    
]