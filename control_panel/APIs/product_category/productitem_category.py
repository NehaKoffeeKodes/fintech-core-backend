from ...views import*


class CategoryManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'page_num' in request.data and 'page_size' in request.data:
                return self.list_categories(request)
            elif 'name' in request.data:
                return self.add_category(request)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid request structure.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_category(self, request):
        try:
            serializer = ProductItemSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    category = serializer.save(added_by=request.user)

                    AdminActivityLog.objects.create(
                        table_id=category.cat_id,
                        table_name='item_category',
                        ua_action='create',
                        ua_description='New category added successfully',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data
                    )

                return Response({
                    'status': 'success',
                    'message': 'Category created successfully.'
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_categories(self, request):
        try:
            page_num = int(request.data.get('page_num', 1))
            page_size = request.data.get('page_size', 10)
            inactive_filter = request.data.get('inactive')
            cat_id = request.data.get('cat_id')
            search = request.data.get('search')

            qs = ProductItemCategory.objects.filter(removed=False).order_by('-cat_id')

            if inactive_filter is not None:
                qs = qs.filter(inactive=(inactive_filter in ['true', '1', True]))

            if cat_id:
                qs = qs.filter(cat_id=cat_id)

            if search:
                qs = qs.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search)
                )

            if page_size != "0":
                paginator = Paginator(qs, page_size)

                if not qs.exists():
                    empty_payload = {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                    return Response({
                        'status': 'success',
                        'message': 'No categories found.',
                        'data': empty_payload
                    }, status=status.HTTP_200_OK)

                try:
                    page_data = paginator.page(page_num)
                except EmptyPage:
                    return Response({
                        'status': 'fail',
                        'message': 'Requested page does not exist.'
                    }, status=status.HTTP_404_NOT_FOUND)

                serialized = ProductItemSerializer(
                    page_data.object_list,
                    many=True,
                    context={
                        'request': request,
                        'exclude_fields': ['added_on', 'modified_on', 'removed', 'modified_by', 'added_by']
                    }
                ).data

                payload = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_data.number,
                    'total_items': paginator.count,
                    'results': serialized
                }
            else:
                serialized = ProductItemCategory(
                    qs,
                    many=True,
                    context={
                        'request': request,
                        'exclude_fields': ['added_on', 'modified_on', 'removed', 'modified_by', 'added_by']
                    }
                ).data
                payload = {
                    'total_pages': 1,
                    'current_page': 1,
                    'total_items': qs.count(),
                    'results': serialized
                }

            return Response({
                'status': 'success',
                'message': 'Categories retrieved successfully.',
                'data': payload
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        cat_id = request.data.get('cat_id')
        if not cat_id:
            return Response({
                'status': 'fail',
                'message': 'cat_id is required for update.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = ProductItemCategory.objects.get(cat_id=cat_id, removed=False)
            serializer = ProductItemSerializer(category, data=request.data, partial=True, context={'request': request})

            if serializer.is_valid():
                with transaction.atomic():
                    updated_category = serializer.save(modified_on=datetime.now(), modified_by=request.user)

                    AdminActivityLog.objects.create(
                        table_id=updated_category.cat_id,
                        table_name='item_category',
                        ua_action='update',
                        ua_description='Category details updated',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data
                    )

                    # Custom success message based on what was updated
                    if 'inactive' in request.data:
                        action = "deactivated" if updated_category.inactive else "activated"
                        message = f'Category {action} successfully.'
                    else:
                        message = 'Category updated successfully.'

                    return Response({
                        'status': 'success',
                        'message': message
                    }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except ProductItemCategory.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Category not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        cat_id = request.data.get('cat_id')
        if not cat_id:
            return Response({
                'status': 'fail',
                'message': 'cat_id is required for deletion.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                category = ProductItemCategory.objects.get(cat_id=cat_id, removed=False)
                category.removed = True
                category.inactive = True
                category.save()

                AdminActivityLog.objects.create(
                    table_id=category.cat_id,
                    table_name='item_category',
                    ua_action='delete',
                    ua_description='Category soft-deleted',
                    created_by=request.user,
                    request_data=request.data
                )

                return Response({
                    'status': 'success',
                    'message': 'Category removed successfully.'
                }, status=status.HTTP_200_OK)

        except ProductItemCategory.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Category not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)