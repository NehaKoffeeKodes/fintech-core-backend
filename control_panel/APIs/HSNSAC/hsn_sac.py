from datetime import timezone
from web_portal.models import AdminActivityLog
from ...views import*


class GSTCodeManagerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get('page_no') or request.data.get('limit'):
            return self.get_gst_codes(request)
        elif 'gst_code' in request.data and 'cgst' in request.data:
            return self.add_gst_entry(request)
        
        return Response({
            'ok': False,
            'msg': 'Invalid request format.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def add_gst_entry(self, request):
        try:
            with transaction.atomic():
                serializer = GSTCodeManagerSerializer(
                    data=request.data,
                    context={'request': request}
                )

                if not serializer.is_valid():
                    return Response({
                        'ok': False,
                        'msg': 'Validation failed.',
                        'errors': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)

                gst_entry = serializer.save(added_by=request.user)
                print('gst_entry:',gst_entry)
                AdminActivityLog.objects.create(
                    user=request.user,
                    action='GST_CODE_ADDED',
                    description=f'Added GST code: {gst_entry.gst_code}',
                    request_data=request.data
                )

                return Response({
                    'ok': True,
                    'msg': 'GST code added successfully!',
                    'id': gst_entry.gst_id
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'ok': False,
                'msg': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_gst_codes(self, request):
        try:
            page = int(request.data.get('page_no', 1))
            limit = int(request.data.get('limit', 20))
            code_id = request.data.get('gst_id')
            search = request.data.get('search', '').strip()
            sort_order = request.data.get('sort', 'desc')

            if page < 1 or limit < 1:
                return Response({'ok': False, 'msg': 'Invalid pagination values.'}, status=status.HTTP_400_BAD_REQUEST)

            qs = GSTCode.objects.filter(is_removed=False)

            if code_id:
                if not is_positive_integer(code_id):
                    return Response({'ok': False, 'msg': 'Invalid gst_id.'}, status=status.HTTP_400_BAD_REQUEST)
                qs = qs.filter(gst_id=code_id)

            if search:
                qs = qs.filter(
                    Q(gst_code__icontains=search) |
                    Q(cgst__icontains=search) |
                    Q(sgst__icontains=search)
                )

            qs = qs.order_by('-gst_id' if sort_order == 'desc' else 'gst_id')

            if code_id and not qs.exists():
                return Response({'ok': False, 'msg': 'GST code not found.'}, status=status.HTTP_404_NOT_FOUND)

            paginator = Paginator(qs, limit)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            serializer = GSTCodeManagerSerializer(
                page_obj.object_list,
                many=True,
                context={'request': request, 'exclude_fields': ['added_by', 'added_on', 'updated_at', 'updated_by']}
            )

            add_serial_numbers(serializer.data, page, limit, sort_order)

            result = {
                'total': paginator.num_pages,
                'current': page_obj.number,
                'total': paginator.count,
                'data': serializer.data
            }

            return Response({
                'ok': True,
                'msg': 'GST codes retrieved.',
                'result': result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'ok': False, 'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            gst_id = request.data.get('gst_id')
            if not gst_id or not is_positive_integer(gst_id):
                return Response({'ok': False, 'msg': 'gst_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                try:
                    entry = GSTCode.objects.get(gst_id=gst_id, is_removed=False)
                except GSTCode.DoesNotExist:
                    return Response({'ok': False, 'msg': 'GST code not found.'}, status=status.HTTP_404_NOT_FOUND)

                toggle_status = request.data.get('is_hidden') in [True, 'true', 'True', '1']

                if toggle_status is not None:
                    entry.is_hidden = toggle_status
                    entry.updated_at = timezone.now()
                    entry.updated_by = request.user
                    entry.save()

                    msg = "GST code hidden." if toggle_status else "GST code made visible."
                else:
                    serializer = GSTCodeManagerSerializer(
                        entry, data=request.data, partial=True, context={'request': request}
                    )
                    if not serializer.is_valid():
                        return Response({'ok': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                    serializer.save(updated_at=timezone.now(), updated_by=request.user)
                    msg = "GST code updated."

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='GST_CODE_UPDATED',
                    description=msg,
                    request_data=request.data
                )

                return Response({'ok': True, 'msg': msg}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'ok': False, 'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            gst_id = request.data.get('gst_id')
            if not gst_id or not is_positive_integer(gst_id):
                return Response({'ok': False, 'msg': 'gst_id required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                entry = GSTCode.objects.filter(gst_id=gst_id, is_removed=False).first()
                if not entry:
                    return Response({'ok': False, 'msg': 'GST code not found.'}, status=status.HTTP_404_NOT_FOUND)

                entry.is_removed = True
                entry.save()

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='GST_CODE_DELETED',
                    description=f'Soft deleted GST code: {entry.gst_code}',
                    request_data=request.data
                )

                return Response({'ok': True, 'msg': 'GST code removed.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'ok': False, 'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)