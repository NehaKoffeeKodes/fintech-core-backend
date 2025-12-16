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
                return self.list_vendors(request)
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
            if 'vendor_id' in request.data and 'fees_to_customer' in request.data:
                return self.update_vendor_fees(request)
            elif 'vendor_id' in request.data:
                return self.toggle_vendor_status(request)
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

    def list_vendors(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 20))
            vendor_id = request.data.get('vendor_id')
            service_id = request.data.get('service_id')
            tax_id = request.data.get('tax_id')
            search = request.data.get('search')

            if page < 1 or size < 1:
                return Response({'status': 'fail', 'message': 'Invalid pagination values'}, 
                                status=status.HTTP_400_BAD_REQUEST)

            query = ServiceProvider.objects.filter(parent__isnull=True, is_removed=False).order_by('-id')

            if vendor_id and vendor_id.isdigit():
                query = query.filter(id=vendor_id)
            if service_id and service_id.isdigit():
                query = query.filter(service_id=service_id)
            if tax_id and tax_id.isdigit():
                query = query.filter(tax_code_id=tax_id)
            if search:
                query = query.filter(
                    Q(service__name__icontains=search) |
                    Q(name__icontains=search) |
                    Q(display_name__icontains=search) |
                    Q(tax_code__code__icontains=search)
                )

            paginator = Paginator(query, size)
            try:
                current_page = paginator.page(page)
            except EmptyPage:
                return Response({'status': 'fail', 'message': 'Page not found'}, 
                                status=status.HTTP_404_NOT_FOUND)

            results = []
            for vendor in current_page:
                tag_mode = vendor.uses_tag_based_fees

                if tag_mode:
                    related = ServiceIdentifier.objects.filter(provider__id=vendor.id, is_removed=False)
                else:
                    related = ServiceProvider.objects.filter(parent=vendor)

                fees_qs = ChargeRule.objects.filter(vendor=vendor).order_by('min_amount')
                fee_type = fees_qs.first().fee_type if fees_qs.exists() else None
                serializer = ChargeRuleSerializer(fees_qs, many=True)
                fee_data = serializer.data

                for item in fee_data:
                    item.pop('created_at', None)
                    item.pop('modified_at', None)
                    item.pop('is_inactive', None)
                    item.pop('is_removed', None)
                    item['is_range_based'] = not (item['min_amount'] == "0.00" and item['max_amount'] == "0.00")

                if tag_mode:
                    active_tags = related.filter(is_inactive=False).count()
                    total_tags = related.count()
                    fees_exist_status = ("True" if active_tags == total_tags else 
                                        "Partially True" if active_tags > 0 else "False")
                else:
                    fees_exist_status = "True" if not vendor.is_inactive else "False"

                results.append({
                    'vendor_id': vendor.id,
                    'service_id': vendor.service.id,
                    'service_name': vendor.service.name,
                    'name': vendor.name,
                    'display_name': vendor.display_name,
                    'tax_code_id': vendor.tax_code.id if vendor.tax_code else None,
                    'tax_code': vendor.tax_code.code if vendor.tax_code else None,
                    'tax_percent': vendor.tax_code.percent if vendor.tax_code else None,
                    'fee_type': fee_type,
                    'is_active': not vendor.is_inactive,
                    'fee_list': fee_data,
                    'config_data': vendor.config_json,
                    'platform_charge': vendor.platform_charge,
                    'platform_charge_type': vendor.platform_charge_type,
                    'required_fields': vendor.required_fields,
                    'fees_configured': fees_exist_status,
                    'tag_data': get_tag_data_safely(vendor, tag_mode)
                })

            response_data = {
                'total_pages': paginator.num_pages,
                'current_page': current_page.number,
                'total_count': paginator.count,
                'data': results
            }

            return Response({
                'status': 'success',
                'message': 'Vendors fetched successfully',
                'data': response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def toggle_vendor_status(self, request):
        try:
            vendor_id = request.data.get('vendor_id')
            tag_id = request.data.get('tag_id')

            vendor = ServiceProvider.objects.filter(id=vendor_id).first()
            if not vendor:
                return Response({'status': 'fail', 'message': 'Vendor not found'}, 
                                status=status.HTTP_404_NOT_FOUND)

            if tag_id:
                tag = ServiceIdentifier.objects.filter(tag_id=tag_id, provider=vendor).first()
                if not tag:
                    return Response({'status': 'fail', 'message': 'Tag not found'}, 
                                    status=status.HTTP_404_NOT_FOUND)

                has_fees = ChargeRule.objects.filter(vendor=vendor, tag_id=tag_id).exists()
                if tag.is_inactive and not has_fees:
                    return Response({'status': 'fail', 'message': 'Cannot activate without fee setup'}, 
                                    status=status.HTTP_400_BAD_REQUEST)

                tag.is_inactive = not tag.is_inactive
                tag.save()
                msg = 'Tag activated' if not tag.is_inactive else 'Tag deactivated'
                return Response({'status': 'success', 'message': msg}, status=status.HTTP_200_OK)

            if vendor.is_inactive:
                if not ChargeRule.objects.filter(vendor=vendor).exists():
                    return Response({'status': 'fail', 'message': 'Setup fees before activating'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                vendor.is_inactive = False
                msg = 'Vendor activated successfully'
            else:
                vendor.is_inactive = True
                msg = 'Vendor deactivated successfully'

            vendor.save()
            return Response({'status': 'success', 'message': msg}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def update_vendor_fees(self, request):
        try:
            vendor_id = request.data.get('vendor_id')
            tag_id = request.data.get('tag_id')
            fee_type = request.data.get('fee_type')
            tax_id = request.data.get('tax_id')
            display_name = request.data.get('display_name')

            if not vendor_id:
                return Response({'status': 'fail', 'message': 'vendor_id required'}, 
                                status=status.HTTP_400_BAD_REQUEST)

            vendor = ServiceProvider.objects.get(id=vendor_id)

            if not tag_id:
                if not tax_id:
                    return Response({'status': 'fail', 'message': 'tax_id required'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                vendor.tax_code = GSTCode.objects.get(id=tax_id)
                vendor.display_name = display_name
                vendor.modified_at = timezone.now()
                vendor.modified_by = request.user
                vendor.save()

            customer_fees_json = request.data.get('fees_to_customer', '[]')
            provider_fees_json = request.data.get('fees_to_provider', '[]')

            self.sync_fees(customer_fees_json, vendor, request, 'customer', fee_type, tag_id)
            self.sync_fees(provider_fees_json, vendor, request, 'provider', fee_type, tag_id)

            return Response({
                'status': 'success',
                'message': 'Fees updated successfully'
            }, status=status.HTTP_200_OK)

        except ServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Vendor not found'}, 
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def sync_fees(self, fees_json_str, vendor, request, category, fee_type, tag_id=None):
        try:
            fees_list = json.loads(fees_json_str)
        except json.JSONDecodeError:
            raise ValueError("Invalid fee data format")

        existing = ChargeRule.objects.filter(
            vendor=vendor,
            category=category,
            is_removed=False
        )
        if tag_id:
            existing = existing.filter(tag_id=tag_id)

        existing_map = {
            (f.min_amount, f.max_amount, f.rate_kind, f.fee_type): f
            for f in existing
        }

        incoming_keys = set()

        for item in fees_list:
            required = ['min_amount', 'max_amount', 'rate_kind', 'rate']
            if not all(k in item for k in required):
                raise ValueError("Missing required fee fields")

            try:
                min_val = Decimal(item['min_amount'])
                max_val = Decimal(item['max_amount'])
                rate_val = Decimal(item['rate'])
            except (InvalidOperation, ValueError):
                raise ValueError("Invalid number in fees")

            key = (min_val, max_val, item['rate_kind'], fee_type)
            incoming_keys.add(key)

            existing_fee = existing_map.get(key)
            if existing_fee and existing_fee.rate != rate_val:
                existing_fee.rate = rate_val
                existing_fee.modified_at = timezone.now()
                existing_fee.modified_by = request.user
                existing_fee.save()
            elif not existing_fee:
                data = {
                    'min_amount': min_val,
                    'max_amount': max_val,
                    'rate': rate_val,
                    'rate_kind': item['rate_kind'],
                    'fee_type': fee_type,
                    'category': category,
                    'vendor': vendor,
                }
                if tag_id:
                    data['tag_id'] = tag_id
                ChargeRule.objects.create(**data)

        for key, fee in existing_map.items():
            if key not in incoming_keys:
                fee.is_removed = True
                fee.modified_at = timezone.now()
                fee.modified_by = request.user
                fee.save()