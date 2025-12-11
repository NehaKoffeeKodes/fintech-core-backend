from web_portal.APIs.latestnews_update.news_hub import ALLOWED_DOMAIN
from ...views import*

class ServiceManagementView(APIView):
    permission_classes = [IsAuthenticated]
    
    ALLOWED_DOMAINS = ["localhost:3000","127.0.0.1:8000"]

    def post(self, request):
        if 'page_no' in request.data or 'limit' in request.data:
            return self.list_products(request)
        elif 'name' in request.data and 'images' in request.FILES and 'details' in request.data:
            return self.add_new_product(request)
        return Response({
            'status': 'fail',
            'message': 'Invalid payload structure.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def add_new_product(self, request):
        try:
            category_id = request.data.get('category_id')
            product_name = request.data.get('name')
            product_details = request.data.get('details')
            uploaded_images = request.FILES.getlist('images')

            category_obj = None
            if category_id:
                if not category_id.isdigit():
                    return Response({'status': 'fail', 'message': 'Invalid category_id.'}, status=status.HTTP_400_BAD_REQUEST)
                category_obj = ServiceCategory.objects.filter(category_id=int(category_id), is_removed=False).first()
                if not category_obj:
                    return Response({'status': 'fail', 'message': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

            if Product.objects.filter(name=product_name, category=category_obj, is_removed=False).exists():
                return Response({'status': 'fail', 'message': 'Product already exists in this category.'}, status=status.HTTP_400_BAD_REQUEST)

            if not uploaded_images:
                return Response({'status': 'fail', 'message': 'Image is required.'}, status=status.HTTP_400_BAD_REQUEST)

            image = uploaded_images[0]
            allowed_ext = ['png', 'jpg', 'jpeg', 'webp']
            if image.name.rsplit('.', 1)[-1].lower() not in allowed_ext:
                return Response({'status': 'fail', 'message': 'Invalid image format.'}, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.create(name=product_name,thumbnail=image,details=product_details,category=category_obj,is_hidden=False,added_by=category_obj,is_removed=False)

            try:
                safe_data = {}
                for k, v in request.data.items():
                    if hasattr(v, 'name'):
                        safe_data[k] = f"File: {v.name} ({v.size} bytes)"
                    else:
                        safe_data[k] = v

                if uploaded_images:
                    safe_data['images_count'] = len(uploaded_images)

                AdminActivityLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='PRODUCT_CREATED',
                    description=f'Created product: {product_name}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_data=safe_data
                )
            except Exception as e:
                print("Log error (ignored):", e)  

            return Response({
                'status': 'success',
                'message': 'Product created successfully!',
                'product_id': product.product_id
            }, status=201)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_products(self, request):
        empty_response = {
            "total_pages": 0,
            "current_page": 1,
            "total_count": 0,
            "items": []
        }
        
        try:
            page = int(request.data.get('page_no', 1))
            limit = int(request.data.get('limit', 10))
            product_id = request.data.get('product_id')

            if page < 1:
                return Response({'status': 'fail', 'message': 'page_no must be >= 1'}, status=status.HTTP_400_BAD_REQUEST)
            if limit < 1:
                return Response({'status': 'fail', 'message': 'limit must be >= 1'}, status=status.HTTP_400_BAD_REQUEST)

            queryset = Product.objects.filter(
                is_removed=False     
            ).order_by('-product_id')  

            if product_id:
                if not str(product_id).isdigit():
                    return Response({'status': 'fail', 'message': 'Invalid product_id'}, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(product_id=int(product_id))

            total = queryset.count()
            start = (page - 1) * limit
            end = start + limit
            products = queryset[start:end]

            if product_id and not products:
                return Response({'status': 'fail', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

            serializer = ProductDetailSerializer(products, many=True, context={'request': request})

            for item in serializer.data:
                img_path = item.get('thumbnail', '')
                if img_path:
                    if img_path.startswith('/media/'):
                        img_path = img_path[7:]  
                    host = request.META.get('HTTP_HOST', '127.0.0.1:8000')
                    item['thumbnail'] = f"http://{host}/media/{img_path}"

            add_serial_numbers(data_list=serializer.data, page=page, page_size=limit, order="desc")

            response_data = {
                'total_pages': (total + limit - 1) // limit if total else 0,
                'current_page': page,
                'total_count': total,
                'items': serializer.data
            }

            return Response({
                'status': 'success',
                'message': 'Products retrieved successfully.',
                'data': response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'data': empty_response
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def put(self, request):
        return self.update_product(request)

    def delete(self, request):
        return self.soft_delete_product(request)        

    def update_product(self, request):
        try:
            prod_id = request.data.get('product_id')
            if not prod_id or not str(prod_id).isdigit():
                return Response({'status': 'fail', 'message': 'Valid product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.filter(
                product_id=int(prod_id),
                is_removed=False
            ).first()

            if not product:
                return Response({'status': 'fail', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

            name = request.data.get('name')
            category_id = request.data.get('category_id')
            details = request.data.get('details')
            new_images = request.FILES.getlist('images')

            if name and category_id:
                if Product.objects.filter(
                    name=name,
                    category_id=category_id,
                    is_removed=False
                ).exclude(product_id=product.product_id).exists():
                    return Response({'status': 'fail', 'message': 'Product name already exists in this category.'}, status=status.HTTP_400_BAD_REQUEST)

            if new_images:
                image = new_images[0]
                allowed = ['png', 'jpg', 'jpeg', 'webp']
                ext = image.name.rsplit('.', 1)[-1].lower() if '.' in image.name else ''
                if ext not in allowed:
                    return Response({'status': 'fail', 'message': 'Invalid image format.'}, status=status.HTTP_400_BAD_REQUEST)
                product.thumbnail = image  
            if name: product.name = name
            if details: product.details = details
            if category_id:
                cat = ServiceCategory.objects.filter(category_id=int(category_id), is_removed=False).first()
                if not cat:
                    return Response({'status': 'fail', 'message': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)
                product.category = cat


            if not any([name, new_images, category_id, details]):
                product.is_hidden = not product.is_hidden

            product.last_updated = timezone.now()
            product.save()
            try:
                safe_data = {k: v.name if hasattr(v, 'name') else v for k, v in request.data.items()}
                AdminActivityLog.objects.create(
                    user=request.user,
                    action='PRODUCT_UPDATED',
                    description=f'Updated product: {product.name}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_data=safe_data
                )
            except Exception as e:
                print("Log error:", e)

            return Response({
                'status': 'success',
                'message': 'Product updated successfully!'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def soft_delete_product(self, request):
        try:
            prod_id = request.data.get('product_id')
            if not prod_id or not str(prod_id).isdigit():
                return Response({'status': 'fail', 'message': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                product = Product.objects.select_for_update().get(
                    product_id=int(prod_id),
                    is_removed=False
                )

                visible_count = Product.objects.filter(is_hidden=False, is_removed=False).count()
                if visible_count <= 1 and not product.is_hidden:
                    return Response({
                        'status': 'fail',
                        'message': 'Cannot delete the last visible product.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                product.is_removed = True
                product.is_hidden = True
                product.save()

                try:
                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='PRODUCT_DELETED',
                        description=f'Soft deleted product: {product.name} (ID: {product.product_id})',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_data=request.data
                    )
                except Exception as e:
                    print("Log error:", e)

                return Response({
                    'status': 'success',
                    'message': 'Product deleted successfully.'
                }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PublicServiceListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            host = request.META.get('HTTP_HOST')
            if host not in ALLOWED_DOMAIN:
                return Response({'status': 'error', 'message': 'Domain not allowed.'}, status=status.HTTP_403_FORBIDDEN)

            products = Product.objects.filter(is_hidden=False, is_removed=False)
            
            if not products.exists():
                return Response({'status': 'fail', 'message': 'No products available.', 'data': []}, status=status.HTTP_404_NOT_FOUND)

            serializer = ProductPublicSerializer(products, many=True, context={'request': request})

            return Response({
                'status': 'success',
                'message': 'Active products',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        

class PublicserviceDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            host = request.META.get('HTTP_HOST')
            if host not in ALLOWED_DOMAIN:
                return Response({'status': 'error', 'message': 'Domain not allowed.'}, status=status.HTTP_403_FORBIDDEN)

            pid = request.query_params.get('product_id') 
            if not pid or not pid.isdigit():
                return Response({'status': 'fail', 'message': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.filter(
                product_id=int(pid),
                is_hidden=False,
                is_removed=False
            ).first()

            if not product:
                return Response({'status': 'fail', 'message': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

            serializer = ProductDetailSerializer(product, context={'request': request})

            return Response({
                'status': 'success',
                'message': 'Product details',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)