from ...views import*


def get_tag_data_safely(entry, use_tag_mode=False):
    if not use_tag_mode:
        return None
    data = getattr(entry, 'tag_data', None)
    if data is None:
        return None
    if isinstance(data, (dict, list)):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


class ProviderManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'page_number' in request.data:
                return self.list_admins(request)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid request format'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            if 'admin_id' in request.data and 'fees_to_customer' in request.data:
                return self.update_admin_fees(request)
            elif 'admin_id' in request.data:
                return self.toggle_admin_status(request)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid update request'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_admins(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 20))
            admin_id = request.data.get('admin_id')
            service_id = request.data.get('service_id')
            tax_id = request.data.get('tax_id')
            search = request.data.get('search')

            if page < 1 or size < 1:
                return Response({'status': 'fail', 'message': 'Invalid pagination values'},
                                status=status.HTTP_400_BAD_REQUEST)

            query = ServiceProvider.objects.filter(is_removed=False).order_by('-sp_id')

            if admin_id and admin_id.isdigit():
                query = query.filter(sp_id=admin_id)
            if service_id and service_id.isdigit():
                query = query.filter(service_id=service_id)
            if tax_id and tax_id.isdigit():
                query = query.filter(hsn_code_id=tax_id)
            if search:
                query = query.filter(
                    Q(service__title__icontains=search) |     
                    Q(display_label__icontains=search) |
                    Q(admin_code__icontains=search) |
                    Q(hsn_code__gst_code__icontains=search)    
                )

            paginator = Paginator(query, size)
            try:
                current_page = paginator.page(page)
            except EmptyPage:
                return Response({'status': 'fail', 'message': 'Page not found'},
                                status=status.HTTP_404_NOT_FOUND)

            results = []
            for admin in current_page:
                tag_mode = getattr(admin, 'uses_tag_based_fees', False)

                if tag_mode:
                    related = ServiceIdentifier.objects.filter(provider=admin, is_removed=False)
                else:
                    related = ServiceIdentifier.objects.none()
                    
                fees_qs = ChargeRule.objects.filter(service_provider=admin, is_deleted=False).order_by('min_amount')
                fee_type = fees_qs.first().rate_mode if fees_qs.exists() else None  
                serializer = ChargeRuleSerializer(fees_qs, many=True)
                fee_data = serializer.data

                for item in fee_data:
                    item.pop('created_at', None)
                    item.pop('updated_at', None)
                    item.pop('is_disabled', None)
                    item.pop('is_deleted', None)
                    item['is_range_based'] = not (item['min_amount'] in ["0.00", None] and item['max_amount'] in ["0.00", None])

                if tag_mode:
                    active_tags = related.filter(is_disabled=False).count()  
                    total_tags = related.count()
                    fees_exist_status = ("True" if active_tags == total_tags else
                                        "Partially True" if active_tags > 0 else "False")
                else:
                    fees_exist_status = "True" if not admin.is_inactive else "False"

                results.append({
                    'admin_id': admin.sp_id,
                    'service_id': admin.service.service_key,   
                    'service_name': admin.service.title,      
                    'name': admin.admin_code,
                    'display_name': admin.display_label,
                    'tax_code_id': admin.hsn_code.service_key if admin.hsn_code else None, 
                    'tax_code': admin.hsn_code.code if admin.hsn_code else None,
                    'tax_percent': admin.hsn_code.percent if admin.hsn_code else None,
                    'fee_type': fee_type,
                    'is_active': not admin.is_inactive,
                    'fee_list': fee_data,
                    'config_data': admin.api_credentials,
                    'platform_charge': admin.platform_charge,
                    'platform_charge_type': admin.charge_type,
                    'required_fields': admin.required_params,
                    'fees_configured': fees_exist_status,
                    'tag_data': get_tag_data_safely(admin, tag_mode)
                })

            response_data = {
                'total_pages': paginator.num_pages,
                'current_page': current_page.number,
                'total_count': paginator.count,
                'data': results
            }

            return Response({
                'status': 'success',
                'message': 'admins fetched successfully',
                'data': response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def toggle_admin_status(self, request):
        try:
            admin_id = request.data.get('admin_id')
            tag_id = request.data.get('tag_id')

            admin = ServiceProvider.objects.filter(sp_id=admin_id).first()
            if not admin:
                return Response({'status': 'fail', 'message': 'admin not found'},
                                status=status.HTTP_404_NOT_FOUND)

            if tag_id:
                tag = ServiceIdentifier.objects.filter(tag_id=tag_id, provider=admin).first()
                if not tag:
                    return Response({'status': 'fail', 'message': 'Tag not found'},
                                    status=status.HTTP_404_NOT_FOUND)

                has_fees = ChargeRule.objects.filter(service_provider=admin, linked_identifier=tag_id, is_deleted=False).exists()
                if tag.is_disabled and not has_fees:  
                    return Response({'status': 'fail', 'message': 'Cannot activate without fee setup'},
                                    status=status.HTTP_400_BAD_REQUEST)

                tag.is_disabled = not tag.is_disabled
                tag.save()
                msg = 'Tag activated' if not tag.is_disabled else 'Tag deactivated'
                return Response({'status': 'success', 'message': msg}, status=status.HTTP_200_OK)

            if admin.is_inactive:
                if not ChargeRule.objects.filter(service_provider=admin, is_deleted=False).exists():
                    return Response({'status': 'fail', 'message': 'Setup fees before activating'},
                                    status=status.HTTP_400_BAD_REQUEST)
                admin.is_inactive = False
                msg = 'admin activated successfully'
            else:
                admin.is_inactive = True
                msg = 'admin deactivated successfully'

            admin.save()
            return Response({'status': 'success', 'message': msg}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def update_admin_fees(self, request):
        try:
            admin_id = request.data.get('admin_id')
            tag_id = request.data.get('tag_id')
            fee_type = request.data.get('fee_type')  
            tax_id = request.data.get('tax_id')
            display_name = request.data.get('display_name')

            if not admin_id:
                return Response({'status': 'fail', 'message': 'admin_id required'},
                                status=status.HTTP_400_BAD_REQUEST)

            admin = ServiceProvider.objects.get(sp_id=admin_id)

            if not tag_id:
                if not tax_id:
                    return Response({'status': 'fail', 'message': 'tax_id required'},
                                    status=status.HTTP_400_BAD_REQUEST)
                admin.hsn_code = GSTCode.objects.get(id=tax_id)
                if display_name:
                    admin.display_label = display_name
                admin.last_updated = timezone.now()
                admin.updated_by = request.user
                admin.save()

            customer_fees_json = request.data.get('fees_to_customer', '[]')
            provider_fees_json = request.data.get('fees_to_provider', '[]')
            self.sync_fees(customer_fees_json, admin, request, 'OUR_SHARE', fee_type, tag_id)       
            self.sync_fees(provider_fees_json, admin, request, 'admin_SHARE', fee_type, tag_id)    

            return Response({
                'status': 'success',
                'message': 'Fees updated successfully'
            }, status=status.HTTP_200_OK)

        except ServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'admin not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def sync_fees(self, fees_json_str, admin, request, category, rate_mode, tag_id=None):
        try:
            fees_list = json.loads(fees_json_str)
        except json.JSONDecodeError:
            raise ValueError("Invalid fee data format")
        
        existing = ChargeRule.objects.filter(
            service_provider=admin,
            charge_beneficiary=category,
            is_deleted=False
        )
        if tag_id:
            existing = existing.filter(linked_identifier=tag_id)

        existing_map = {
            (f.min_amount or Decimal('0'), f.max_amount or Decimal('0'), f.rate_mode, f.charge_type): f
            for f in existing
        }

        incoming_keys = set()

        for item in fees_list:
            required = ['min_amount', 'max_amount', 'rate_kind', 'rate']
            if not all(k in item for k in required):
                raise ValueError("Missing required fee fields")

            try:
                min_val = Decimal(str(item['min_amount'])) if item['min_amount'] not in ['', None] else Decimal('0')
                max_val = Decimal(str(item['max_amount'])) if item['max_amount'] not in ['', None] else Decimal('0')
                rate_val = Decimal(str(item['rate']))
            except (InvalidOperation, ValueError):
                raise ValueError("Invalid number in fees")

            resolved_rate_mode = item['rate_kind'].upper()  

            key = (min_val, max_val, resolved_rate_mode, 'DEBIT') 
            incoming_keys.add(key)

            existing_fee = existing_map.get(key)
            if existing_fee and existing_fee.rate_value != rate_val:
                existing_fee.rate_value = rate_val
                existing_fee.updated_at = timezone.now()
                existing_fee.updated_by = request.user
                existing_fee.save()
            elif not existing_fee:
                ChargeRule.objects.create(
                    service_provider=admin,
                    charge_type='DEBIT',  
                    rate_mode=resolved_rate_mode,
                    min_amount=min_val if min_val != Decimal('0') else None,
                    max_amount=max_val if max_val != Decimal('0') else None,
                    rate_value=rate_val,
                    linked_identifier=tag_id,
                    charge_beneficiary=category,
                    updated_by=request.user
                )

        for key, fee in existing_map.items():
            if key not in incoming_keys:
                fee.is_deleted = True
                fee.updated_at = timezone.now()
                fee.updated_by = request.user
                fee.save()