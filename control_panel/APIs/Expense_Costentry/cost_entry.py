from ...views import * 

class CostManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'page_number' in request.data:
                return self.list_costs(request)
            elif 'entry_date' in request.data:
                return self.add_new_cost(request)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid request format'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_new_cost(self, request):
        try:
            with transaction.atomic():
                data = request.data.copy()
                uploaded_files = []

                for key in data.keys():
                    if key.startswith('expense_attachment'):
                        file_obj = data[key]
                        if file_obj.size > 10 * 1024 * 1024: 
                            raise ValidationError("Each file must be under 10MB")

                        save_path = os.path.join('costs/documents', file_obj.name)
                        full_path = os.path.join(settings.MEDIA_ROOT, save_path)
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)

                        with open(full_path, 'wb+') as f:
                            for chunk in file_obj.chunks():
                                f.write(chunk)

                        uploaded_files.append(save_path)

                if uploaded_files:
                    data['documents'] = uploaded_files

                serializer = CostEntrySerializer(data=data, context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    cost_obj = serializer.save(created_by=request.user)

                    AdminActivityLog.objects.create(
                        table_id=cost_obj.entry_id,
                        table_name='cost_entry',
                        ua_action='create',
                        ua_description='Added new cost entry',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Cost entry added successfully'
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as ve:
            return Response({
                'status': 'fail',
                'message': str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_costs(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            entry_id = request.data.get('entry_id')
            search = request.data.get('search')

            qs = CostEntry.objects.filter(is_removed=False).order_by('-entry_id')

            if entry_id:
                qs = qs.filter(entry_id=entry_id)
            if search:
                qs = qs.filter(
                    Q(amount__icontains=search) |
                    Q(payment_method__icontains=search) |
                    Q(tax_status__icontains=search) |
                    Q(notes__icontains=search) |
                    Q(vendor_name__icontains=search)
                )

            if not qs.exists():
                return Response({
                    'status': 'success',
                    'message': 'No records found',
                    'data': {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                }, status=status.HTTP_200_OK)

            paginator = Paginator(qs, size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = CostEntrySerializer(page_obj, many=True, context={'request': request})

            return Response({
                'status': 'success',
                'message': 'Cost entries retrieved',
                'data': {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        entry_id = request.data.get('entry_id')
        if not entry_id:
            return Response({
                'status': 'fail',
                'message': 'entry_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                cost_obj = CostEntry.objects.get(entry_id=entry_id, is_removed=False)

                data = request.data.copy()
                new_files = []

                for key in data.keys():
                    if key.startswith('expense_attachment'):
                        file = data[key]
                        if file.size > 10 * 1024 * 1024:
                            raise ValidationError("File too large (max 10MB)")

                        save_path = os.path.join('costs/documents', file.name)
                        full_path = os.path.join(settings.MEDIA_ROOT, save_path)
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)

                        with open(full_path, 'wb+') as f:
                            for chunk in file.chunks():
                                f.write(chunk)
                        new_files.append(save_path)

                if new_files:
                    current_docs = cost_obj.documents or []
                    data['documents'] = current_docs + new_files

                serializer = CostEntrySerializer(cost_obj, data=data, partial=True, context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    serializer.save(updated_at=datetime.now(), updated_by=request.user)

                    AdminActivityLog.objects.create(
                        table_id=cost_obj.entry_id,
                        table_name='cost_entry',
                        ua_action='update',
                        ua_description=f'Updated cost entry {cost_obj.entry_id}',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Cost entry updated successfully'
                    }, status=status.HTTP_200_OK)

        except CostEntry.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Entry not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({
                'status': 'fail',
                'message': str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        entry_id = request.data.get('entry_id')
        if not entry_id:
            return Response({
                'status': 'fail',
                'message': 'entry_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                cost_obj = CostEntry.objects.get(entry_id=entry_id, is_removed=False)
                cost_obj.is_removed = True
                cost_obj.save()

                AdminActivityLog.objects.create(
                    table_id=cost_obj.entry_id,
                    table_name='cost_entry',
                    ua_action='delete',
                    ua_description=f'Deleted cost entry {cost_obj.entry_id}',
                    created_by=request.user,
                    request_data=request.data
                )

                return Response({
                    'status': 'success',
                    'message': 'Cost entry deleted successfully'
                }, status=status.HTTP_200_OK)

        except CostEntry.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Entry not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)