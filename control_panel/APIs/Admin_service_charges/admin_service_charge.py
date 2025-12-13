from ...views import *


class ServiceChargesManagementView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            payload = request.data

            # Extract and validate core parameters
            admin_identifier = payload.get('admin_id')
            page_num = int(payload.get('page_number', 1))
            page_sz = int(payload.get('page_size', 10))
            provider_id = payload.get('sp_id')
            svc_id = payload.get('service_id')
            hsn_id = payload.get('hsn_sac_id')
            query_text = payload.get('search')
            from_date = payload.get('start_date')
            to_date = payload.get('end_date', str(datetime.now().date()))

            # Mandatory validations
            if not admin_identifier or not str(admin_identifier).isdigit():
                return self._bad_request("Valid admin_id is required and must be numeric.")

            if page_sz <= 0 or page_num <= 0:
                return self._bad_request("page_size and page_number must be positive integers.")

            admin_identifier = int(admin_identifier)

            # Optional numeric field validation
            for val, field_name in [(provider_id, 'sp_id'), (svc_id, 'service_id'), (hsn_id, 'hsn_sac_id')]:
                if val is not None and not str(val).isdigit():
                    return self._bad_request(f"{field_name} must be numeric if provided.")

            # Fetch admin and user
            try:
                portal_user = PortalUser.objects.get(id=admin_identifier)
                admin_record = Admin.objects.get(admin_id=admin_identifier)
            except (PortalUser.DoesNotExist, Admin.DoesNotExist):
                return self._bad_request("Admin or associated user not found.")

            client_db = switch_to_database(admin_record.db_name)

            # Build filtered queryset
            providers_qs = self._build_provider_queryset(
                from_date, to_date, provider_id, svc_id, hsn_id, query_text
            )

            # Pagination
            paginator = Paginator(providers_qs, page_sz)
            try:
                current_page = paginator.page(page_num)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Requested page does not exist.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            # Transform data with charges and hierarchy
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
        qs = ServiceProvider.objects.filter(is_deactive=False)

        if start_dt:
            qs = qs.filter(created_at__date__range=[start_dt, end_dt])

        if sp_id:
            qs = qs.filter(pk=sp_id)
        if service_id:
            qs = qs.filter(service_id=service_id)
        if hsn_id:
            qs = qs.filter(hsn_sac=hsn_id)

        if search:
            qs = qs.filter(
                Q(service__service_name__icontains=search) |
                Q(sp_name__icontains=search) |
                Q(label__icontains=search) |
                Q(hsn_sac__hsnsac_code__icontains=search)
            )

        return qs.order_by('-pk')

    def _format_providers_with_charges(self, page_items, admin_rec, portal_usr, db_alias):
        results = []
        child_mapping = {}

        for sp in page_items:
            charge_list = self._retrieve_applicable_charges(sp, admin_rec)

            # Determine if this SP is provided to the admin
            ad_sp_entry = AdServiceProvider.objects.using(db_alias).filter(sys_id=sp.sys_id).first()
            is_provided_to_admin = ad_sp_entry.sa_provided if ad_sp_entry else True

            provider_info = {
                'sp_id': sp.sp_id,
                'service_name': sp.service.service_name if sp.service else None,
                'provider_name': f"{sp.sp_name} (CLUB SERVICE)" if sp.club_key else sp.sp_name,
                'provider_label': sp.label,
                'tds_rate': sp.tds_rate,
                'tds_type': sp.tds_type,
                'hsn_sac_id': sp.hsn_sac.hsnsac_id if sp.hsn_sac else None,
                'hsn_sac_code': sp.hsn_sac.hsnsac_code if sp.hsn_sac else None,
                'tax_rate': sp.hsn_sac.tax_rate if sp.hsn_sac else None,
                'charges': charge_list,
                'is_user_service_provider': is_provided_to_admin,
            }

            if sp.parent_id is None:
                provider_info.update({
                    'parent_id': None,
                    'sub_service_provider': []
                })
                results.append(provider_info)
            else:
                if sp.parent_id not in child_mapping:
                    child_mapping[sp.parent_id] = {
                        'parent_id': sp.parent_id,
                        'sub_service_provider': []
                    }
                child_mapping[sp.parent_id]['sub_service_provider'].append(provider_info)

        # Append all sub-provider groups
        for child_group in child_mapping.values():
            results.append(child_group)

        return results

    def _retrieve_applicable_charges(self, service_provider, admin):
        charge_list = []

        if service_provider.sp_id not in [11, 12]:
            admin_specific = AdminService.objects.filter(admin=admin, service_provider=service_provider)
            if admin_specific.exists():
                default_slabs = Charges.objects.filter(
                    service_provider=service_provider,
                    charge_category='to_us'
                ).order_by('minimum')

                for admin_svc in admin_specific:
                    for slab in admin_svc.charges:
                        category = slab.get('charge_category') or slab.get('charge_categoy')
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

            if portal_usr.pu_status in ['PENDING', 'REJECT']:
                return self._bad_request("Account not approved. Contact support.")

            providers = ServiceProvider.objects.filter(Q(sp_id=sp_id) | Q(parent_id=sp_id))
            main_provider = providers.first()

            if not main_provider.is_charge_identifier:
                # Standard provider flow
                for sp in providers:
                    service = SaService.objects.filter(service_id=sp.service.service_id).first()
                    self._ensure_hsn_exists(sp.hsn_sac, portal_usr)

                    slabs = Charges.objects.filter(
                        service_provider_id=sp.sp_id,
                        charge_category='to_provide'
                    ).order_by('minimum')

                    ad_sp = AdServiceProvider.objects.using(client_db).filter(
                        sys_id=sp.sys_id, is_self_config=False
                    ).first()
                    if not ad_sp:
                        continue

                    # Sync charges
                    for slab in slabs:
                        if not Adcharges.objects.using(client_db).filter(
                            service_provider=ad_sp, charge_category='to_us',
                            minimum=slab.minimum, maximum=slab.maximum
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

                    # Toggle status
                    toggle_msg = self._toggle_provider_status(
                        ad_sp, not ad_sp.sa_provided,
                        sp.platform_fee, sp.platform_fee_type,
                        sp.credentials_json, client_db
                    )

            else:
                # Identifier-based flow
                identifiers = SaServiceIdentifier.objects.filter(sp__sp_id=sp_id)
                for identifier in identifiers:
                    self._ensure_hsn_exists(identifier.sp.hsn_sac, portal_usr)

                    slabs = Charges.objects.filter(
                        service_provider_id=identifier.sp.sp_id,
                        identifier_id=identifier.si_id,
                        charge_category='to_provide'
                    ).order_by('minimum')

                    ad_sp = AdServiceProvider.objects.using(client_db).filter(
                        sys_id=identifier.sp.sys_id, is_self_config=False
                    ).first()
                    if not ad_sp:
                        continue

                    for slab in slabs:
                        if not Adcharges.objects.using(client_db).filter(
                            service_provider=ad_sp, charge_identifier=identifier.si_id,
                            charge_category='to_us', minimum=slab.minimum
                        ).exists():
                            Adcharges.objects.using(client_db).create(
                                service_provider=ad_sp,
                                charge_identifier=identifier.si_id,
                                minimum=slab.minimum,
                                maximum=slab.maximum,
                                charges_type=slab.charges_type,
                                rate_type=slab.rate_type,
                                rate=slab.rate,
                                charge_category='to_us',
                                created_by=portal_usr
                            )

                    toggle_msg = self._toggle_provider_status(
                        ad_sp, not ad_sp.sa_provided,
                        identifier.sp.platform_fee, identifier.sp.platform_fee_type,
                        identifier.sp.credentials_json, client_db
                    )

            # Update collective deactivation status
            admin_services = AdminService.objects.filter(service_provider_id=sp_id, admin__admin_id=admin_id)
            for svc in admin_services:
                svc.is_deactive = not svc.is_deactive
                svc.save()

            all_admin_svcs = AdminService.objects.filter(service_provider_id=sp_id)
            all_deactivated = all_admin_svcs.filter(is_deactive=True).count() == all_admin_svcs.count()
            sp_main = ServiceProvider.objects.filter(sp_id=sp_id).first()
            if sp_main:
                sp_main.is_deactive = all_deactivated
                sp_main.save()

            return Response({'status': 'success', 'message': toggle_msg}, status=status.HTTP_200_OK)

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

            # Update AdminService charges
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

            # Update Adcharges
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