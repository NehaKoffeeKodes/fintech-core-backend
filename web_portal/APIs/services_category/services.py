from ...views import*

class ServiceCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if request.data.get('page_size') and request.data.get('page_number'):
                return self.list_categories(request)
            elif request.data.get('category_title'):
                return self.add_new_category(request)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Request payload not recognized'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_new_category(self, request):
        try:
            with transaction.atomic():
                title = request.data.get('category_title')
                if not title:
                    return Response({'status': 'fail', 'message': 'Category title required'}, status=status.HTTP_400_BAD_REQUEST)

                if ServiceCategory.objects.filter(category_title__iexact=title, is_removed=False).exists():
                    return Response({'status': 'fail', 'message': 'Category already exists'}, status=status.HTTP_400_BAD_REQUEST)

                serializer = ServiceCategorySerializer(data=request.data, context={'request': request})
                if serializer.is_valid():
                    category = serializer.save(added_by=request.user)

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='create',
                        description=f'Added new service category: "{category.category_title}"',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_data=request.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Category added successfully'
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_categories(self, request):
        try:
            page_size = request.data.get('page_size')
            page_no = request.data.get('page_number', 1)

            if not page_size or not str(page_size).isdigit() or int(page_size) < 1:
                return Response({'status': 'fail', 'message': 'Valid page_size is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not str(page_no).isdigit() or int(page_no) < 1:
                return Response({'status': 'fail', 'message': 'Valid page_number is required'}, status=status.HTTP_400_BAD_REQUEST)

            queryset = ServiceCategory.objects.filter(is_removed=False).order_by('-category_id')

            cat_id = request.data.get('category_id')
            if cat_id:
                queryset = queryset.filter(category_id=cat_id)

            hidden = request.data.get('is_hidden')
            if hidden == 'true':
                queryset = queryset.filter(is_hidden=True)
            elif hidden == 'false':
                queryset = queryset.filter(is_hidden=False)

            search = request.data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(category_title__icontains=search) | Q(short_info__icontains=search)
                )

            if not queryset.exists():
                return Response({
                    'status': 'fail',
                    'message': 'No categories found',
                    'data': {'total_pages': 0, 'current_page': 0, 'total_items': 0, 'results': []}
                }, status=status.HTTP_200_OK)

            paginator = Paginator(queryset, page_size)
            try:
                page = paginator.page(page_no)
            except EmptyPage:
                return Response({'status': 'fail', 'message': 'Page out of range'}, status=status.HTTP_404_NOT_FOUND)

            serializer = ServiceCategorySerializer(
                page.object_list, many=True,
                context={'request': request, 'exclude_fields': ['added_on', 'last_updated', 'is_removed', 'added_by']}
            )
            serializer = ServiceCategorySerializer(
                page.object_list, many=True,
                context={'request': request, 'exclude_fields': ['added_on', 'last_updated', 'is_removed', 'added_by']}
            )

            add_serial_numbers(
                data_list=serializer.data,
                page=int(page_no),
                page_size=int(page_size),
                order=str(request.data.get('order_by', 'asc')).lower()
            )

            result = {
                'total_pages': paginator.num_pages,
                'current_page': page.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            return Response({                     
                'status': 'success',
                'message': 'Categories retrieved',
                'data': result
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            with transaction.atomic():
                cat_id = request.data.get('category_id')
                if not cat_id:
                    return Response({'status': 'fail', 'message': 'category_id required'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    category = ServiceCategory.objects.get(category_id=cat_id, is_removed=False)
                except ServiceCategory.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

                serializer = ServiceCategorySerializer(category, data=request.data, partial=True, context={'request': request})
                if serializer.is_valid():
                    serializer.save(last_updated=now())

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='update',
                        description=f'Updated service category: "{category.category_title}"',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_data=request.data
                    )

                    if 'is_hidden' in request.data:
                        msg = 'Category hidden successfully' if serializer.instance.is_hidden else 'Category made visible successfully'
                    else:
                        msg = 'Category updated successfully'

                    return Response({'status': 'success', 'message': msg}, status=status.HTTP_200_OK)

                return Response({'status': 'fail', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        cat_id = request.data.get('category_id')
        if not cat_id:
            return Response({'status': 'fail', 'message': 'category_id is mandatory'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                category = ServiceCategory.objects.get(category_id=cat_id)

                active_count = ServiceCategory.objects.filter(is_hidden=False, is_removed=False).count()
                if active_count <= 1 and not category.is_hidden:
                    return Response({
                        'status': 'fail',
                        'message': 'At least one visible category must exist'
                    }, status=status.HTTP_400_BAD_REQUEST)

                products = Product.objects.filter(category=category)
                if products.exists():
                    products.update(is_removed=True)
                    category.is_removed = True
                    category.is_hidden = True
                    category.save()
                    msg = 'Category and all linked products removed'
                else:
                    category.is_removed = True
                    category.is_hidden = True
                    category.save()
                    msg = 'Category removed successfully'

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='delete',
                    description=f'Removed service category: "{category.category_title}"',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_data=request.data
                )

                return Response({'status': 'success', 'message': msg}, status=status.HTTP_200_OK)

        except ServiceCategory.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Category does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({'status': 'error', 'message': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PublicCategoryView(APIView):
    permission_classes = [AllowAny]
    VALID_DOMAINS = ['localhost:3000', '127.0.0.1:8000', 'yourdomain.com']

    def get(self, request):
        host = request.META.get('HTTP_HOST')
        if host not in self.VALID_DOMAINS:
            return Response({'status': 'error', 'message': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        categories = ServiceCategory.objects.filter(is_hidden=False, is_removed=False)

        if not categories.exists():
            return Response({'status': 'fail', 'message': 'No categories available', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

        data = ServiceCategorySerializer(categories, many=True, context={
            'request': request,
            'exclude_fields': ['added_on', 'last_updated', 'is_removed', 'added_by']
        }).data

        return Response({
            'status': 'success',
            'message': 'Categories loaded',
            'data': data
        }, status=status.HTTP_200_OK)


class PublicCategoryWithProducts(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        host = request.META.get('HTTP_HOST')
        if host not in PublicCategoryView.VALID_DOMAINS:
            return Response({'status': 'error', 'message': 'Invalid source'}, status=status.HTTP_403_FORBIDDEN)

        categories = ServiceCategory.objects.filter(is_removed=False, is_hidden=False)
        cat_data = CategoryDetailSerializer(categories, many=True, context={
            'request': request,
            'exclude_fields': ['added_on', 'last_updated', 'is_removed', 'added_by']
        }).data

        orphan_products = Product.objects.filter(category__isnull=True, is_removed=False, is_hidden=False)
        orphan_data = ProductInfoSerializer(orphan_products, many=True, context={
            'request': request,
            'exclude_fields': ['added_on', 'last_updated', 'is_removed', 'added_by']
        }).data

        return Response({
            'status': 'success',
            'message': 'Data fetched',
            'categories': cat_data,
            'standalone_products': orphan_data
        }, status=status.HTTP_200_OK)