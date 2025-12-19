from ...views import*

class ProductManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'page_num' in request.data and 'page_size' in request.data:
                return self.retrieve_items(request)
            elif 'manufacturer' in request.data and 'item_model' in request.data:
                return self.add_new_item(request)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid request payload.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_new_item(self, request):
        try:
            with transaction.atomic():
                data_copy = request.data.copy()
                uploaded_paths = []

                for field_name, file_obj in request.FILES.items():
                    if field_name.startswith('item_image'):
                        if file_obj.size > 10 * 1024 * 1024: 
                            raise ValidationError("Each image must be under 10MB.")

                        safe_filename = os.path.basename(file_obj.name)
                        rel_path = os.path.join('inventory_images', safe_filename)
                        full_path = os.path.join(settings.MEDIA_ROOT, rel_path)

                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        with open(full_path, 'wb') as f:
                            for chunk in file_obj.chunks():
                                f.write(chunk)

                        uploaded_paths.append(rel_path)

                if uploaded_paths:
                    data_copy['images'] = uploaded_paths

                serializer = ProductItemSerializer(data=data_copy, context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    serializer.save(added_by=request.user)
                    return Response({
                        'status': 'success',
                        'message': 'Item added to inventory successfully.'
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as ve:
            return Response({'status': 'fail', 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve_items(self, request):
        try:
            item_id = request.data.get('item_id')
            page_size_raw = request.data.get('page_size', 10)
            page_num_raw = request.data.get('page_num', 1)
            start = request.data.get('from_date')
            end = request.data.get('to_date')
            search = request.data.get('search')
            cat_filter = request.data.get('category')
            inactive_filter = request.data.get('inactive')
            sort_order = request.data.get('sort', 'desc')

            try:
                page_size = int(page_size_raw)
                page_num = int(page_num_raw)
            except ValueError:
                return Response({'status': 'fail', 'message': 'Invalid pagination values.'}, status=status.HTTP_400_BAD_REQUEST)

            if page_num < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_num and page_size must be >= 1.'}, status=status.HTTP_400_BAD_REQUEST)

            qs = ProductItem.objects.filter(removed=False)

            if item_id:
                qs = qs.filter(pk=item_id)

            if inactive_filter is not None:
                qs = qs.filter(inactive=(str(inactive_filter).lower() == 'true'))

            if start and end:
                try:
                    start_dt = datetime.strptime(start, '%Y-%m-%d').date()
                    end_dt = datetime.strptime(end, '%Y-%m-%d').date()
                    qs = qs.filter(purchase_date__range=[start_dt, end_dt + timedelta(days=1)])
                except ValueError:
                    return Response({'status': 'fail', 'message': 'Invalid date format.'}, status=status.HTTP_400_BAD_REQUEST)

            if search:
                qs = qs.filter(
                    Q(manufacturer__icontains=search) |
                    Q(item_model__icontains=search) |
                    Q(details__icontains=search)
                )

            if cat_filter and str(cat_filter) != "0":
                qs = qs.filter(category_id=cat_filter)

            qs = qs.order_by('pk' if sort_order == 'asc' else '-pk')

            paginator = Paginator(qs, page_size)
            try:
                current_page = paginator.page(page_num)
            except EmptyPage:
                return Response({'status': 'fail', 'message': 'Page does not exist.'}, status=status.HTTP_404_NOT_FOUND)

            if not qs.exists():
                empty_data = {'total_pages': 0, 'current_page': 0, 'total_items': 0, 'results': []}
                return Response({'status': 'success', 'message': 'No items found.', 'data': empty_data}, status=status.HTTP_200_OK)

            serialized = ProductItemSerializer(current_page.object_list, many=True, context={'request': request}).data
            add_serial_numbers(page_num, page_size, serialized, sort_order)

            response_payload = {
                'total_pages': paginator.num_pages,
                'current_page': current_page.number,
                'total_items': paginator.count,
                'results': serialized
            }

            return Response({
                'status': 'success',
                'message': 'Inventory items retrieved.',
                'data': response_payload
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def put(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'status': 'fail', 'message': 'item_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                item = ProductItem.objects.get(item_id=item_id, removed=False)
                data_copy = request.data.copy()
                new_images = []

                for key, file in request.FILES.items():
                    if key.startswith('item_image'):
                        if file.size > 10 * 1024 * 1024:
                            raise ValidationError("Image size exceeds 10MB limit.")

                        filename = os.path.basename(file.name)
                        rel_path = os.path.join('inventory_images', filename)
                        full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)

                        with open(full_path, 'wb') as f:
                            for chunk in file.chunks():
                                f.write(chunk)
                        new_images.append(rel_path)

                if new_images:
                    data_copy['images'] = new_images

                serializer = ProductItemSerializer(item, data=data_copy, partial=True, context={'request': request})
                if serializer.is_valid():
                    serializer.save(modified_on=datetime.now(), modified_by=request.user)
                    return Response({
                        'status': 'success',
                        'message': 'Item updated successfully.'
                    }, status=status.HTTP_200_OK)

                return Response({'status': 'fail', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except ProductItem.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'status': 'fail', 'message': 'item_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                item = ProductItem.objects.get(item_id=item_id, removed=False)
                item.removed = True
                item.save()
                return Response({
                    'status': 'success',
                    'message': 'Item removed from inventory.'
                }, status=status.HTTP_200_OK)

        except ProductItem.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)