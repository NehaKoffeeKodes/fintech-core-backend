from ...views import *  

class ChargeCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle create or list requests"""
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.list_categories(request)
            elif 'category_name' in request.data:
                return self.add_category(request)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid request data'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_category(self, request):
        """Create a new charge category"""
        try:
            with transaction.atomic():
                serializer = ChargeCategorySerializer(data=request.data)
                if serializer.is_valid(raise_exception=True):
                    category = serializer.save(added_by=request.user)

                    # Log activity
                    AdminActivityLog.objects.create(
                        table_id=category.category_id,
                        table_name='charge_category',
                        ua_action='create',
                        ua_description=f'Created charge category: {category.category_name}',
                        created_by=request.user
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Charge category created successfully'
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_categories(self, request):
        """Fetch paginated and filtered list of charge categories"""
        try:
            # Pagination params
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))

            if page < 1 or size < 1 or size > 100:
                return Response({
                    'status': 'fail',
                    'message': 'Valid page_number (≥1) and page_size (1-100) required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Optional filters
            category_id = request.data.get('category_id')
            search = request.data.get('search')
            sort_field = request.data.get('sort_by', 'category_id')
            sort_order = request.data.get('order', 'desc')  # asc or desc

            # Base queryset
            qs = ChargeCategory.objects.filter(is_removed=False)

            # Single record fetch
            if category_id:
                try:
                    category = qs.get(category_id=category_id)
                    serializer = ChargeCategorySerializer(category)
                    return Response({
                        'status': 'success',
                        'message': 'Category details',
                        'data': serializer.data
                    }, status=status.HTTP_200_OK)
                except ChargeCategory.DoesNotExist:
                    return Response({
                        'status': 'fail',
                        'message': 'Category not found'
                    }, status=status.HTTP_404_NOT_FOUND)

            # Search
            if search:
                qs = qs.filter(Q(category_name__icontains=search))

            # Sorting
            if sort_order == 'asc':
                qs = qs.order_by(sort_field)
            else:
                qs = qs.order_by(f'-{sort_field}')

            # Date range filter
            start = request.data.get('from_date')
            end = request.data.get('to_date')
            if start and end:
                qs = qs.filter(added_on__date__range=[start, end])

            # Pagination
            paginator = Paginator(qs, size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            serializer = ChargeCategorySerializer(page_obj, many=True)

            response_payload = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            return Response({
                'status': 'success',
                'message': 'Charge categories fetched',
                'data': response_payload
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({
                'status': 'fail',
                'message': 'Invalid pagination values'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Update existing charge category"""
        category_id = request.data.get('category_id')
        new_name = request.data.get('category_name')

        if not category_id or not new_name:
            return Response({
                'status': 'fail',
                'message': 'category_id and category_name are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = ChargeCategory.objects.get(category_id=category_id, is_removed=False)
            
            # Use serializer for validation (including uniqueness)
            serializer = ChargeCategorySerializer(category, data={'category_name': new_name}, partial=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save(modified_on=datetime.now())

                # Log update
                AdminActivityLog.objects.create(
                    table_id=category.category_id,
                    table_name='charge_category',
                    ua_action='update',
                    ua_description=f'Updated category name to: {new_name}',
                    created_by=request.user
                )

                return Response({
                    'status': 'success',
                    'message': 'Charge category updated successfully'
                }, status=status.HTTP_200_OK)

        except ChargeCategory.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """Soft delete a charge category"""
        category_id = request.data.get('category_id')
        if not category_id:
            return Response({
                'status': 'fail',
                'message': 'category_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = ChargeCategory.objects.get(category_id=category_id, is_removed=False)
            category.is_removed = True
            category.save()

            # Log deletion
            AdminActivityLog.objects.create(
                table_id=category.category_id,
                table_name='charge_category',
                ua_action='delete',
                ua_description=f'Soft deleted category: {category.category_name}',
                created_by=request.user
            )

            return Response({
                'status': 'success',
                'message': 'Charge category deleted successfully'
            }, status=status.HTTP_200_OK)

        except ChargeCategory.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)