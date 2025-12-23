from ...views import*



class GadgetCategoryView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.get_category_list(request)
            elif 'category_name' in request.data or 'name' in request.data:
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
            name = request.data.get('category_name') or request.data.get('name')
            details = request.data.get('description') or request.data.get('details')
            parent_id = request.data.get('parent_category_id') or request.data.get('parent')

            save_api_log(request, "OwnAPI", request.data, {"status": "processing"}, None,
                         service_type="Create Device Category", client_override="fintech_backend_db")

            if not name:
                return Response({
                    'status': 'fail',
                    'message': 'Category name is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if GadgetCategory.objects.filter(name__iexact=name, removed=False).exists():
                return Response({
                    'status': 'fail',
                    'message': 'A category with this name already exists'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                GadgetCategory.objects.create(
                    name=name,
                    details=details,
                    parent=parent_id,
                    created_by=request.user.id
                )

                save_api_log(request, "OwnAPI", request.data, {"status": "success"}, None,
                             service_type="Create Device Category", client_override="fintech_backend_db")

            return Response({
                'status': 'success',
                'message': 'Device category created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            save_api_log(request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                         service_type="Create Device Category", client_override="fintech_backend_db")
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_category_list(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            search = request.data.get('search', '')
            parent_id = request.data.get('parent_category_id') or request.data.get('parent')
            only_sub = request.data.get('only_subcategories', False)

            queryset = GadgetCategory.objects.filter(removed=False).order_by('-cat_id')

            if parent_id:
                queryset = queryset.filter(parent=parent_id)
            elif only_sub:
                queryset = queryset.exclude(parent__isnull=True)

            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(details__icontains=search)
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
                if cat.parent:
                    parent = GadgetCategory.objects.filter(cat_id=cat.parent).first()
                    parent_name = parent.name if parent else None

                results.append({
                    'category_id': cat.cat_id,
                    'category_name': cat.name,
                    'parent_category_id': cat.parent,
                    'parent_category_name': parent_name,
                    'description': cat.details,
                    'created_at': cat.created_on.strftime("%d %B %Y %I:%M %p")
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

            category = GadgetCategory.objects.get(cat_id=cat_id)
            if GadgetCategory.objects.filter(name__iexact=name).exclude(cat_id=cat_id).exists():
                return Response({
                    'status': 'fail',
                    'message': 'Category name already taken'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                category.name = name
                if desc is not None:
                    category.details = desc
                if parent is not None:
                    category.parent = parent
                category.updated_on = timezone.now()
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

            category = GadgetCategory.objects.get(cat_id=cat_id)

            with transaction.atomic():
                category.inactive = True
                category.removed = True
                category.updated_on = timezone.now()
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
            elif all(k in request.data for k in ['category_id', 'price', 'stock_qty', 'model_number', 'purchase_date']):
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
            purchase_date = request.data.get('purchase_date')
            desc = request.data.get('description', '')
            image = request.FILES.get('product_image')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Create Product", client_override="fintech_backend_db"
            )

            if not all([category_id, price, stock, model, purchase_date]):
                return Response({
                    'status': 'fail',
                    'message': 'Missing required fields'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                category = ProductItemCategory.objects.get(cat_id=category_id)
            except ProductItemCategory.DoesNotExist:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid category'
                }, status=status.HTTP_404_NOT_FOUND)

            image_path = store_uploaded_document(image, 'products') if image else None
            image_data = {'product_image': image_path} if image_path else None

            with transaction.atomic():
                ProductItem.objects.create(
                    category=category,
                    manufacturer=model.split()[0] if ' ' in model else model,
                    item_model=model,
                    stock_count=stock,
                    unit_price=price,
                    purchase_date=purchase_date,
                    details=desc,
                    images=image_data,
                    added_by=request.user,
                )

                save_api_log(
                    request, "OwnAPI", request.data, {"status": "success"}, None,
                    service_type="Create Product", client_override="fintech_backend_db"
                )

            return Response({
                'status': 'success',
                'message': 'Product created successfully'
            }, status=status.HTTP_201_CREATED)

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

            products = ProductItem.objects.select_related('category').filter(inactive=False, removed=False).order_by('-item_id')

            if search:
                products = products.filter(
                    Q(item_model__icontains=search) |
                    Q(details__icontains=search) |
                    Q(category__name__icontains=search)
                )
            if cat_id:
                products = products.filter(category__cat_id=cat_id)

            paginator = Paginator(products, size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found'
                }, status=status.HTTP_404_NOT_FOUND)

            results = []
            for prod in page_obj:
                results.append({
                    'item_id': prod.item_id,
                    'category_id': prod.category.cat_id,
                    'category_name': prod.category.name,
                    'manufacturer': prod.manufacturer,
                    'item_model': prod.item_model,
                    'stock_count': prod.stock_count,
                    'unit_price': str(prod.unit_price),
                    'purchase_date': prod.purchase_date.strftime("%Y-%m-%d"),
                    'details': prod.details,
                    'images': prod.images,
                    'added_on': prod.added_on.strftime("%d %B %Y %I:%M %p"),
                })

            return Response({
                'status': 'success',
                'message': 'Products fetched successfully',
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
            item_id = request.data.get('product_id')
            cat_id = request.data.get('category_id')
            desc = request.data.get('description')
            price = request.data.get('price')
            stock = request.data.get('stock_qty')
            image = request.FILES.get('product_image')
            purchase_date = request.data.get('purchase_date')

            save_api_log(
                request, "OwnAPI", request.data, {"status": "processing"}, None,
                service_type="Update Product", client_override="fintech_backend_db"
            )

            if not item_id:
                return Response({
                    'status': 'fail',
                    'message': 'Product ID required'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = ProductItem.objects.get(item_id=item_id)

            with transaction.atomic():
                if cat_id:
                    try:
                        product.category = ProductItemCategory.objects.get(cat_id=cat_id)
                    except ProductItemCategory.DoesNotExist:
                        return Response({
                            'status': 'fail',
                            'message': 'Invalid category'
                        }, status=status.HTTP_404_NOT_FOUND)

                if desc is not None:
                    product.details = desc
                if price is not None:
                    product.unit_price = price
                if stock is not None:
                    product.stock_count = stock
                if purchase_date:
                    product.purchase_date = purchase_date
                if image:
                    path = store_uploaded_document(image, 'products')
                    product.images = {'product_image': path}

                product.modified_on = timezone.now()
                product.save()

            save_api_log(
                request, "OwnAPI", request.data, {"status": "success"}, None,
                service_type="Update Product", client_override="fintech_backend_db"
            )

            return Response({
                'status': 'success',
                'message': 'Product updated successfully'
            }, status=status.HTTP_200_OK)

        except ProductItem.DoesNotExist:
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
            item_id = request.data.get('product_id')
            if not item_id:
                return Response({
                    'status': 'fail',
                    'message': 'Product ID required'
                }, status=status.HTTP_400_BAD_REQUEST)

            product = ProductItem.objects.get(item_id=item_id)
            with transaction.atomic():
                product.inactive = True
                product.removed = True
                product.modified_on = timezone.now()
                product.save()

            return Response({
                'status': 'success',
                'message': 'Product deleted successfully'
            }, status=status.HTTP_200_OK)

        except ProductItem.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.shortcuts import get_object_or_404


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
                return Response({'status': 'error', 'message': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def export_template(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return Response({'status': 'fail', 'message': 'Product ID required'}, status=status.HTTP_400_BAD_REQUEST)

            product = get_object_or_404(ProductItem, item_id=product_id)
            qty = product.stock_count or 0
            name = product.manufacturer
            model = product.item_model

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
            return Response({'status': 'success', 'file_url': file_url}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def import_serials(self, request):
        try:
            product_id = request.data.get('product_id')
            file = request.FILES.get('serial_file')

            save_api_log(request, "OwnAPI", request.data, {"status": "processing"}, None,
                         service_type="Import Product Serials", client_override="fintech_backend_db")

            if not product_id or not file:
                return Response({'status': 'fail', 'message': 'Product ID and file required'}, status=status.HTTP_400_BAD_REQUEST)

            wrapper = TextIOWrapper(file.file, encoding='utf-8')
            reader = csv.DictReader(wrapper)
            serials = [row['Serial Number'].strip() for row in reader if row.get('Serial Number', '').strip()]

            if not serials:
                return Response({'status': 'fail', 'message': 'No serial numbers found in file'}, status=status.HTTP_400_BAD_REQUEST)

            product = get_object_or_404(ProductItem, item_id=product_id)
            existing_count = ItemSerial.objects.filter(item=product, deactivated=False, deleted=False).count()
            available = product.stock_count - existing_count
            unique_serials = list(set(serials))

            if len(unique_serials) > available:
                return Response({'status': 'fail', 'message': f'Only {available} serials can be added'}, status=status.HTTP_400_BAD_REQUEST)

            duplicates = ItemSerial.objects.filter(serial_code__in=unique_serials, deleted=False).values_list('serial_code', flat=True)
            if set(unique_serials) & set(duplicates):
                return Response({'status': 'fail', 'message': 'Some serial numbers already exist'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                ItemSerial.objects.bulk_create([
                    ItemSerial(
                        item=product, 
                        serial_code=s,
                        created_by=request.user.id
                    ) for s in unique_serials
                ])
                save_api_log(request, "OwnAPI", request.data, {"status": "success"}, None,
                             service_type="Import Product Serials", client_override="fintech_backend_db")

            return Response({'status': 'success', 'message': f'{len(unique_serials)} serial numbers imported'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            save_api_log(request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                         service_type="Import Product Serials", client_override="fintech_backend_db")
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_serial_list(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            product_id = request.data.get('product_id')
            search = request.data.get('search')
            active_only = request.data.get('only_active', False)

            qs = ItemSerial.objects.filter(deactivated=False) if active_only else ItemSerial.objects.all()
            if product_id:
                qs = qs.filter(item__item_id=product_id)
            if search:
                qs = qs.filter(serial_code__icontains=search)

            paginator = Paginator(qs, size)
            page_obj = paginator.page(page)

            results = []
            for serial in page_obj:
                results.append({
                    'serial_id': serial.serial_id,
                    'serial_number': serial.serial_code,
                    'product_name': serial.item.item_model if serial.item else None,
                    'product_id': serial.item.item_id if serial.item else None,
                    'category_id': serial.item.category.cat_id if serial.item and serial.item.category else None,
                    'created_at': serial.created_on.strftime("%Y-%m-%d %H:%M:%S")
                })

            return Response({'status': 'success', 'message': 'Serial numbers fetched',
                             'data': {'total_items': paginator.count, 'total_pages': paginator.num_pages,
                                      'current_page': page, 'results': results}}, status=status.HTTP_200_OK)

        except EmptyPage:
            return Response({'status': 'fail', 'message': 'Page not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def put(self, request):
        try:
            serial_id = request.data.get('serial_id')
            new_serial = request.data.get('serial_number')
            new_product_id = request.data.get('product_id')

            save_api_log(request, "OwnAPI", request.data, {"status": "processing"}, None,
                         service_type="Update Serial Number", client_override="fintech_backend_db")

            if not serial_id:
                return Response({'status': 'fail', 'message': 'Serial ID required'}, status=status.HTTP_400_BAD_REQUEST)

            serial = get_object_or_404(ItemSerial, serial_id=serial_id)
            with transaction.atomic():
                if new_serial:
                    if ItemSerial.objects.exclude(serial_id=serial_id).filter(serial_code=new_serial).exists():
                        return Response({'status': 'fail', 'message': 'Serial number already exists'}, status=status.HTTP_400_BAD_REQUEST)
                    serial.serial_code = new_serial
                if new_product_id:
                    serial.item = get_object_or_404(ProductItem, item_id=new_product_id)
                serial.updated_on = timezone.now()
                serial.save()

                save_api_log(request, "OwnAPI", request.data, {"status": "success"}, None,
                             service_type="Update Serial Number", client_override="fintech_backend_db")

            return Response({'status': 'success', 'message': 'Serial number updated'}, status=status.HTTP_200_OK)

        except Exception as e:
            save_api_log(request, "OwnAPI", request.data, {"status": "error", "message": str(e)}, None,
                         service_type="Update Serial Number", client_override="fintech_backend_db")
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            serial_id = request.data.get('serial_id')
            if not serial_id:
                return Response({'status': 'fail', 'message': 'Serial ID required'}, status=status.HTTP_400_BAD_REQUEST)

            serial = get_object_or_404(ItemSerial, serial_id=serial_id)
            with transaction.atomic():
                serial.deactivated = True
                serial.deleted = True
                serial.updated_on = timezone.now()
                serial.save()

            return Response({'status': 'success', 'message': 'Serial number deleted'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
