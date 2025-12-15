from ...views import*

class FeeManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'page_num' in request.data and 'page_size' in request.data:
                return self.list_fee_configs(request)
            elif 'charges_type' in request.data:
                return self.add_new_fee(request)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'Request payload is not valid.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_new_fee(self, request):
        save_api_log(request, "OwnAPI", request.data, {"status": "in_progress"}, None,
                            service_type="SuperAdmin Fee Creation", client_override="tcpl_db")
        try:
            serializer = ChargesRuleSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    fee_instance = serializer.save()

                    AdminActivityLog.objects.create(
                        table_id=fee_instance.pk,
                        table_name='charges',
                        ua_action='create',
                        ua_description='New fee configuration created successfully',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data
                    )

                save_api_log(request, "OwnAPI", request.data, {"status": "success", "data": serializer.data},
                                    None, service_type="SuperAdmin Fee Creation", client_override="tcpl_db")

                return Response({
                    'status': 'success',
                    'message': 'Fee configuration added successfully.'
                }, status=status.HTTP_201_CREATED)
            else:
                save_api_log(request, "OwnAPI", request.data, {"status": "validation_failed", "errors": serializer.errors},
                                    None, service_type="SuperAdmin Fee Creation", client_override="tcpl_db")
                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            save_api_log(request, "OwnAPI", request.data, {"status": "failed", "error": str(exc)},
                                None, service_type="SuperAdmin Fee Creation", client_override="tcpl_db")
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_fee_configs(self, request):
        try:
            page_size = int(request.data.get('page_size', 10))
            page_num = int(request.data.get('page_num', 1))
            provider_id = request.data.get('sp_id')
            search_term = request.data.get('search')

            base_qs = Charges.objects.filter(is_deleted=False).order_by('-pk')

            if provider_id:
                base_qs = base_qs.filter(service_provider=provider_id)
            if search_term:
                base_qs = base_qs.filter(
                    Q(charges_type__icontains=search_term) |
                    Q(rate_type__icontains=search_term)
                    # Add more Q objects if you have additional searchable fields
                )

            paginator = Paginator(base_qs, page_size)

            if not base_qs.exists():
                empty_response = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                return Response({
                    'status': 'success',
                    'message': 'No fee records available.',
                    'data': empty_response
                }, status=status.HTTP_200_OK)

            try:
                page_object = paginator.page(page_num)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Requested page does not exist.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            serialized = ChargesRuleSerializer(page_object.object_list, many=True).data

            pagination_info = {
                'total_pages': paginator.num_pages,
                'current_page': page_object.number,
                'total_items': paginator.count,
                'results': serialized
            }

            return Response({
                'status': 'success',
                'message': 'Fee configurations retrieved successfully.',
                'data': pagination_info
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        fee_id = request.data.get('charges_id')
        save_api_log(request, "OwnAPI", request.data, {"status": "in_progress"}, None,
                            service_type="SuperAdmin Fee Update", client_override="tcpl_db")

        if not fee_id:
            return Response({
                'status': 'fail',
                'message': 'charges_id field is mandatory.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            fee_record = Charges.objects.get(pk=fee_id, is_deleted=False)
            serializer = ChargesRuleSerializer(fee_record, data=request.data, partial=True,
                                             context={'request': request})

            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save(updated_by=request.user, updated_at=datetime.now())

                    AdminActivityLog.objects.create(
                        table_id=fee_record.pk,
                        table_name='charges',
                        ua_action='update',
                        ua_description='Fee configuration updated successfully',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data
                    )

                save_api_log(request, "OwnAPI", request.data, {"status": "success", "data": serializer.data},
                                    None, service_type="SuperAdmin Fee Update", client_override="tcpl_db")

                return Response({
                    'status': 'success',
                    'message': 'Fee configuration updated successfully.'
                }, status=status.HTTP_200_OK)
            else:
                save_api_log(request, "OwnAPI", request.data, {"status": "validation_failed", "errors": serializer.errors},
                                    None, service_type="SuperAdmin Fee Update", client_override="tcpl_db")
                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Charges.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Fee record not found or already deleted.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            save_api_log(request, "OwnAPI", request.data, {"status": "failed", "error": str(exc)},
                                None, service_type="SuperAdmin Fee Update", client_override="tcpl_db")
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        fee_id = request.data.get('charges_id')
        save_api_log(request, "OwnAPI", request.data, {"status": "in_progress"}, None,
                            service_type="SuperAdmin Fee Delete", client_override="tcpl_db")

        if not fee_id:
            return Response({
                'status': 'fail',
                'message': 'charges_id is required for deletion.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            fee_record = Charges.objects.get(pk=fee_id, is_deleted=False)
            fee_record.is_deleted = True
            fee_record.save()

            AdminActivityLog.objects.create(
                table_id=fee_record.pk,
                table_name='charges',
                ua_action='delete',
                ua_description='Fee configuration soft-deleted successfully',
                created_by=request.user,
                request_data=request.data
            )

            save_api_log(request, "OwnAPI", request.data, {"status": "success"},
                                None, service_type="SuperAdmin Fee Delete", client_override="tcpl_db")

            return Response({
                'status': 'success',
                'message': 'Fee configuration removed successfully.'
            }, status=status.HTTP_200_OK)

        except Charges.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Fee record not found or already removed.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            save_api_log(request, "OwnAPI", request.data, {"status": "failed", "error": str(exc)},
                                None, service_type="SuperAdmin Fee Delete", client_override="tcpl_db")
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)