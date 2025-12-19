from ...views import*

class AdminDisputeRecordsView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        try:
            if 'page_num' in request.data and 'page_size' in request.data:
                return self.list_complaint_records(request)
            elif 'perform_reverse' in request.data and 'txn_ref' in request.data:
                return self.execute_reversal(request)
            elif 'txn_ref' in request.data:
                return self.show_reversal_impact(request)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid payload structure.'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': f'Server error occurred: {str(exc)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_complaint_records(self, request):
        page_num = int(request.data.get('page_num', 1))
        page_size = int(request.data.get('page_size', 10))
        query_text = request.data.get('query', '')

        status_filter_raw = request.data.get('complaint_status', '')
        if isinstance(status_filter_raw, (int, float)):
            status_filter = str(int(status_filter_raw))
        elif isinstance(status_filter_raw, list):
            status_filter = ','.join(map(str, status_filter_raw))
        else:
            status_filter = str(status_filter_raw or '')

        status_list = [s.strip().upper() for s in status_filter.split(',') if s.strip()]

        admin_ids_raw = request.data.get('admin_ids', '')
        if isinstance(admin_ids_raw, (int, float)):
            admin_ids = str(int(admin_ids_raw))
        elif isinstance(admin_ids_raw, list):
            admin_ids = ','.join(map(str, admin_ids_raw))
        else:
            admin_ids = str(admin_ids_raw or '')

        admin_id_list = []
        if admin_ids:
            admin_id_list = [int(s.strip()) for s in admin_ids.split(',') if s.strip()]

        provider_id_raw = request.data.get('provider_id')
        provider_id = None
        if provider_id_raw is not None:
            try:
                provider_id = str(provider_id_raw)
            except:
                pass

        min_amt = request.data.get('min_amt')
        max_amt = request.data.get('max_amt')

        # validation_resp = add_serial_numbers(page_num, page_size)
        # if validation_resp:
        #     return validation_resp

        try:
            service_model_map = {
                '2': {
                    'model': FundTransferEntry,
                    'ref_field': 'mt_ref_no',
                    'status_field': 'mt_status',
                    'amount_field': 'mt_amt',
                    'table': 'svc_money_transfer',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'benef_mobile',
                    'cust_name': 'benef_name'
                },
                '4': {
                    'model': FundTransferEntry,
                    'ref_field': 'mt_ref_no',
                    'status_field': 'mt_status',
                    'amount_field': 'mt_amt',
                    'table': 'svc_money_transfer',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'benef_mobile',
                    'cust_name': 'benef_name'
                },
                '6': {
                    'model': FundTransferEntry,
                    'ref_field': 'mt_ref_no',
                    'status_field': 'mt_status',
                    'amount_field': 'mt_amt',
                    'table': 'svc_money_transfer',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'benef_mobile',
                    'cust_name': 'benef_name'
                },
                '8': {
                    'model': ElectricityBillEntry,
                    'ref_field': 'ubill_ref',
                    'status_field': 'ubill_status',
                    'amount_field': 'bill_amt',
                    'table': 'svc_utility_electricity',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'consumer_mobile',
                    'cust_name': 'consumer_name'
                },
                '9': {
                    'model': ElectricityBillEntry,
                    'ref_field': 'ubill_ref',
                    'status_field': 'ubill_status',
                    'amount_field': 'bill_amt',
                    'table': 'svc_utility_gas',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'consumer_mobile',
                    'cust_name': 'consumer_name'
                },
                '10': {
                    'model': ElectricityBillEntry,
                    'ref_field': 'ubill_ref',
                    'status_field': 'ubill_status',
                    'amount_field': 'bill_amt',
                    'table': 'svc_utility_lic',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'consumer_mobile',
                    'cust_name': 'consumer_name'
                },
                '11': {
                    'model': RechargeTransaction,
                    'ref_field': 'recharge_ref',
                    'status_field': 'recharge_status',
                    'amount_field': 'recharge_amt',
                    'table': 'svc_recharge',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'mobile_num',
                    'cust_name': ''
                },
                '12': {
                    'model': BillPaymentRecord,
                    'ref_field': 'bbps_ref_id',
                    'status_field': 'bbps_txn_status',
                    'amount_field': 'paid_amt',
                    'table': 'svc_bbps_payment',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'bill_mobile',
                    'cust_name': ''
                },
                '45': {
                    'model': BillPaymentRecord,
                    'ref_field': 'bbps_ref_id',
                    'status_field': 'bbps_txn_status',
                    'amount_field': 'paid_amt',
                    'table': 'svc_bbps_payment',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'bill_mobile',
                    'cust_name': ''
                },
                '41': {
                    'model': CashfreePaymentLog,
                    'ref_field': 'cf_order_ref',
                    'status_field': 'cf_txn_status',
                    'amount_field': 'cf_paid_amt',
                    'table': 'svc_cashfree_txn',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'payer_mobile',
                    'cust_name': ''
                },
                '74': {
                    'model': CashfreePaymentLog,
                    'ref_field': 'cf_order_ref',
                    'status_field': 'cf_txn_status',
                    'amount_field': 'cf_paid_amt',
                    'table': 'svc_cashfree_txn',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'payer_mobile',
                    'cust_name': ''
                },
                '42': {
                    'model': PhonePePaymentEntry,
                    'ref_field': 'pp_merchant_ref',
                    'status_field': 'pp_txn_status',
                    'amount_field': 'pp_paid_amt',
                    'table': 'svc_phonepe_txn',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'payer_contact',
                    'cust_name': ''
                },
                '75': {
                    'model': PhonePePaymentEntry,
                    'ref_field': 'pp_merchant_ref',
                    'status_field': 'pp_txn_status',
                    'amount_field': 'pp_paid_amt',
                    'table': 'svc_phonepe_txn',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'payer_contact',
                    'cust_name': ''
                },
                '43': {
                    'model': PaymentGatewayRecord,
                    'ref_field': 'pg_client_ref',
                    'status_field': 'pg_txn_status',
                    'amount_field': 'pg_transfer_amt',
                    'table': 'svc_pg_transaction',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'client_mobile',
                    'cust_name': 'client_name'
                },
                '76': {
                    'model': PaymentGatewayRecord,
                    'ref_field': 'pg_client_ref',
                    'status_field': 'pg_txn_status',
                    'amount_field': 'pg_transfer_amt',
                    'table': 'svc_pg_transaction',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'client_mobile',
                    'cust_name': 'client_name'
                },
                '44': {
                    'model': PaymentGatewayRecord,
                    'ref_field': 'payout_unique_ref',
                    'status_field': 'payout_status',
                    'amount_field': 'payout_amt',
                    'table': 'svc_payout',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'benef_contact',
                    'cust_name': 'benef_full_name'
                },
                '77': {
                    'model': PaymentGatewayRecord,
                    'ref_field': 'payout_unique_ref',
                    'status_field': 'payout_status',
                    'amount_field': 'payout_amt',
                    'table': 'svc_payout',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'benef_contact',
                    'cust_name': 'benef_full_name'
                },
                '80': {
                    'model': AepsCashLog,
                    'ref_field': 'aeps_ref_id',
                    'status_field': 'aeps_txn_status',
                    'amount_field': 'aeps_amt',
                    'table': 'svc_aeps',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'aeps_mobile',
                    'cust_name': ''
                },
                '81': {
                    'model': AepsCashLog,
                    'ref_field': 'aeps_ref_id',
                    'status_field': 'aeps_txn_status',
                    'amount_field': 'aeps_amt',
                    'table': 'svc_aeps',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'aeps_mobile',
                    'cust_name': ''
                },
                '82': {
                    'model': AepsCashLog,
                    'ref_field': 'aeps_ref_id',
                    'status_field': 'aeps_txn_status',
                    'amount_field': 'aeps_amt',
                    'table': 'svc_aeps',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'aeps_mobile',
                    'cust_name': ''
                },
                '83': {
                    'model': AepsCashLog,
                    'ref_field': 'aeps_ref_id',
                    'status_field': 'aeps_txn_status',
                    'amount_field': 'aeps_amt',
                    'table': 'svc_aeps',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'aeps_mobile',
                    'cust_name': ''
                },
                '84': {
                    'model': BulkPayoutRecord,
                    'ref_field': 'bulk_txn_id',
                    'status_field': 'bulk_status',
                    'amount_field': 'bulk_amt',
                    'table': 'svc_bulk_payout',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'bulk_benef_mobile',
                    'cust_name': 'bulk_benef_name'
                },
                '85': {
                    'model': AirtelBillEntry,
                    'ref_field': 'airtel_txn_ref',
                    'status_field': 'airtel_status',
                    'amount_field': 'airtel_amt',
                    'table': 'svc_airtel_cms',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'airtel_mobile',
                    'cust_name': ''
                },
                '86': {
                    'model': BankItAepsRecord,
                    'ref_field': 'bankit_ref',
                    'status_field': 'bankit_status',
                    'amount_field': 'bankit_amt',
                    'table': 'svc_bankit_aeps',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'bankit_mobile',
                    'cust_name': ''
                },
                '92': {
                    'model': MicroAtmEntry,
                    'ref_field': 'matm_ref',
                    'status_field': 'matm_status',
                    'amount_field': 'matm_amt',
                    'table': 'svc_micro_atm',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'matm_mobile',
                    'cust_name': ''
                },
                '95': {
                    'model': FundTransferEntry,
                    'ref_field': 'mt_ref_no',
                    'status_field': 'mt_status',
                    'amount_field': 'mt_amt',
                    'table': 'svc_money_transfer',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'benef_mobile',
                    'cust_name': 'benef_name'
                },
                '97': {
                    'model': BankItAepsRecord,
                    'ref_field': 'bankit_ref',
                    'status_field': 'bankit_status',
                    'amount_field': 'bankit_amt',
                    'table': 'svc_bankit_aeps',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'bankit_mobile',
                    'cust_name': ''
                },
                '103': {
                    'model': MicroAtmEntry,
                    'ref_field': 'matm_ref',
                    'status_field': 'matm_status',
                    'amount_field': 'matm_amt',
                    'table': 'svc_micro_atm',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'matm_mobile',
                    'cust_name': ''
                },
                '106': {
                    'model': PpiTransferLog,
                    'ref_field': 'ppi_txn_ref',
                    'status_field': 'ppi_status',
                    'amount_field': 'ppi_amt',
                    'table': 'svc_dmt_ppi',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'ppi_contact',
                    'cust_name': ''
                },
                '109': {
                    'model': KhataTransferEntry,
                    'ref_field': 'digi_ref_id',
                    'status_field': 'digi_txn_status',
                    'amount_field': 'digi_txn_amt',
                    'table': 'svc_digi_ledger',
                    'creator_field': 'initiated_by',
                    'cust_mobile': 'digi_customer_mobile',
                    'cust_name': 'digi_customer_name'
                },
            }

            complaints_qs = Servicedispute.objects.all().order_by('-created_on')

            if admin_id_list:
                complaints_qs = complaints_qs.filter(admin__in=admin_id_list)

            if query_text:
                base_q = Q(txn_ref__icontains=query_text)
                admin_ids = Admin.objects.filter(name__icontains=query_text).values_list('admin_id', flat=True)
                if admin_ids:
                    base_q |= Q(admin__in=admin_ids)

                provider_ids = ServiceProvider.objects.filter(display_label__icontains=query_text).values_list('sp_id', flat=True)
                if provider_ids:
                    base_q |= Q(provider_id__in=provider_ids)

                complaints_qs = complaints_qs.filter(base_q)

            if provider_id:
                complaints_qs = complaints_qs.filter(provider_id=provider_id)  # already str → int safe

            complaints_qs = apply_date_range_filter(request.data, complaints_qs, date_field='created_on')

            min_amt_raw = request.data.get('min_amt')
            max_amt_raw = request.data.get('max_amt')

            min_amt = None
            if min_amt_raw not in (None, '', []):
                try:
                    min_amt = float(min_amt_raw)
                except (ValueError, TypeError):
                    pass 

            max_amt = None
            if max_amt_raw not in (None, '', []):
                try:
                    max_amt = float(max_amt_raw)
                except (ValueError, TypeError):
                    pass 

            if min_amt is not None:
                complaints_qs = complaints_qs.filter(txn_amount__gte=min_amt)
            if max_amt is not None:
                complaints_qs = complaints_qs.filter(txn_amount__lte=max_amt)

            start_idx = (page_num - 1) * page_size
            end_idx = start_idx + page_size
            paginated_records = complaints_qs[start_idx:end_idx]
            total_count = complaints_qs.count()
            total_pages = (total_count + page_size - 1) // page_size

            serialized_data = DisputeRecordSerializer(paginated_records, many=True).data

            for item in serialized_data:
                if item.get('created_on'):
                    try:
                        parsed_dt = datetime.strptime(item['created_on'], "%Y-%m-%dT%H:%M:%S.%f%z")
                    except ValueError:
                        parsed_dt = datetime.strptime(item['created_on'], "%Y-%m-%dT%H:%M:%S%z")
                    item['created_on'] = localtime(parsed_dt).strftime("%d-%m-%Y %I:%M %p")

                item['provider_name'] = None
                item['admin_full_name'] = None

                admin_obj = Admin.objects.get(admin_id=item['admin'])
                db_connection = switch_to_database(admin_obj.db_name)

                provider_local = AdServiceProvider.objects.using(db_connection).get(sp_id=item.get('provider_id'))
                global_provider = ServiceProvider.objects.filter(sys_id=provider_local.sys_id).first()
                portal_admin = PortalUser.objects.using(db_connection).filter(pk=1).first()

                item['provider_name'] = global_provider.provider_name if global_provider else None
                item['admin_full_name'] = portal_admin.pu_name if portal_admin else None

                map_entry = service_model_map.get(str(global_provider.sp_id))
                if not map_entry:
                    continue

                txn_model = map_entry['model']
                ref_field = map_entry['ref_field']
                txn_ref_val = item.get('txn_ref')

                txn_record = txn_model.objects.using(db_connection).filter(**{ref_field: txn_ref_val}).first()
                if not txn_record:
                    continue

                creator_id = getattr(txn_record, map_entry.get('creator_field', 'initiated_by'), None)
                if creator_id:
                    retailer = PortalUser.objects.using(db_connection).filter(pk=creator_id).first()
                    retailer_detail = PortalUserInfo.objects.using(db_connection).filter(pu_id=creator_id).first()
                    item['retailer_id'] = retailer.pk if retailer else None
                    item['retailer_name'] = retailer.pu_name if retailer else None
                    item['retailer_code'] = retailer_detail.pud_unique_id if retailer_detail else None

                item['customer_mobile'] = getattr(txn_record, map_entry.get('cust_mobile'), None) if map_entry.get('cust_mobile') else None
                item['customer_full_name'] = getattr(txn_record, map_entry.get('cust_name'), None) if map_entry.get('cust_name') else None
                item['txn_amount'] = getattr(txn_record, map_entry['amount_field'], None)
                item['txn_current_status'] = getattr(txn_record, map_entry['status_field'], None)

            pagination_result = add_serial_numbers(serialized_data, page_num, page_size, 'desc')

            return Response({
                'status': 'success',
                'message': 'Complaint records retrieved successfully.',
                'data': {
                    'total_records': total_count,
                    'total_pages': total_pages,
                    'current_page': page_num,
                    'records': serialized_data
                }
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': f'Error fetching records: {str(exc)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def show_reversal_impact(self, request):
        provider_id = str(request.data.get('provider_id'))
        txn_ref = request.data.get('txn_ref')
        admin_id = request.data.get('admin_id')

        service_model_map = {
            '2': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '4': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '6': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '8': {
                'model': ElectricityBillEntry,
                'ref_field': 'ubill_ref',
                'status_field': 'ubill_status',
                'amount_field': 'bill_amt',
                'table': 'svc_utility_electricity',
                'creator_field': 'initiated_by',
                'cust_mobile': 'consumer_mobile',
                'cust_name': 'consumer_name'
            },
            '9': {
                'model': ElectricityBillEntry,
                'ref_field': 'ubill_ref',
                'status_field': 'ubill_status',
                'amount_field': 'bill_amt',
                'table': 'svc_utility_gas',
                'creator_field': 'initiated_by',
                'cust_mobile': 'consumer_mobile',
                'cust_name': 'consumer_name'
            },
            '10': {
                'model': ElectricityBillEntry,
                'ref_field': 'ubill_ref',
                'status_field': 'ubill_status',
                'amount_field': 'bill_amt',
                'table': 'svc_utility_lic',
                'creator_field': 'initiated_by',
                'cust_mobile': 'consumer_mobile',
                'cust_name': 'consumer_name'
            },
            '11': {
                'model': RechargeTransaction,
                'ref_field': 'recharge_ref',
                'status_field': 'recharge_status',
                'amount_field': 'recharge_amt',
                'table': 'svc_recharge',
                'creator_field': 'initiated_by',
                'cust_mobile': 'mobile_num',
                'cust_name': ''
            },
            '12': {
                'model': BillPaymentRecord,
                'ref_field': 'bbps_ref_id',
                'status_field': 'bbps_txn_status',
                'amount_field': 'paid_amt',
                'table': 'svc_bbps_payment',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bill_mobile',
                'cust_name': ''
            },
            '45': {
                'model': BillPaymentRecord,
                'ref_field': 'bbps_ref_id',
                'status_field': 'bbps_txn_status',
                'amount_field': 'paid_amt',
                'table': 'svc_bbps_payment',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bill_mobile',
                'cust_name': ''
            },
            '41': {
                'model': CashfreePaymentLog,
                'ref_field': 'cf_order_ref',
                'status_field': 'cf_txn_status',
                'amount_field': 'cf_paid_amt',
                'table': 'svc_cashfree_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_mobile',
                'cust_name': ''
            },
            '74': {
                'model': CashfreePaymentLog,
                'ref_field': 'cf_order_ref',
                'status_field': 'cf_txn_status',
                'amount_field': 'cf_paid_amt',
                'table': 'svc_cashfree_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_mobile',
                'cust_name': ''
            },
            '42': {
                'model': PhonePePaymentEntry,
                'ref_field': 'pp_merchant_ref',
                'status_field': 'pp_txn_status',
                'amount_field': 'pp_paid_amt',
                'table': 'svc_phonepe_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_contact',
                'cust_name': ''
            },
            '75': {
                'model': PhonePePaymentEntry,
                'ref_field': 'pp_merchant_ref',
                'status_field': 'pp_txn_status',
                'amount_field': 'pp_paid_amt',
                'table': 'svc_phonepe_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_contact',
                'cust_name': ''
            },
            '43': {
                'model': PaymentGatewayRecord,
                'ref_field': 'pg_client_ref',
                'status_field': 'pg_txn_status',
                'amount_field': 'pg_transfer_amt',
                'table': 'svc_pg_transaction',
                'creator_field': 'initiated_by',
                'cust_mobile': 'client_mobile',
                'cust_name': 'client_name'
            },
            '76': {
                'model': PaymentGatewayRecord,
                'ref_field': 'pg_client_ref',
                'status_field': 'pg_txn_status',
                'amount_field': 'pg_transfer_amt',
                'table': 'svc_pg_transaction',
                'creator_field': 'initiated_by',
                'cust_mobile': 'client_mobile',
                'cust_name': 'client_name'
            },
            '44': {
                'model': PaymentGatewayRecord,
                'ref_field': 'payout_unique_ref',
                'status_field': 'payout_status',
                'amount_field': 'payout_amt',
                'table': 'svc_payout',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_contact',
                'cust_name': 'benef_full_name'
            },
            '77': {
                'model': PaymentGatewayRecord,
                'ref_field': 'payout_unique_ref',
                'status_field': 'payout_status',
                'amount_field': 'payout_amt',
                'table': 'svc_payout',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_contact',
                'cust_name': 'benef_full_name'
            },
            '80': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '81': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '82': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '83': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '84': {
                'model': BulkPayoutRecord,
                'ref_field': 'bulk_txn_id',
                'status_field': 'bulk_status',
                'amount_field': 'bulk_amt',
                'table': 'svc_bulk_payout',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bulk_benef_mobile',
                'cust_name': 'bulk_benef_name'
            },
            '85': {
                'model': AirtelBillEntry,
                'ref_field': 'airtel_txn_ref',
                'status_field': 'airtel_status',
                'amount_field': 'airtel_amt',
                'table': 'svc_airtel_cms',
                'creator_field': 'initiated_by',
                'cust_mobile': 'airtel_mobile',
                'cust_name': ''
            },
            '86': {
                'model': BankItAepsRecord,
                'ref_field': 'bankit_ref',
                'status_field': 'bankit_status',
                'amount_field': 'bankit_amt',
                'table': 'svc_bankit_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bankit_mobile',
                'cust_name': ''
            },
            '92': {
                'model': MicroAtmEntry,
                'ref_field': 'matm_ref',
                'status_field': 'matm_status',
                'amount_field': 'matm_amt',
                'table': 'svc_micro_atm',
                'creator_field': 'initiated_by',
                'cust_mobile': 'matm_mobile',
                'cust_name': ''
            },
            '95': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '97': {
                'model': BankItAepsRecord,
                'ref_field': 'bankit_ref',
                'status_field': 'bankit_status',
                'amount_field': 'bankit_amt',
                'table': 'svc_bankit_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bankit_mobile',
                'cust_name': ''
            },
            '103': {
                'model': MicroAtmEntry,
                'ref_field': 'matm_ref',
                'status_field': 'matm_status',
                'amount_field': 'matm_amt',
                'table': 'svc_micro_atm',
                'creator_field': 'initiated_by',
                'cust_mobile': 'matm_mobile',
                'cust_name': ''
            },
            '106': {
                'model': PpiTransferLog,
                'ref_field': 'ppi_txn_ref',
                'status_field': 'ppi_status',
                'amount_field': 'ppi_amt',
                'table': 'svc_dmt_ppi',
                'creator_field': 'initiated_by',
                'cust_mobile': 'ppi_contact',
                'cust_name': ''
            },
            '109': {
                'model': KhataTransferEntry,
                'ref_field': 'digi_ref_id',
                'status_field': 'digi_txn_status',
                'amount_field': 'digi_txn_amt',
                'table': 'svc_digi_ledger',
                'creator_field': 'initiated_by',
                'cust_mobile': 'digi_customer_mobile',
                'cust_name': 'digi_customer_name'
            },
        }

        try:
            if provider_id not in service_model_map:
                return Response({'status': 'fail', 'message': 'Unsupported service provider.'}, status=status.HTTP_400_BAD_REQUEST)

            admin_obj = Admin.objects.get(admin_id=admin_id)
            db_conn = switch_to_database(admin_obj.db_name)

            mapping = service_model_map[provider_id]
            txn_record = mapping['model'].objects.using(db_conn).get(**{mapping['ref_field']: txn_ref})
            current_status = getattr(txn_record, mapping['status_field'])

            if current_status not in ['SUCCESS', 'IN PROGRESS', 'DISPUTE RAISED']:
                return Response({'status': 'fail', 'message': 'Transaction not eligible for reversal.'}, status=status.HTTP_400_BAD_REQUEST)

            gl_entries = GlTrn.objects.using(db_conn).filter(
                related_table=mapping['table'],
                related_id=txn_record.pk,
                pu_id=1
            ).order_by('gl_entry_id')

            if not gl_entries.exists():
                return Response({'status': 'fail', 'message': 'No ledger entries found.'}, status=status.HTTP_404_NOT_FOUND)

            gl_ids = gl_entries.values_list('gl_entry_id', flat=True)
            wallet_entries = WalletHistory.objects.using(db_conn).filter(action_ref__in=gl_ids).order_by('wl_entry_id')

            impact_list = []
            for w_entry in wallet_entries:
                user = w_entry.pu
                wallet_type = w_entry.affected_wallet
                amount = w_entry.affected_amount or 0
                entry_type = w_entry.entry_direction

                user_wallet = PortalUserBalance.objects.using(db_conn).filter(pu=user).first()
                current_bal = getattr(user_wallet, wallet_type, 0) if user_wallet else 0

                if entry_type == 'CR':
                    new_bal = current_bal - amount
                    rev_direction = 'DR'
                else:
                    new_bal = current_bal + amount
                    rev_direction = 'CR'

                user_code = PortalUserInfo.objects.using(db_conn).get(pu=user).pud_unique_id or 'ADMIN'

                impact_list.append({
                    'user_code': user_code,
                    'wallet_type': wallet_type,
                    'amount': amount,
                    'original_direction': entry_type,
                    'reverse_direction': rev_direction,
                    'current_balance': current_bal,
                    'after_reversal_balance': new_bal
                })

            return Response({
                'status': 'success',
                'message': 'Reversal impact calculated.',
                'data': {'impact': impact_list}
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': f'Error: {str(exc)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def execute_reversal(self, request):
        provider_id = str(request.data.get('provider_id'))
        txn_ref = request.data.get('txn_ref')
        admin_id = request.data.get('admin_id')
        notes = request.data.get('notes', '')
        new_status = request.data.get('new_complaint_status')

        service_model_map = {
            '2': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '4': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '6': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '8': {
                'model': ElectricityBillEntry,
                'ref_field': 'ubill_ref',
                'status_field': 'ubill_status',
                'amount_field': 'bill_amt',
                'table': 'svc_utility_electricity',
                'creator_field': 'initiated_by',
                'cust_mobile': 'consumer_mobile',
                'cust_name': 'consumer_name'
            },
            '9': {
                'model': ElectricityBillEntry,
                'ref_field': 'ubill_ref',
                'status_field': 'ubill_status',
                'amount_field': 'bill_amt',
                'table': 'svc_utility_gas',
                'creator_field': 'initiated_by',
                'cust_mobile': 'consumer_mobile',
                'cust_name': 'consumer_name'
            },
            '10': {
                'model': ElectricityBillEntry,
                'ref_field': 'ubill_ref',
                'status_field': 'ubill_status',
                'amount_field': 'bill_amt',
                'table': 'svc_utility_lic',
                'creator_field': 'initiated_by',
                'cust_mobile': 'consumer_mobile',
                'cust_name': 'consumer_name'
            },
            '11': {
                'model': RechargeTransaction,
                'ref_field': 'recharge_ref',
                'status_field': 'recharge_status',
                'amount_field': 'recharge_amt',
                'table': 'svc_recharge',
                'creator_field': 'initiated_by',
                'cust_mobile': 'mobile_num',
                'cust_name': ''
            },
            '12': {
                'model': BillPaymentRecord,
                'ref_field': 'bbps_ref_id',
                'status_field': 'bbps_txn_status',
                'amount_field': 'paid_amt',
                'table': 'svc_bbps_payment',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bill_mobile',
                'cust_name': ''
            },
            '45': {
                'model': BillPaymentRecord,
                'ref_field': 'bbps_ref_id',
                'status_field': 'bbps_txn_status',
                'amount_field': 'paid_amt',
                'table': 'svc_bbps_payment',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bill_mobile',
                'cust_name': ''
            },
            '41': {
                'model': CashfreePaymentLog,
                'ref_field': 'cf_order_ref',
                'status_field': 'cf_txn_status',
                'amount_field': 'cf_paid_amt',
                'table': 'svc_cashfree_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_mobile',
                'cust_name': ''
            },
            '74': {
                'model': CashfreePaymentLog,
                'ref_field': 'cf_order_ref',
                'status_field': 'cf_txn_status',
                'amount_field': 'cf_paid_amt',
                'table': 'svc_cashfree_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_mobile',
                'cust_name': ''
            },
            '42': {
                'model': PhonePePaymentEntry,
                'ref_field': 'pp_merchant_ref',
                'status_field': 'pp_txn_status',
                'amount_field': 'pp_paid_amt',
                'table': 'svc_phonepe_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_contact',
                'cust_name': ''
            },
            '75': {
                'model': PhonePePaymentEntry,
                'ref_field': 'pp_merchant_ref',
                'status_field': 'pp_txn_status',
                'amount_field': 'pp_paid_amt',
                'table': 'svc_phonepe_txn',
                'creator_field': 'initiated_by',
                'cust_mobile': 'payer_contact',
                'cust_name': ''
            },
            '43': {
                'model': PaymentGatewayRecord,
                'ref_field': 'pg_client_ref',
                'status_field': 'pg_txn_status',
                'amount_field': 'pg_transfer_amt',
                'table': 'svc_pg_transaction',
                'creator_field': 'initiated_by',
                'cust_mobile': 'client_mobile',
                'cust_name': 'client_name'
            },
            '76': {
                'model': PaymentGatewayRecord,
                'ref_field': 'pg_client_ref',
                'status_field': 'pg_txn_status',
                'amount_field': 'pg_transfer_amt',
                'table': 'svc_pg_transaction',
                'creator_field': 'initiated_by',
                'cust_mobile': 'client_mobile',
                'cust_name': 'client_name'
            },
            '44': {
                'model': PaymentGatewayRecord,
                'ref_field': 'payout_unique_ref',
                'status_field': 'payout_status',
                'amount_field': 'payout_amt',
                'table': 'svc_payout',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_contact',
                'cust_name': 'benef_full_name'
            },
            '77': {
                'model': PaymentGatewayRecord,
                'ref_field': 'payout_unique_ref',
                'status_field': 'payout_status',
                'amount_field': 'payout_amt',
                'table': 'svc_payout',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_contact',
                'cust_name': 'benef_full_name'
            },
            '80': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '81': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '82': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '83': {
                'model': AepsCashLog,
                'ref_field': 'aeps_ref_id',
                'status_field': 'aeps_txn_status',
                'amount_field': 'aeps_amt',
                'table': 'svc_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'aeps_mobile',
                'cust_name': ''
            },
            '84': {
                'model': BulkPayoutRecord,
                'ref_field': 'bulk_txn_id',
                'status_field': 'bulk_status',
                'amount_field': 'bulk_amt',
                'table': 'svc_bulk_payout',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bulk_benef_mobile',
                'cust_name': 'bulk_benef_name'
            },
            '85': {
                'model': AirtelBillEntry,
                'ref_field': 'airtel_txn_ref',
                'status_field': 'airtel_status',
                'amount_field': 'airtel_amt',
                'table': 'svc_airtel_cms',
                'creator_field': 'initiated_by',
                'cust_mobile': 'airtel_mobile',
                'cust_name': ''
            },
            '86': {
                'model': BankItAepsRecord,
                'ref_field': 'bankit_ref',
                'status_field': 'bankit_status',
                'amount_field': 'bankit_amt',
                'table': 'svc_bankit_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bankit_mobile',
                'cust_name': ''
            },
            '92': {
                'model': MicroAtmEntry,
                'ref_field': 'matm_ref',
                'status_field': 'matm_status',
                'amount_field': 'matm_amt',
                'table': 'svc_micro_atm',
                'creator_field': 'initiated_by',
                'cust_mobile': 'matm_mobile',
                'cust_name': ''
            },
            '95': {
                'model': FundTransferEntry,
                'ref_field': 'mt_ref_no',
                'status_field': 'mt_status',
                'amount_field': 'mt_amt',
                'table': 'svc_money_transfer',
                'creator_field': 'initiated_by',
                'cust_mobile': 'benef_mobile',
                'cust_name': 'benef_name'
            },
            '97': {
                'model': BankItAepsRecord,
                'ref_field': 'bankit_ref',
                'status_field': 'bankit_status',
                'amount_field': 'bankit_amt',
                'table': 'svc_bankit_aeps',
                'creator_field': 'initiated_by',
                'cust_mobile': 'bankit_mobile',
                'cust_name': ''
            },
            '103': {
                'model': MicroAtmEntry,
                'ref_field': 'matm_ref',
                'status_field': 'matm_status',
                'amount_field': 'matm_amt',
                'table': 'svc_micro_atm',
                'creator_field': 'initiated_by',
                'cust_mobile': 'matm_mobile',
                'cust_name': ''
            },
            '106': {
                'model': PpiTransferLog,
                'ref_field': 'ppi_txn_ref',
                'status_field': 'ppi_status',
                'amount_field': 'ppi_amt',
                'table': 'svc_dmt_ppi',
                'creator_field': 'initiated_by',
                'cust_mobile': 'ppi_contact',
                'cust_name': ''
            },
            '109': {
                'model': KhataTransferEntry,
                'ref_field': 'digi_ref_id',
                'status_field': 'digi_txn_status',
                'amount_field': 'digi_txn_amt',
                'table': 'svc_digi_ledger',
                'creator_field': 'initiated_by',
                'cust_mobile': 'digi_customer_mobile',
                'cust_name': 'digi_customer_name'
            },
        }

        try:
            if new_status == "RESOLVED":
                if provider_id not in service_model_map:
                    return Response({'status': 'fail', 'message': 'Invalid service provider.'}, status=status.HTTP_400_BAD_REQUEST)

                admin_obj = Admin.objects.get(admin_id=admin_id)
                db_conn = switch_to_database(admin_obj.db_name)

                mapping = service_model_map[provider_id]
                txn_record = mapping['model'].objects.using(db_conn).filter(**{mapping['ref_field']: txn_ref}).first()
                if not txn_record:
                    return Response({'status': 'fail', 'message': 'Transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

                current_status = getattr(txn_record, mapping['status_field'])
                if current_status not in ['SUCCESS', 'IN PROGRESS', 'DISPUTE RAISED']:
                    return Response({'status': 'fail', 'message': 'Transaction status not eligible.'}, status=status.HTTP_400_BAD_REQUEST)

                setattr(txn_record, mapping['status_field'], 'REVERSED')
                txn_record.save(using=db_conn)

                gl_entries = GlTrn.objects.using(db_conn).filter(
                    related_table=mapping['table'],
                    related_id=txn_record.pk,
                    pu_id=1
                ).order_by('gl_entry_id')

                if not gl_entries.exists():
                    return Response({'status': 'fail', 'message': 'No ledger entries to reverse.'}, status=status.HTTP_404_NOT_FOUND)

                gl_ids = gl_entries.values_list('gl_entry_id', flat=True)
                wallet_entries = WalletHistory.objects.using(db_conn).filter(action_ref__in=gl_ids)

                for w_entry in wallet_entries:
                    gl_rec = GlTrn.objects.using(db_conn).get(gl_entry_id=w_entry.action_ref)
                    user = w_entry.pu
                    wallet_field = w_entry.affected_wallet
                    amt = w_entry.affected_amount or 0
                    direction = w_entry.entry_direction

                    user_wallet = PortalUserBalance.objects.using(db_conn).filter(pu=user).first()
                    if user_wallet and wallet_field in ['main_wallet', 'commission_wallet', 'pg_wallet', 'cashin_wallet']:
                        curr_bal = getattr(user_wallet, wallet_field, 0)
                        if direction == 'CR':
                            new_bal = curr_bal - amt
                            rev_dir = 'DR'
                            new_label = w_entry.wl_description.replace("CR", "DR")
                        else:
                            new_bal = curr_bal + amt
                            rev_dir = 'CR'
                            new_label = w_entry.wl_description.replace("DR", "CR")
                        new_label = f"REVERSED | {new_label}"

                        setattr(user_wallet, wallet_field, new_bal)
                        user_wallet.save(using=db_conn)

                        if amt > 0:
                            WalletHistory.objects.using(db_conn).create(
                                pu=user,
                                action_type=w_entry.action_type,
                                wl_description=new_label,
                                current_balance=new_bal,
                                affected_wallet=wallet_field,
                                affected_amount=amt,
                                entry_direction=rev_dir,
                                action_ref=w_entry.action_ref,
                                entry_datetime=now()
                            )

                for gl in gl_entries:
                    gl.effective_type = 'DR' if gl.effective_type == 'CR' else 'CR'
                    gl.save(using=db_conn)

                GovernmentChargeLog.objects.using(db_conn).filter(sp__sp_id=provider_id, transaction_id=txn_ref).update(is_deleted=True)
                
            complaint_obj = Servicedispute.objects.get(txn_ref=txn_ref, provider_id=provider_id)
            complaint_obj.complaint_status = new_status
            complaint_obj.admin_notes = notes
            complaint_obj.updated_by = request.user.id
            complaint_obj.updated_at = now()
            complaint_obj.save()

            Servicedispute.objects.create(
                complaint=complaint_obj,
                action="Status Updated",
                user_role="SUPER ADMIN",
                performed_by=request.user.id
            )

            return Response({
                'status': 'success',
                'message': f'Complaint {new_status} successfully.'
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': f'Error during reversal: {str(exc)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)