from ...views import *


class DashboardSummaryView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    SERVICE_TRANSACTION_MAP = {
        '44':  (MoneyTransferLog, 'provider'),
        '77':  (MoneyTransferLog, 'provider'),
        '73':  (PaymentGatewayRecord, 'partner'),
        '76':  (PaymentGatewayRecord, 'partner'),
        '11':  (RechargeHistory, 'service_partner'),
        '2':   (FundTransferEntry, 'partner'),
        '4':   (FundTransferEntry, 'partner'),
        '6':   (FundTransferEntry, 'partner'),
        '12':  (BillPaymentRecord, 'service_partner'),
        '45':  (BillPaymentRecord, 'service_partner'),
        '41':  (CashfreePaymentLog, 'partner'),
        '74':  (CashfreePaymentLog, 'partner'),
        '42':  (PhonePePaymentEntry, 'partner'),
        '75':  (PhonePePaymentEntry, 'partner'),
        '1':   (AadhaarVerifyLog, 'partner'),
        '8':   (ElectricityBillEntry, 'partner'),
        '9':   (GasBillEntry, 'partner'),
        '10':  (LicPremiumEntry, 'partner'),
        '80':  (AepsCashLog, 'partner'),
        '84':  (BulkPayoutRecord, 'vendor'),
        '85':  (AirtelBillEntry, 'vendor'),
        '86':  (BankItAepsRecord, 'partner'),
        '92':  (MicroAtmEntry, 'vendor'),
        '95':  (FundTransferEntry, 'partner'),
        '97':  (BankItAepsRecord, 'partner'),
        '103': (MicroAtmEntry, 'vendor'),
        '106': (PpiTransferLog, 'partner'),
        '109': (KhataTransferEntry, 'vendor'),
    }

    def post(self, request):
        admin_id = request.data.get('admin_id')

        if not admin_id:
            return Response({
                "status": "fail",
                "message": "admin_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin = Admin.objects.get(admin_id=admin_id)
            switch_to_database(admin.db_name)

            providers = AdServiceProvider.objects.filter(
                Q(self_managed=True) | Q(sa_provided=True),
                parent__isnull=True
            )

            services_data = []

            for provider in providers:
                sp_key = str(provider.sp_id)

                if sp_key not in self.SERVICE_TRANSACTION_MAP:
                    continue

                app_label, model_name = self.SERVICE_TRANSACTION_MAP[sp_key][0].split('.')
                related_field = self.SERVICE_TRANSACTION_MAP[sp_key][1]

                try:
                    model = apps.get_model(app_label=app_label, model_name=model_name)
                    txn_count = model.objects.filter(**{related_field: provider}).count()
                except:
                    txn_count = 0

                services_data.append({
                    "service_label": provider.display_name or provider.provider_name,
                    "service_type": provider.service.title,
                    "provider_id": provider.sp_id,
                    "is_active": not provider.is_disabled,
                    "total_transactions": txn_count
                })
                
            hierarchy = {
                "super_distributors": PortalUserInfo.objects.filter(role='DISTRIBUTOR', hierarchy__code='SD').count(),
                "master_distributors": PortalUserInfo.objects.filter(role='DISTRIBUTOR', hierarchy__code='MD').count(),
                "distributors": PortalUserInfo.objects.filter(role='DISTRIBUTOR', hierarchy__code='DT').count(),
                "retailers": PortalUserInfo.objects.filter(role='RETAILER').count(),
            }

            return Response({
                "status": "success",
                "message": "Dashboard summary loaded successfully",
                "data": {
                    "active_services": services_data,
                    **hierarchy
                }
            }, status=status.HTTP_200_OK)

        except Admin.DoesNotExist:
            return Response({
                "status": "fail",
                "message": "Admin not found"
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)