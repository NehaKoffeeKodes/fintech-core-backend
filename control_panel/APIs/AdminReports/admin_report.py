from ...views import *


class SuperAdminTransactionReportView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            if request.data.get('page_number') is not None or request.data.get('page_size') is not None:
                return self.generate_paginated_report(request)
            else:
                return Response(
                    {"status": "fail", "message": "Invalid request parameters."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as exc:
            return Response(
                {"status": "error", "message": f"Server error occurred: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve_all_database_names(self):
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
                return [row[0] for row in cur.fetchall()]
        except Exception as exc:
            print(f"Error listing databases: {exc}")
            return []

    def resolve_service_and_provider_details(self, provider_id, database_alias):
        try:
            if not provider_id:
                return None, None

            ad_provider = AdServiceProvider.objects.using(database_alias).filter(sp_id=provider_id).first()
            if not ad_provider or not ad_provider.sys_id:
                return None, None

            main_provider = ServiceProvider.objects.filter(sys_id=ad_provider.sys_id).select_related('service').first()
            if not main_provider:
                return None, None

            service_title = main_provider.service.service_name if main_provider.service else "Unknown"
            provider_title = main_provider.sp_name or "Unknown Provider"

            return service_title, provider_title
        except Exception as exc:
            print(f"Error resolving provider details: {exc}")
            return None, None

    def generate_paginated_report(self, request):
        try:
            page_num = int(request.data.get('page_number', 1))
            page_sz = int(request.data.get('page_size', 10))
            admin_identifier = request.data.get('admin_id', '').strip()
            order_direction = request.data.get('sort_by', 'desc').lower()
            min_amt = request.data.get('min_amount')
            max_amt = request.data.get('max_amount')
            date_range_type = request.data.get('date_filter', '')
            from_date = request.data.get('start_date', '')
            to_date = request.data.get('end_date', '')
            search_term = request.data.get('search', '').strip().lower()
            target_sp_id = int(request.data.get('sp_id', 0))  

            report_entries = []

            if admin_identifier:
                try:
                    target_admin = Admin.objects.get(admin_id=admin_identifier)
                    database_list = [target_admin.db_name]
                except ObjectDoesNotExist:
                    return Response(
                        {"status": "fail", "message": "Specified admin not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                all_dbs = self.retrieve_all_database_names()
                database_list = all_dbs[2:] if len(all_dbs) > 2 else []

            transaction_mappings = {
                "2": {"model": FundTransferEntry, "table": "ad_dmt_transaction", "sp_field": "dmt_sp_id", "amt_field": "dmt_txn_amount", "status_field": "dmt_txn_status", "cust_name": "dmt_customer_name", "cust_mobile": "dmt_customer_contact_number", "ref_id": "dmt_refrence_id"},
                "4": {"model": FundTransferEntry, "table": "ad_dmt_transaction", "sp_field": "dmt_sp_id", "amt_field": "dmt_txn_amount", "status_field": "dmt_txn_status", "cust_name": "dmt_customer_name", "cust_mobile": "dmt_customer_contact_number", "ref_id": "dmt_refrence_id"},
                "6": {"model": FundTransferEntry, "table": "ad_dmt_transaction", "sp_field": "dmt_sp_id", "amt_field": "dmt_txn_amount", "status_field": "dmt_txn_status", "cust_name": "dmt_customer_name", "cust_mobile": "dmt_customer_contact_number", "ref_id": "dmt_refrence_id"},
                "8": {"model": ElectricityBillEntry, "table": "ad_ux_electricity_transaction", "sp_field": "sp", "amt_field": "amount", "status_field": "ux_status", "cust_name": "consumer_name", "cust_mobile": "mobile_number", "ref_id": "ux_unique_trn_id"},
                "9": {"model": GasBillEntry, "table": "ad_ux_gas_transaction", "sp_field": "sp", "amt_field": "amount", "status_field": "ux_status", "cust_name": "consumer_name", "cust_mobile": "mobile_number", "ref_id": "ux_unique_trn_id"},
                "10": {"model": LicPremiumEntry, "table": "ad_ux_LIC_transaction", "sp_field": "sp", "amt_field": "amount", "status_field": "ux_lic_status", "cust_name": "", "cust_mobile": "mobile_number", "ref_id": "ux_lic_unique_trn_id"},
                "11": {"model": RechargeTransaction, "table": "ad_mobile_recharge", "sp_field": "mr_sp", "amt_field": "mr_amount", "status_field": "mr_status", "cust_name": "", "cust_mobile": "mr_mobile_no", "ref_id": "mr_request_txnid"},
                "12": {"model": BillPaymentRecord, "table": "ad_bbps_service_trnasaction", "sp_field": "bbps_sp", "amt_field": "bbps_amount", "status_field": "bbps_status", "cust_name": "", "cust_mobile": "bbps_contact_no", "ref_id": "bbps_request_id"},
                "41": {"model": CashfreePaymentLog, "table": "ad_cashfree_pg_service_transaction", "sp_field": "sp", "amt_field": "cf_pg_trn_amount", "status_field": "cf_pg_trn_status", "cust_name": "", "cust_mobile": "cf_pg_customer_contact_no", "ref_id": "cf_pg_trn_unique_id"},
                "42": {"model": PhonePePaymentEntry, "table": "ad_phonepe_service_transaction", "sp_field": "sp", "amt_field": "pp_amount", "status_field": "pp_status", "cust_name": "", "cust_mobile": "pp_contact_no", "ref_id": "pp_marchant_trn_id"},
                "43": {"model": PaymentGatewayRecord, "table": "ad_pg_service_trnasaction", "sp_field": "sp", "amt_field": "pg_trn_amount", "status_field": "pg_trn_status", "cust_name": "pg_customer_name", "cust_mobile": "pg_customer_contact_no", "ref_id": "pg_customer_id"},
                "44": {"model": MoneyTransferLog, "table": "ad_payout_service_trnasaction", "sp_field": "sp", "amt_field": "trn_amount", "status_field": "trn_status", "cust_name": "customer_name", "cust_mobile": "customer_contact_no", "ref_id": "trn_unique_id"},
                "47": {"model": AepsCashLog, "table": "ad_aeps_transaction", "sp_field": "at_sp", "amt_field": "at_amount", "status_field": "at_status", "cust_name": "", "cust_mobile": "at_mobile_number", "ref_id": "at_unique_id"},
                "48": {"model": AepsCashLog, "table": "ad_aeps_transaction", "sp_field": "at_sp", "amt_field": "at_amount", "status_field": "at_status", "cust_name": "", "cust_mobile": "at_mobile_number", "ref_id": "at_unique_id"},
                "49": {"model": AepsCashLog, "table": "ad_aeps_transaction", "sp_field": "at_sp", "amt_field": "at_amount", "status_field": "at_status", "cust_name": "", "cust_mobile": "at_mobile_number", "ref_id": "at_unique_id"},
                "50": {"model": AepsCashLog, "table": "ad_aeps_transaction", "sp_field": "at_sp", "amt_field": "at_amount", "status_field": "at_status", "cust_name": "", "cust_mobile": "at_mobile_number", "ref_id": "at_unique_id"},
                "51": {"model": BulkPayoutRecord, "table": "ad_bulk_pe_customer_transaction", "sp_field": "sp", "amt_field": "amount", "status_field": "payout_status", "cust_name": "customer", "cust_mobile": "customer", "ref_id": "transaction_id"},
                "52": {"model": AirtelBillEntry, "table": "ad_airtel_cms_transaction", "sp_field": "trn_sp", "amt_field": "trn_amount", "status_field": "trn_status", "cust_name": "", "cust_mobile": "trn_mobile_no", "ref_id": "trn_transaction_id"},
                "53": {"model": BankItAepsRecord, "table": "ad_bankit_aeps_transaction", "sp_field": "ba_sp", "amt_field": "ba_amount", "status_field": "ba_status", "cust_name": "", "cust_mobile": "ba_mobile", "ref_id": "ba_trn_id"},
                "59": {"model": MicroAtmEntry, "table": "ad_micro_atm_transaction", "sp_field": "mat_sp", "amt_field": "mat_amount", "status_field": "mat__status", "cust_name": "", "cust_mobile": "mat_mobile", "ref_id": "mat_trn_id"},
                "62": {"model": FundTransferEntry, "table": "ad_dmt_transaction", "sp_field": "dmt_sp_id", "amt_field": "dmt_txn_amount", "status_field": "dmt_txn_status", "cust_name": "dmt_customer_name", "cust_mobile": "dmt_customer_contact_number", "ref_id": "dmt_refrence_id"},
                "64": {"model": PpiTransferLog, "table": "ad_dmt_ppi_transaction", "sp_field": "dpt_sp", "amt_field": "dpt_amount", "status_field": "dpt_status", "cust_name": "", "cust_mobile": "dpt_contact_no", "ref_id": "dpt_txn_id"},
                "67": {"model": KhataTransferEntry, "table": "ad_digi_khata_transaction", "sp_field": "dkt_sp", "amt_field": "dkt_txn_amount", "status_field": "dkt_txn_status", "cust_name": "dkt_customer_name", "cust_mobile": "dkt_customer_contact_number", "ref_id": "dkt_refrence_id"},
            }

            for db_alias in database_list:
                db_alias = switch_to_database(db_alias)
                print(f"Processing database: {db_alias}")

                try:
                    global_transactions = GlTrn.objects.using(db_alias).filter(
                        pu_id=1, effectvie_wallet="main_wallet"
                    )

                    user_ids = [gt.pu_id for gt in global_transactions]
                    portal_user_cache = PortalUser.objects.using(db_alias).in_bulk(user_ids)

                    for global_trn in global_transactions:
                        try:
                            service_table = str(global_trn.service_trn_table)

                            config = None
                            if target_sp_id > 0:
                                config = transaction_mappings.get(str(target_sp_id))
                                if config and config["model"]._meta.db_table != service_table:
                                    config = None
                            else:
                                for cfg in transaction_mappings.values():
                                    if cfg["model"]._meta.db_table == service_table:
                                        config = cfg
                                        break

                            if not config:
                                continue

                            TransactionModel = config["model"]
                            sp_field_name = config["sp_field"]
                            ref_id_field = config["ref_id"]

                            txn_record = TransactionModel.objects.using(db_alias).get(pk=global_trn.service_trn_id)

                            reference_id = getattr(txn_record, ref_id_field, "")

                            sp_id_value = getattr(txn_record, f"{sp_field_name}_id", None) or getattr(txn_record, sp_field_name, None)

                            service_title, provider_title = self.resolve_service_and_provider_details(sp_id_value, db_alias)
                            if not service_title or not provider_title:
                                continue

                            portal_user_obj = portal_user_cache.get(global_trn.pu_id)
                            if not portal_user_obj:
                                continue

                            entry = {
                                "global_trn_id": global_trn.gl_trn_id,
                                "amount": global_trn.gl_trn_amt,
                                "effective_amount": global_trn.effectvie_amt,
                                "tds_amount": float(global_trn.gl_tds_amt or 0),
                                "tax_amount": float(global_trn.gl_tax_amt or 0),
                                "txn_datetime": global_trn.created_at.strftime("%d %B %Y %H:%M"),
                                "reference_id": reference_id,
                                "service": service_title,
                                "provider": provider_title,
                                "user_name": portal_user_obj.pu_name,
                            }

                            report_entries.append(entry)

                        except TransactionModel.DoesNotExist:
                            continue
                        except Exception as inner_exc:
                            print(f"Error processing global trn {global_trn.gl_trn_id}: {inner_exc}")
                            continue

                finally:
                    connections[db_alias].close()

            total_count = len(report_entries)
            paginator = Paginator(report_entries, page_sz)
            try:
                current_page = paginator.get_page(page_num)
            except Exception:
                current_page = paginator.get_page(1)

            page_data = list(current_page.object_list)
            add_serial_numbers(page_num, page_sz, page_data, order_direction)

            response_payload = {
                "total_items": total_count,
                "total_pages": paginator.num_pages,
                "current_page": page_num,
                "results": page_data
            }

            return Response(
                {"status": "success", "message": "Transaction report generated successfully.", "data": response_payload},
                status=status.HTTP_200_OK
            )

        except Exception as exc:
            return Response(
                {"status": "error", "message": f"Unexpected error: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )