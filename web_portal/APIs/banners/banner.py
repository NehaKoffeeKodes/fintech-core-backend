from ...views import *


class AdminBannerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get('page_number') is not None or request.data.get('page_size') is not None:
            return self.list_Adminbanners(request)
        elif 'client_name' in request.data:
            return self.add_new_Adminbanner(request)
        else:
            return Response({
                'status': 'fail',
                'message': 'Invalid payload. Either provide pagination params or Adminbanner data.'
            }, status=status.HTTP_400_BAD_REQUEST)

    def add_new_Adminbanner(self, request):
        try:
            client_name = request.data.get('client_name')
            designation = request.data.get('designation', '')
            review_text = request.data.get('review_text', '')
            rating = request.data.get('rating')
            profile_photos = request.FILES.getlist('profile_photo')

            if not client_name:
                return Response({'status': 'fail', 'message': 'client_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if Adminbanner.objects.filter(client_name__iexact=client_name, is_deleted=False).exists():
                return Response({
                    'status': 'fail',
                    'message': 'A Adminbanner from this client already exists.'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not profile_photos:
                return Response({
                    'status': 'fail',
                    'message': 'Profile photo is required.'
                }, status=status.HTTP_400_BAD_REQUEST)

            def upload_client_images(files, subfolder):
                base_dir = f'media/Adminbanner/{subfolder}/'
                os.makedirs(base_dir, exist_ok=True)
                saved_paths = []
                for file_obj in files:
                    if not hasattr(file_obj, 'name'):
                        return None
                    ext = file_obj.name.rsplit('.', 1)[-1].lower()
                    if ext not in {'png', 'jpg', 'jpeg', 'webp'}:
                        return None
                    clean_name = ''.join(c for c in file_obj.name if c.isalnum() or c in '._-')
                    full_path = os.path.join(base_dir, clean_name)
                    with open(full_path, 'wb+') as destination:
                        for chunk in file_obj.chunks():
                            destination.write(chunk)
                    saved_paths.append(f'/{base_dir}{clean_name}')
                return saved_paths

            uploaded_urls = upload_client_images(profile_photos, 'Profile')
            if uploaded_urls is None:
                return Response({
                    'status': 'fail',
                    'message': 'Only PNG, JPG, JPEG, WEBP images are allowed.'
                }, status=status.HTTP_400_BAD_REQUEST)

            active_count = Adminbanner.objects.filter(is_inactive=False, is_deleted=False).count()
            make_inactive = active_count >= 5

            Adminbanner.objects.create(
                client_name=client_name,
                designation=designation,
                review_text=review_text,
                rating=int(rating) if rating else None,
                profile_photo=uploaded_urls[0],
                is_inactive=make_inactive,
                added_by=request.user
            )

            return Response({
                'status': 'success',
                'message': 'Adminbanner added successfully.'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_Adminbanners(self, request):
        response_template = {
            "total_pages": 0,
            "current_page": 1,
            "total_items": 0,
            "results": []
        }
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            banner_id = request.data.get('banner_id')
            keyword = request.data.get('search', '').strip()

            if page < 1 or size < 1:
                return Response({
                    'status': 'fail',
                    'message': 'Page number and page size must be positive integers.',
                    'data': response_template
                }, status=status.HTTP_400_BAD_REQUEST)

            queryset = Adminbanner.objects.filter(is_deleted=False).order_by('-id')

            if banner_id:
                if not is_positive_integer(banner_id):
                    return Response({
                        'status': 'fail',
                        'message': 'Invalid banner_id format.',
                        'data': response_template
                    }, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(id=int(banner_id))

            if keyword:
                queryset = queryset.filter(
                    Q(client_name__icontains=keyword) |
                    Q(designation__icontains=keyword) |
                    Q(review_text__icontains=keyword)
                )

            total = queryset.count()
            total_pages = (total + size - 1) // size if total > 0 else 1
            start = (page - 1) * size

            paginated_banners = list(queryset[start:start + size])

            serializer = AdminbannerSerializer(paginated_banners, many=True)

            host = request.META.get('HTTP_HOST', 'localhost:8000')
            for item in serializer.data:
                photo_path = str(item['profile_photo']).lstrip('/')
                if photo_path.startswith('media/'):
                    photo_path = photo_path[6:]
                item['profile_photo'] = f"http://{host}/media/{photo_path}"

            add_serial_numbers(serializer.data,page,size,order="desc")
            response_template.update({
                "total_pages": total_pages,
                "current_page": page,
                "total_items": total,
                "results": serializer.data
            })

            return Response({
                'status': 'success',
                'message': 'Adminbanners fetched successfully.',
                'data': response_template
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'data': response_template
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            banner_id = request.data.get('banner_id')
            if not banner_id or not is_positive_integer(banner_id):
                return Response({'status': 'fail', 'message': 'Valid banner_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            banner = Adminbanner.objects.filter(id=banner_id, is_deleted=False).first()
            if not banner:
                return Response({'status': 'fail', 'message': 'Adminbanner not found.'}, status=status.HTTP_404_NOT_FOUND)

            new_name = request.data.get('client_name')
            if new_name and Adminbanner.objects.filter(client_name__iexact=new_name, is_deleted=False).exclude(id=banner_id).exists():
                return Response({'status': 'fail', 'message': 'Another Adminbanner with this client name already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            def handle_photo_upload(files):
                if not files:
                    return None
                base_dir = 'media/Adminbanner/Profile/'
                os.makedirs(base_dir, exist_ok=True)
                for file in files:
                    ext = file.name.rsplit('.', 1)[-1].lower()
                    if ext not in {'png', 'jpg', 'jpeg', 'webp'}:
                        return Response({'status': 'fail', 'message': 'Invalid image format.'}, status=status.HTTP_400_BAD_REQUEST)
                    clean_name = ''.join(c for c in file.name if c.isalnum() or c in '._-')
                    path = os.path.join(base_dir, clean_name)
                    with open(path, 'wb+') as f:
                        for chunk in file.chunks():
                            f.write(chunk)
                    return f'/media/Adminbanner/Profile/{clean_name}'
                return None

            if not any(k in request.data for k in ['client_name', 'designation', 'review_text', 'rating', 'profile_photo']):
                active_count = Adminbanner.objects.filter(is_inactive=False, is_deleted=False).count()
                if active_count >= 5 and not banner.is_inactive:
                    return Response({'status': 'fail', 'message': 'Maximum 5 active Adminbanners allowed.'}, status=status.HTTP_400_BAD_REQUEST)
                if active_count <= 1 and banner.is_inactive == False:
                    return Response({'status': 'fail', 'message': 'At least one Adminbanner must remain active.'}, status=status.HTTP_400_BAD_REQUEST)

                banner.is_inactive = not banner.is_inactive
                msg = 'Adminbanner deactivated.' if banner.is_inactive else 'Adminbanner activated.'
            else:
                msg = 'Adminbanner updated successfully.'
                if new_name:
                    banner.client_name = new_name
                if request.data.get('designation'):
                    banner.designation = request.data.get('designation')
                if request.data.get('review_text'):
                    banner.review_text = request.data.get('review_text')
                if request.data.get('rating'):
                    banner.rating = int(request.data.get('rating'))

                new_photos = request.FILES.getlist('profile_photo')
                if new_photos:
                    result = handle_photo_upload(new_photos)
                    if isinstance(result, Response):
                        return result
                    banner.profile_photo = result

            banner.modified_at = timezone.now()
            banner.save()

            return Response({'status': 'success', 'message': msg}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        banner_id = request.data.get('banner_id')
        if not banner_id or not is_positive_integer(banner_id):
            return Response({'status': 'fail', 'message': 'Valid banner_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                banner_obj = Adminbanner.objects.select_for_update().get(id=banner_id, is_deleted=False)
                active_count = Adminbanner.objects.filter(is_inactive=False, is_deleted=False).count()

                if not banner_obj.is_inactive and active_count <= 1:
                    return Response({'status': 'fail', 'message': 'Cannot delete the last active Adminbanner.'}, status=status.HTTP_400_BAD_REQUEST)

                banner_obj.is_deleted = True
                banner_obj.is_inactive = True
                banner_obj.save()

                AdminActivityLog.objects.create(
                    table_id=banner_obj.id,
                    table_name='Adminbanner',
                    ua_action='Soft Delete',
                    ua_description=f'Adminbanner soft-deleted by {request.user}',
                    created_by=request.user,
                    request_data=request.data
                )

                return Response({'status': 'success', 'message': 'Adminbanner removed successfully.'}, status=status.HTTP_200_OK)

        except Adminbanner.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Adminbanner not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PublicAdminbannerAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            banners = Adminbanner.objects.filter(is_inactive=False, is_deleted=False).order_by('-id')
            if not banners.exists():
                return Response({'status': 'fail', 'message': 'No Adminbanners found.', 'data': []}, status=status.HTTP_404_NOT_FOUND)

            serializer = AdminbannerSerializer(banners, many=True, context={'request': request})
            host = request.META.get('HTTP_HOST', 'localhost:8000')

            for item in serializer.data:
                photo = str(item['profile_photo']).lstrip('/')
                item['profile_photo'] = f"http://{host}/{photo}"

            return Response({
                'status': 'success',
                'message': 'Adminbanners retrieved.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e), 'data': []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)