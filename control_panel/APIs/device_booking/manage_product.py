from ...views import*



class GadgetCategoryView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.get_category_list(request)
            elif 'category_name' in request.data:
                return self.create_new_category(request)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid request format'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_new_category(self, request):
        try:
            name = request.data.get('category_name')
            description = request.data.get('description')
            parent_id = request.data.get('parent_category_id')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Create Device Category", client_override="fintech_backend_db"
            )

            if not name:
                return Response({
                    'status': 'fail',
                    'message': 'Category name is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if GadgetCategory.objects.filter(category_name__iexact=name, is_deleted=False).exists():
                return Response({
                    'status': 'fail',
                    'message': 'A category with this name already exists'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                GadgetCategory.objects.create(
                    category_name=name,
                    description=description,
                    parent_category_id=parent_id,
                    created_by=request.user.id
                )

                save_api_log(
                    request, "OwnAPI", request.data, {"status": "success"}, None,
                    service_type="Create Device Category", client_override="fintech_backend_db"
                )

            return Response({
                'status': 'success',
                'message': 'Device category created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                service_type="Create Device Category", client_override="fintech_backend_db"
            )
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_category_list(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            search = request.data.get('search', '')
            parent_id = request.data.get('parent_category_id')
            only_sub = request.data.get('only_subcategories', False)

            queryset = GadgetCategory.objects.filter(is_deleted=False).order_by('-category_id')

            if parent_id:
                queryset = queryset.filter(parent_category_id=parent_id)
            elif only_sub:
                queryset = queryset.exclude(parent_category_id__isnull=True)

            if search:
                queryset = queryset.filter(
                    Q(category_name__icontains=search) |
                    Q(description__icontains=search)
                )

            paginator = Paginator(queryset, size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found'
                }, status=status.HTTP_404_NOT_FOUND)

            results = []
            for cat in page_obj:
                parent_name = None
                if cat.parent_category_id:
                    parent = GadgetCategory.objects.filter(category_id=cat.parent_category_id).first()
                    parent_name = parent.category_name if parent else None

                results.append({
                    'category_id': cat.category_id,
                    'category_name': cat.category_name,
                    'parent_category_id': cat.parent_category_id,
                    'parent_category_name': parent_name,
                    'description': cat.description,
                    'created_at': cat.created_at.strftime("%d %B %Y %I:%M %p")
                })

            return Response({
                'status': 'success',
                'message': 'Categories fetched successfully',
                'data': {
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'current_page': page,
                    'results': results
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            cat_id = request.data.get('category_id')
            name = request.data.get('category_name')
            desc = request.data.get('description')
            parent = request.data.get('parent_category_id')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Update Device Category", client_override="fintech_backend_db"
            )

            if not cat_id or not name:
                return Response({
                    'status': 'fail',
                    'message': 'Category ID and name are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            category = GadgetCategory.objects.get(category_id=cat_id)

            if GadgetCategory.objects.filter(category_name__iexact=name).exclude(category_id=cat_id).exists():
                return Response({
                    'status': 'fail',
                    'message': 'Category name already taken'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                category.category_name = name
                if desc is not None:
                    category.description = desc
                if parent is not None:
                    category.parent_category_id = parent
                category.updated_at = timezone.now()
                category.save()

                save_api_log(
                    request, "OwnAPI", request.data, {"status": "success"}, None,
                    service_type="Update Device Category", client_override="fintech_backend_db"
                )

            return Response({
                'status': 'success',
                'message': 'Category updated successfully'
            }, status=status.HTTP_200_OK)

        except GadgetCategory.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                service_type="Update Device Category", client_override="fintech_backend_db"
            )
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            cat_id = request.data.get('category_id')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Delete Device Category", client_override="fintech_backend_db"
            )

            if not cat_id:
                return Response({
                    'status': 'fail',
                    'message': 'Category ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            category = GadgetCategory.objects.get(category_id=cat_id)

            with transaction.atomic():
                category.is_deactive = True
                category.is_deleted = True
                category.updated_at = timezone.now()
                category.save()

                save_api_log(
                    request, "OwnAPI", request.data, {"status": "success"}, None,
                    service_type="Delete Device Category", client_override="fintech_backend_db"
                )

            return Response({
                'status': 'success',
                'message': 'Category deleted successfully'
            }, status=status.HTTP_200_OK)

        except GadgetCategory.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                service_type="Delete Device Category", client_override="fintech_backend_db"
            )
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class ProductView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.get_product_list(request)
            elif all(k in request.data for k in ['category_id', 'price', 'stock_qty', 'model_number']):
                return self.create_new_product(request)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid request'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_new_product(self, request):
        try:
            category_id = request.data.get('category_id')
            price = request.data.get('price')
            stock = request.data.get('stock_qty')
            model = request.data.get('model_number')
            desc = request.data.get('description', '')
            image = request.FILES.get('product_image')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Create Product", client_override="fintech_backend_db"
            )

            required_fields = ['category_id', 'price', 'stock_qty', 'model_number']
            missing = enforce_required_fields(request.data, required_fields)
            if missing:
                return missing

            category = GadgetCategory.objects.get(category_id=category_id)

            image_path = store_uploaded_document(image, 'products') if image else None
            image_data = {'product_image': image_path} if image_path else None

            with transaction.atomic():
                Product.objects.create(
                    category=category,
                    product_name=category.category_name,
                    stock_qty=stock,
                    description=desc,
                    model_number=model,
                    price=price,
                    product_image=image_data,
                    created_by=request.user.id
                )

                save_api_log(
                    request, "OwnAPI", request.data, {"status": "success"}, None,
                    service_type="Create Product", client_override="fintech_backend_db"
                )

            return Response({
                'status': 'success',
                'message': 'Product created successfully'
            }, status=status.HTTP_201_CREATED)

        except GadgetCategory.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Invalid category'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                service_type="Create Product", client_override="fintech_backend_db"
            )
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_product_list(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            search = request.data.get('search', '')
            cat_id = request.data.get('category_id')

            products = Product.objects.select_related('category').filter(is_deactive=False).order_by('-product_id')

            if search:
                products = products.filter(
                    Q(product_name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(category__category_name__icontains=search)
                )
            if cat_id:
                products = products.filter(category__category_id=cat_id)

            if not products.exists():
                return Response({
                    'status': 'fail',
                    'message': 'No products found'
                }, status=status.HTTP_404_NOT_FOUND)

            paginator = Paginator(products, size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = GadgetItemSerializer(page_obj, many=True, context={'request': request})
            data = serializer.data

            for item in data:
                item['category_name'] = GadgetCategory.objects.get(category_id=item['category']).category_name

            return Response({
                'status': 'success',
                'message': 'Products fetched successfully',
                'data': {
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'current_page': page,
                    'results': data
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            prod_id = request.data.get('product_id')
            cat_id = request.data.get('category_id')
            desc = request.data.get('description')
            price = request.data.get('price')
            stock = request.data.get('stock_qty')
            image = request.FILES.get('product_image')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Update Product", client_override="fintech_backend_db"
            )

            if not prod_id:
                return Response({
                    'status': 'fail',
                    'message': 'Product ID required'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.get(product_id=prod_id)

            with transaction.atomic():
                if not any([cat_id, desc, price, stock, image]):
                    product.is_deactive = not product.is_deactive
                    action = 'activated' if not product.is_deactive else 'deactivated'
                else:
                    if cat_id:
                        product.category = GadgetCategory.objects.get(category_id=cat_id)
                    if desc is not None:
                        product.description = desc
                    if price is not None:
                        product.price = price
                    if stock is not None:
                        product.stock_qty = stock
                    if image:
                        path = store_uploaded_document(image, 'products')
                        product.product_image = {'product_image': path}
                    action = 'updated'

                product.updated_at = timezone.now()
                product.save()

            save_api_log(
                request, "OwnAPI", request.data, {"status": "success"}, None,
                service_type="Update Product", client_override="fintech_backend_db"
            )

            return Response({
                'status': 'success',
                'message': f'Product {action} successfully'
            }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                service_type="Update Product", client_override="fintech_backend_db"
            )
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            prod_id = request.data.get('product_id')
            if not prod_id:
                return Response({
                    'status': 'fail',
                    'message': 'Product ID required'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.get(product_id=prod_id)
            with transaction.atomic():
                product.is_deleted = True
                product.is_deactive = True
                product.updated_at = timezone.now()
                product.save()

            return Response({
                'status': 'success',
                'message': 'Product deleted successfully'
            }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ItemSerialView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.get_serial_list(request)
            elif 'product_id' in request.data and 'serial_file' in request.FILES:
                return self.import_serials(request)
            elif 'export_template' in request.data:
                return self.export_template(request)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid action'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def export_template(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return Response({
                    'status': 'fail',
                    'message': 'Product ID required'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.get(product_id=product_id)
            qty = product.stock_qty or 0
            name = product.product_name
            model = product.model_number

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{product_id}_serial_template_{timestamp}.csv"
            folder = os.path.join(settings.MEDIA_ROOT, "exports")
            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, filename)

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['S.No', 'Product Name', 'Model Number', 'Serial Number'])
                for i in range(1, qty + 1):
                    writer.writerow([i, name, model, ''])

            file_url = request.build_absolute_uri(settings.MEDIA_URL + f"exports/{filename}")
            return Response({
                'status': 'success',
                'file_url': file_url
            }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def import_serials(self, request):
        try:
            product_id = request.data.get('product_id')
            file = request.FILES.get('serial_file')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Import Product Serials", client_override="fintech_backend_db"
            )

            if not product_id or not file:
                return Response({
                    'status': 'fail',
                    'message': 'Product ID and file required'
                }, status=status.HTTP_400_BAD_REQUEST)

            wrapper = TextIOWrapper(file.file, encoding='utf-8')
            reader = csv.DictReader(wrapper)
            serials = [row['Serial Number'].strip() for row in reader if row.get('Serial Number', '').strip()]

            if not serials:
                return Response({
                    'status': 'fail',
                    'message': 'No serial numbers found in file'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.get(product_id=product_id)
            existing_count = ItemSerial.objects.filter(product=product, is_deactive=False, is_deleted=False).count()
            available = product.stock_qty - existing_count
            unique_serials = list(set(serials))

            if len(unique_serials) > available:
                return Response({
                    'status': 'fail',
                    'message': f'Only {available} serials can be added'
                }, status=status.HTTP_400_BAD_REQUEST)

            duplicates = ItemSerial.objects.filter(
                serial_number__in=unique_serials, is_deleted=False
            ).values_list('serial_number', flat=True)

            if set(unique_serials) & set(duplicates):
                return Response({
                    'status': 'fail',
                    'message': 'Some serial numbers already exist'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                ItemSerial.objects.bulk_create([
                    ItemSerial(
                        product=product,
                        serial_number=s,
                        created_by=request.user.id
                    ) for s in unique_serials
                ])

                save_api_log(
                    request, "OwnAPI", request.data, {"status": "success"}, None,
                    service_type="Import Product Serials", client_override="fintech_backend_db"
                )

            return Response({
                'status': 'success',
                'message': f'{len(unique_serials)} serial numbers imported'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                service_type="Import Product Serials", client_override="fintech_backend_db"
            )
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_serial_list(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            product_id = request.data.get('product_id')
            search = request.data.get('search')
            active_only = request.data.get('only_active', False)

            qs = ItemSerial.objects.filter(is_deactive=False) if active_only else ItemSerial.objects.all()

            if product_id:
                qs = qs.filter(product__product_id=product_id)
            if search:
                qs = qs.filter(serial_number__icontains=search)

            paginator = Paginator(qs, size)
            page_obj = paginator.page(page)

            results = []
            for serial in page_obj:
                results.append({
                    'serial_id': serial.serial_id,
                    'serial_number': serial.serial_number,
                    'product_name': serial.product.product_name if serial.product else None,
                    'product_id': serial.product.product_id if serial.product else None,
                    'category_id': serial.product.category.category_id if serial.product and serial.product.category else None,
                    'created_at': serial.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })

            return Response({
                'status': 'success',
                'message': 'Serial numbers fetched',
                'data': {
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'current_page': page,
                    'results': results
                }
            }, status=status.HTTP_200_OK)

        except EmptyPage:
            return Response({
                'status': 'fail',
                'message': 'Page not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            serial_id = request.data.get('serial_id')
            new_serial = request.data.get('serial_number')
            new_product_id = request.data.get('product_id')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Update Serial Number", client_override="fintech_backend_db"
            )

            if not serial_id:
                return Response({
                    'status': 'fail',
                    'message': 'Serial ID required'
                }, status=status.HTTP_400_BAD_REQUEST)

            serial = ItemSerial.objects.get(serial_id=serial_id)

            with transaction.atomic():
                if new_serial:
                    if ItemSerial.objects.exclude(serial_id=serial_id).filter(serial_number=new_serial).exists():
                        return Response({
                            'status': 'fail',
                            'message': 'Serial number already exists'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    serial.serial_number = new_serial
                if new_product_id:
                    serial.product = Product.objects.get(product_id=new_product_id)
                serial.updated_at = timezone.now()
                serial.save()

                save_api_log(
                    request, "OwnAPI", request.data, {"status": "success"}, None,
                    service_type="Update Serial Number", client_override="fintech_backend_db"
                )

            return Response({
                'status': 'success',
                'message': 'Serial number updated'
            }, status=status.HTTP_200_OK)

        except ItemSerial.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Serial not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            save_api_log(
                request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                service_type="Update Serial Number", client_override="fintech_backend_db"
            )
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            serial_id = request.data.get('serial_id')
            if not serial_id:
                return Response({
                    'status': 'fail',
                    'message': 'Serial ID required'
                }, status=status.HTTP_400_BAD_REQUEST)

            serial = ItemSerial.objects.get(serial_id=serial_id)
            with transaction.atomic():
                serial.is_deleted = True
                serial.is_deactive = True
                serial.updated_at = timezone.now()
                serial.save()

            return Response({
                'status': 'success',
                'message': 'Serial number deleted'
            }, status=status.HTTP_200_OK)

        except ItemSerial.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Serial not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)