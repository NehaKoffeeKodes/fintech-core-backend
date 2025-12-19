from ...views import *


class ServiceChargesManagementView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            payload = request.data
            admin_identifier = payload.get('admin_id')
            page_num = int(payload.get('page_number', 1))
            page_sz = int(payload.get('page_size', 10))
            provider_id = payload.get('sp_id')
            svc_id = payload.get('service_id')
            hsn_id = payload.get('hsn_sac_id')
            query_text = payload.get('search')
            from_date = payload.get('start_date')
            to_date = payload.get('end_date', str(datetime.now().date()))

            if not admin_identifier or not str(admin_identifier).isdigit():
                return self._bad_request("Valid admin_id is required and must be numeric.")

            if page_sz <= 0 or page_num <= 0:
                return self._bad_request("page_size and page_number must be positive integers.")

            admin_identifier = int(admin_identifier)
            
            for val, field_name in [(provider_id, 'sp_id'), (svc_id, 'service_id'), (hsn_id, 'hsn_sac_id')]:
                if val is not None and not str(val).isdigit():
                    return self._bad_request(f"{field_name} must be numeric if provided.")

            try:
                portal_user = PortalUser.objects.get(id=admin_identifier)
                admin_record = Admin.objects.get(admin_id=admin_identifier)
            except (PortalUser.DoesNotExist, Admin.DoesNotExist):
                return self._bad_request("Admin or associated user not found.")

            client_db = switch_to_database(admin_record.db_name)

            providers_qs = self._build_provider_queryset(
                from_date, to_date, provider_id, svc_id, hsn_id, query_text
            )

            paginator = Paginator(providers_qs, page_sz)
            try:
                current_page = paginator.page(page_num)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Requested page does not exist.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            transformed_data = self._format_providers_with_charges(
                current_page, admin_record, portal_user, client_db
            )

            response_data = {
                'total_pages': paginator.num_pages,
                'current_page': current_page.number,
                'total_items': paginator.count,
                'results': transformed_data
            }

            return Response({
                'status': 'success',
                'message': 'Service charges retrieved successfully.',
                'data': response_data
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return self._server_error(exc)

    def _build_provider_queryset(self, start_dt, end_dt, sp_id, service_id, hsn_id, search):
        qs = ServiceProvider.objects.filter(is_inactive=False)  

        if start_dt:
            qs = qs.filter(last_updated__date__range=[start_dt, end_dt])

            qs = qs.filter(sp_id=sp_id) 
        if service_id:
            qs = qs.filter(service_id=service_id)
        if hsn_id:
            qs = qs.filter(hsn_code_id=hsn_id)

        if search:
            qs = qs.filter(
                Q(service__title__icontains=search) |
                Q(display_label__icontains=search) |
                Q(admin_code__icontains=search)
            )

        return qs.order_by('-sp_id')

    def _format_providers_with_charges(self, page_items, admin_rec, portal_usr, db_alias):
        results = []

        for sp in page_items:
            charge_list = self._retrieve_applicable_charges(sp, admin_rec)
            is_provided_to_admin = True

            provider_info = {
                'sp_id': sp.sp_id,
                'service_name': sp.service.title if sp.service else "Unknown Service",
                'provider_name': sp.display_label,
                'provider_label': sp.display_label,
                'tds_rate': float(sp.tds_percentage) if sp.tds_percentage else 0.0,
                'tds_type': sp.tds_applicable or "WITHOUT_TDS",
                'hsn_sac_id': sp.hsn_code_id if sp.hsn_code else None,
                'hsn_sac_code': sp.hsn_code.hsnsac_code if sp.hsn_code else None,
                'tax_rate': sp.hsn_code.tax_rate if sp.hsn_code else None,
                'charges': charge_list,
                'is_user_service_provider': is_provided_to_admin,
                'parent_id': None,
                'sub_service_provider': []
            }
            results.append(provider_info)

        return results

    def _retrieve_applicable_charges(self, service_provider, admin):
        charge_list = []

        admin_specific = AdminService.objects.filter(admin=admin, provider=service_provider)
        if admin_specific.exists():
            default_slabs = Charges.objects.filter(
                service_provider=service_provider,
                charge_category='to_us'
            ).order_by('minimum')

            for admin_svc in admin_specific:
                for slab in admin_svc.charges or []:
                    category = slab.get('charge_category') or slab.get('charge_categoy') or 'to_us'
                    charge_list.append({
                        'charge_type': slab.get('charge_type'),
                        'minimum': slab.get('minimum'),
                        'maximum': slab.get('maximum'),
                        'rate_type': slab.get('rate_type'),
                        'rate': slab.get('rate'),
                        'charge_category': category
                    })

            for default in default_slabs:
                charge_list.append({
                    'charge_type': default.charges_type,
                    'minimum': default.minimum,
                    'maximum': default.maximum,
                    'rate_type': default.rate_type,
                    'rate': default.rate,
                    'charge_category': default.charge_category
                })
        else:
            defaults = Charges.objects.filter(service_provider=service_provider).order_by('minimum')
            for item in defaults:
                charge_list.append({
                    'charge_type': item.charges_type,
                    'minimum': item.minimum,
                    'maximum': item.maximum,
                    'rate_type': item.rate_type,
                    'rate': item.rate,
                    'charge_category': item.charge_category
                })

        return charge_list

    def put(self, request):
        try:
            data = request.data
            if 'charges' in data and 'sp_id' in data and 'admin_id' in data:
                return self._handle_charge_update(request)
            elif 'sp_id' in data and 'admin_id' in data:
                return self._handle_service_toggle(request)
            else:
                return self._bad_request("Invalid request payload.")
        except Exception as exc:
            return self._server_error(exc)

    def _toggle_provider_status(self, ad_provider, enable, platform_fee, fee_type, creds, db):
        if enable:
            ad_provider.sa_provided = True
            ad_provider.platform_fee = platform_fee
            ad_provider.platform_fee_type = fee_type
            ad_provider.credentials_json = creds
        else:
            ad_provider.sa_provided = False
        ad_provider.save(using=db)
        return "Service Provider Activated Successfully." if enable else "Service Provider Deactivated Successfully."

    def _ensure_hsn_exists(self, base_hsn, creator):
        try:
            return AdGSTCode.objects.get(hsnsac_code=base_hsn.hsnsac_code)
        except AdGSTCode.DoesNotExist:
            return AdGSTCode.objects.create(
                hsnsac_code=base_hsn.hsnsac_code,
                tax_rate=base_hsn.tax_rate,
                description=base_hsn.description,
                created_by=creator
            )


    @transaction.atomic
    def _handle_service_toggle(self, request):
        sp_id = request.data['sp_id']
        admin_id = request.data['admin_id']

        try:
            portal_usr = PortalUser.objects.get(id=admin_id)
            admin_obj = Admin.objects.get(admin_id=admin_id)
            client_db = switch_to_database(admin_obj.db_name)

            sp_obj = ServiceProvider.objects.get(sp_id=sp_id)

            if hasattr(sp_obj, 'hsn_code') and sp_obj.hsn_code:
                self._ensure_hsn_exists(sp_obj.hsn_code, portal_usr)

            slabs = Charges.objects.filter(
                service_provider_id=sp_id,
                charge_category='to_provide'
            ).order_by('minimum')

            ad_sp = AdServiceProvider.objects.using(client_db).filter(
                system_ref_id=sp_obj.sp_id,
                self_managed=False
            ).first()

            if ad_sp:
                for slab in slabs:
                    if not Adcharges.objects.using(client_db).filter(
                        service_provider=ad_sp,
                        charge_category='to_us',
                        minimum=slab.minimum,
                        maximum=slab.maximum
                    ).exists():
                        Adcharges.objects.using(client_db).create(
                            service_provider=ad_sp,
                            minimum=slab.minimum,
                            maximum=slab.maximum,
                            charges_type=slab.charges_type,
                            rate_type=slab.rate_type,
                            rate=slab.rate,
                            charge_category='to_us',
                            created_by=portal_usr
                        )

                new_status = not ad_sp.sa_provided
                ad_sp.sa_provided = new_status
                ad_sp.platform_fee_value = getattr(sp_obj, 'platform_charge', None) or 0
                ad_sp.platform_fee_mode = getattr(sp_obj, 'charge_type', 'PERCENT')
                ad_sp.api_credentials = getattr(sp_obj, 'api_credentials', {})
                ad_sp.save(using=client_db)

                toggle_msg = "Service Provider Activated Successfully." if new_status else "Service Provider Deactivated Successfully."
            else:
                toggle_msg = "Service Provider not found in admin configuration or is self-managed."


            admin_services = AdminService.objects.filter(
                provider_id=sp_id,
                admin__admin_id=admin_id
            )
            for svc in admin_services:
                field = 'is_inactive' if hasattr(svc, 'is_inactive') else 'is_deactive'
                setattr(svc, field, not getattr(svc, field))
                svc.save()


            all_admin_svcs = AdminService.objects.filter(provider_id=sp_id)
            if all_admin_svcs.exists():
                field = 'is_inactive' if hasattr(all_admin_svcs.first(), 'is_inactive') else 'is_deactive'
                all_inactive = all_admin_svcs.filter(**{field: True}).count() == all_admin_svcs.count()
                setattr(sp_obj, field, all_inactive)
                sp_obj.save()

            return Response({
                'status': 'success',
                'message': toggle_msg
            }, status=status.HTTP_200_OK)

        except ServiceProvider.DoesNotExist:
            return self._bad_request("Service Provider not found.")
        except Exception as exc:
            return self._server_error(exc)
        
    def _handle_charge_update(self, request):
        sp_id = request.data['sp_id']
        admin_id = request.data['admin_id']
        raw_charges = request.data['charges']

        try:
            charges_data = json.loads(raw_charges) if isinstance(raw_charges, str) else raw_charges
            if not isinstance(charges_data, list) or not charges_data:
                return self._bad_request("Charges must be a non-empty list.")

            to_provide_slabs = [c for c in charges_data if c.get('charge_categoy') == 'to_provide']
            if not to_provide_slabs:
                return self._bad_request('No "to_provide" charges provided.')

            admin_obj = Admin.objects.get(admin_id=admin_id)
            client_db = switch_to_database(admin_obj.db_name)
            sp_obj = ServiceProvider.objects.get(sp_id=sp_id)
            admin_user = PortalUser.objects.using(admin_obj.db_name).get(id=1)

            admin_svcs = AdminService.objects.filter(admin=admin_obj, service_provider=sp_obj)
            if not admin_svcs.exists():
                return self._bad_request("No admin service mapping found.")

            for admin_svc in admin_svcs:
                updated = False
                new_rate_val = None
                new_charges = []

                for existing in admin_svc.charges:
                    if existing.get('charge_categoy') == 'to_provide':
                        for incoming in to_provide_slabs:
                            if existing.get('minimum') == incoming.get('minimum') and existing.get('maximum') == incoming.get('maximum'):
                                if existing.get('rate') != incoming.get('rate'):
                                    existing['rate'] = incoming.get('rate')
                                    updated = True
                                    new_rate_val = incoming.get('rate')
                    new_charges.append(existing)

                if updated:
                    admin_svc.charges = new_charges
                    if new_rate_val:
                        admin_svc.rate = new_rate_val
                    admin_svc.save()

            ad_sps = AdServiceProvider.objects.using(client_db).filter(sys_id=sp_obj.sys_id, is_self_config=False)
            if ad_sps.exists():
                ad_charges = Adcharges.objects.using(client_db).filter(
                    service_provider__in=ad_sps, created_by=admin_user
                )
                for ad_charge in ad_charges:
                    for incoming in to_provide_slabs:
                        if ad_charge.minimum == incoming.get('minimum') and ad_charge.maximum == incoming.get('maximum'):
                            if ad_charge.rate != incoming.get('rate'):
                                ad_charge.rate = incoming.get('rate')
                                ad_charge.save()

            return Response({
                'status': 'success',
                'message': 'Charges updated successfully.'
            }, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return self._bad_request("Invalid JSON in charges field.")
        except Exception as exc:
            return self._server_error(exc)

    def _bad_request(self, msg):
        return Response({'status': 'fail', 'message': msg}, status=status.HTTP_400_BAD_REQUEST)

    def _server_error(self, exc):
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(exc)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)