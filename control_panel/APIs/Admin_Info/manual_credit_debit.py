from ...views import *


class AdminWalletAdjustmentView(APIView):
    """
    Super Admin ke liye manual credit/debit aur transaction reversal
    Tere naye sundar models ke saath perfect sync!
    """
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]


    SERVICE_TXN_MAPPING = {
        '2':  (FundTransferEntry, 'reference_code', 'current_status', 'transfer_amount'),
        '4':  (FundTransferEntry, 'reference_code', 'current_status', 'transfer_amount'),
        '6':  (FundTransferEntry, 'reference_code', 'current_status', 'transfer_amount'),
        '8':  (ElectricityBillEntry, 'unique_ref', 'bill_status', 'bill_amount'),
        '9':  (GasBillEntry, 'transaction_ref', 'payment_status', 'due_amount'),
        '10': (LicPremiumEntry, 'lic_ref_id', 'premium_status', 'premium_amount'),
        '11': (RechargeHistory, 'request_txn_id', 'recharge_status', 'recharge_amount'),
        '12': (BillPaymentRecord, 'request_ref', 'payment_status', 'bill_amount'),
        '45': (BillPaymentRecord, 'request_ref', 'payment_status', 'bill_amount'),
        '41': (CashfreePaymentLog, 'cf_order_id', 'payment_status', 'payment_amount'),
        '74': (CashfreePaymentLog, 'cf_order_id', 'payment_status', 'payment_amount'),
        '42': (PhonePePaymentEntry, 'merchant_txn_id', 'current_status', 'amount_paid'),
        '75': (PhonePePaymentEntry, 'merchant_txn_id', 'current_status', 'amount_paid'),
        '44': (MoneyTransferLog, 'reference_code', 'transfer_status', 'transfer_amount'),
        '77': (MoneyTransferLog, 'reference_code', 'transfer_status', 'transfer_amount'),
        '80': (AepsCashLog, 'reference_no', 'current_status', 'txn_amount'),
        '84': (BulkPayoutRecord, 'payout_ref', 'payout_result', 'transfer_amount'),
        '85': (AirtelBillEntry, 'cms_ref', 'bill_status', 'bill_amount'),
        '86': (BankItAepsRecord, 'bankit_txn', 'txn_status', 'amount'),
        '92': (MicroAtmEntry, 'txn_ref', 'current_status', 'txn_amount'),
        '95': (FundTransferEntry, 'reference_code', 'current_status', 'transfer_amount'),
        '97': (BankItAepsRecord, 'bankit_txn', 'txn_status', 'amount'),
        '103':(MicroAtmEntry, 'txn_ref', 'current_status', 'txn_amount'),
        '106':(PpiTransferLog, 'txn_ref_id', 'txn_status', 'amount'),
        '109':(KhataTransferEntry, 'reference_no', 'current_status', 'transfer_amount'),
    }

    def post(self, request):
        try:
            if request.data.get('fetch_amount'):
                return self.get_transaction_details(request)
            elif request.data.get('admin_id'):
                return self.process_adjustment(request)
            else:
                return Response({
                    "status": "fail",
                    "message": "Invalid request"
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data,
                {"status": "error", "error": str(e)},
                None, service_type="Admin Wallet Adjustment", client_override="tcpl_db"
            )
            return Response({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=500)

    def get_transaction_details(self, request):
        sp_id = request.data.get('sp_id')
        admin_id = request.data.get('admin_id')
        txn_ref = request.data.get('transaction_id')

        save_api_log(request, "OwnAPI", request.data, {"status": "processing"}, None,
                            service_type="Fetch Reversal Amount", client_override="tcpl_db")

        if not all([sp_id, admin_id, txn_ref]):
            return Response({"status": "fail", "message": "Missing required fields"}, status=400)

        try:
            admin = Admin.objects.get(admin_id=admin_id)
            switch_to_database(admin.db_name)

            partner = ServiceProvider.objects.using(admin.db_name).get(
                master_id=sp_id
            )

            if str(sp_id) not in self.SERVICE_TXN_MAPPING:
                return Response({"status": "fail", "message": "Service not supported"}, status=400)

            app_label, model_name, ref_field, status_field, amount_field = self.SERVICE_TXN_MAPPING[str(sp_id)]
            model = apps.get_model(app_label, model_name)

            transaction = model.objects.using(admin.db_name).get(**{ref_field: txn_ref})
            current_status = getattr(transaction, status_field)

            if current_status == "REVERSED":
                return Response({"status": "fail", "message": "Already reversed"}, status=400)

            gl_entries = GlTrn.objects.using(admin.db_name).filter(
                service_table=transaction._meta.db_table,
                service_record_id=transaction.pk
            )

            wallet_entries = WalletHistory.objects.using(admin.db_name).filter(
                linked_global_txn__in=gl_entries,
                user_id=1
            )

            results = []
            main_wallet = PortalUserBalance.objects.using(admin.db_name).get(user_id=1)

            for entry in wallet_entries:
                current_bal = getattr(main_wallet, entry.wallet_type, 0)
                if entry.entry_type == 'CR':
                    new_bal = current_bal - entry.amount
                    reverse = 'DR'
                else:
                    new_bal = current_bal + entry.amount
                    reverse = 'CR'

                results.append({
                    "amount": float(entry.amount),
                    "type": entry.entry_type,
                    "wallet": entry.wallet_type,
                    "current": float(current_bal),
                    "after_reverse": float(new_bal),
                    "reverse_type": reverse
                })

            save_api_log(request, "OwnAPI", request.data, {"status": "success"}, None,
                                service_type="Fetch Reversal Amount", client_override="tcpl_db")

            return Response({
                "status": "success",
                "message": "Amount details fetched",
                "data": results
            })

        except Exception as e:
            save_api_log(request, "OwnAPI", request.data, {"status": "error", "msg": str(e)}, None,
                                service_type="Fetch Reversal Amount", client_override="tcpl_db")
            return Response({"status": "error", "message": str(e)}, status=500)

    def process_adjustment(self, request):
        admin_id = request.data.get('admin_id')
        charge_type = request.data.get('charge_type')  
        amount = request.data.get('amount')
        wallet = request.data.get('wallet')
        description = request.data.get('description', '')

        save_api_log(request, "OwnAPI", request.data, {"status": "processing"}, None,
                            service_type="Manual Wallet Adjustment", client_override="tcpl_db")

        try:
            admin = Admin.objects.get(admin_id=admin_id)
            switch_to_database(admin.db_name)

            main_user = PortalUser.objects.using(admin.db_name).get(id=1)
            user_wallet = PortalUserBalance.objects.using(admin.db_name).get(user=main_user)

            
            if charge_type:
                current = decimal.Decimal(getattr(user_wallet, wallet, 0))
                if charge_type == 'CR':
                    new_balance = current + decimal.Decimal(amount)
                elif charge_type == 'DR':
                    new_balance = current - decimal.Decimal(amount)
                else:
                    return Response({"status": "fail", "message": "Invalid type"}, status=400)

                setattr(user_wallet, wallet, new_balance)
                user_wallet.save(using=admin.db_name)

                label = super_admin_action_label(
                    "MANUAL ADJUSTMENT", None, charge_type, float(amount), wallet, description, None
                )

                if float(amount) > 0:
                    WalletHistory.objects.using(admin.db_name).create(
                        user=main_user,
                        action="MANUAL_ADJUSTMENT",
                        label=label,
                        balance_after=new_balance,
                        wallet_type=wallet,
                        amount=float(amount),
                        entry_type=charge_type,
                        created_at=now()
                    )

                save_api_log(request, "OwnAPI", request.data, {"status": "success"}, None,
                                    service_type="Manual Wallet Adjustment", client_override="tcpl_db")
                return Response({
                    "status": "success",
                    "message": f"Wallet {charge_type} successful"
                })

            sp_id = request.data.get('sp_id')
            txn_ref = request.data.get('transaction_id')

            partner = ServiceProvider.objects.using(admin.db_name).get(master_id=sp_id)

            if str(sp_id) not in self.SERVICE_TXN_MAPPING:
                return Response({"status": "fail", "message": "Service not supported"}, status=400)

            app_label, model_name, ref_field, status_field, amount_field = self.SERVICE_TXN_MAPPING[str(sp_id)]
            model = apps.get_model(app_label, model_name)

            transaction = model.objects.using(admin.db_name).get(**{ref_field: txn_ref})
            if getattr(transaction, status_field) == "REVERSED":
                return Response({"status": "fail", "message": "Already reversed"}, status=400)

            setattr(transaction, status_field, 'REVERSED')
            transaction.save(using=admin.db_name)

            # Reverse wallet entries
            gl_entries = GlTrn.objects.using(admin.db_name).filter(
                service_table=transaction._meta.db_table,
                service_record_id=transaction.pk
            )

            for gl in gl_entries:
                wallet_entries = WalletHistory.objects.using(admin.db_name).filter(
                    linked_global_txn=gl, user_id=1
                )
                for w in wallet_entries:
                    reverse_type = 'DR' if w.entry_type == 'CR' else 'CR'
                    new_bal = getattr(user_wallet, w.wallet_type) + (w.amount if reverse_type == 'CR' else -w.amount)
                    setattr(user_wallet, w.wallet_type, new_bal)

                    label = super_admin_action_label(
                        "TRANSACTION REVERSAL", f"{partner.provider_name} - {txn_ref}",
                        reverse_type, float(w.amount), w.wallet_type, description, None
                    )

                    WalletHistory.objects.using(admin.db_name).create(
                        user=main_user,
                        action="REVERSAL",
                        label=label,
                        balance_after=new_bal,
                        wallet_type=w.wallet_type,
                        amount=float(w.amount),
                        entry_type=reverse_type,
                        linked_global_txn=gl,
                        created_at=now()
                    )

            # Mark govt levy as deleted
            GovernmentChargeLog.objects.using(admin.db_name).filter(
                provider_id=sp_id, transaction_ref=txn_ref
            ).update(is_deleted=True)

            save_api_log(request, "OwnAPI", request.data, {"status": "success"}, None,
                                service_type="Transaction Reversal", client_override="tcpl_db")

            return Response({
                "status": "success",
                "message": "Transaction reversed successfully"
            })

        except Exception as e:
            save_api_log(request, "OwnAPI", request.data, {"status": "error", "msg": str(e)}, None,
                                service_type="Wallet Adjustment", client_override="tcpl_db")
            return Response({"status": "error", "message": str(e)}, status=500)