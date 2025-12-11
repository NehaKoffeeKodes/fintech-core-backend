from ...views import*

ALLOWED_DOMAINS = ["localhost:3000","127.0.0.1:8000",]

class YouTubeVideoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get('page_number') or request.data.get('page_size'):
            return self.list_videos(request)
        elif 'title' in request.data and 'thumbnail' in request.FILES:
            return self.upload_video(request)
        return Response({
            'status': 'fail',
            'message': 'Invalid request payload.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def list_videos(self, request):
        try:
            video_id = request.data.get('video_id')
            search = request.data.get('q', '').strip()
            active_only = request.data.get('active_only')
            sort_by = request.data.get('sort', 'desc')
            page = int(request.data.get('page_number', 1))
            limit = int(request.data.get('page_size', 10))

            if page < 1 or limit < 1:
                return Response({'status': 'fail', 'message': 'Page and limit must be positive.'}, status=status.HTTP_400_BAD_REQUEST)

            qs = YouTubeVideo.objects.filter(is_deleted=False)

            if video_id:
                if not is_positive_integer(video_id):
                    return Response({'status': 'fail', 'message': 'Invalid video ID.'}, status=status.HTTP_400_BAD_REQUEST)
                qs = qs.filter(id=video_id)

            if search:
                qs = qs.filter(Q(title__icontains=search))

            if active_only == 'true':
                qs = qs.filter(is_active=True)
            elif active_only == 'false':
                qs = qs.filter(is_active=False)

            if sort_by == 'asc':
                qs = qs.order_by('id')
            else:
                qs = qs.order_by('-id')

            if video_id and not qs.exists():
                return Response({'status': 'fail', 'message': 'Video not found.'}, status=status.HTTP_404_NOT_FOUND)

            paginator = Paginator(qs, limit)
            try:
                page_data = paginator.page(page)
            except EmptyPage:
                page_data = paginator.page(paginator.num_pages)

            serializer = VideoContentSerializer(
                page_data.object_list,
                many=True,
                context={'request': request, 'exclude_fields': ['created_at', 'modified_at', 'is_deleted']}
            )

            add_serial_numbers(serializer.data, page, limit, sort_by)

            payload = {
                'total_pages': paginator.num_pages,
                'current_page': page_data.number,
                'total_count': paginator.count,
                'items': serializer.data
            }

            return Response({
                'status': 'success',
                'message': 'Videos retrieved.',
                'data': payload
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def upload_video(self, request):
        try:
            with transaction.atomic():
                if YouTubeVideo.objects.filter(is_active=True).count() >= 10:
                    return Response({
                        'status': 'fail',
                        'message': 'Maximum 10 active videos allowed.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                serializer = VideoContentSerializer(data=request.data, context={'request': request})
                if not serializer.is_valid():
                    return Response({'status': 'fail', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                video = serializer.save(created_by=request.user)

                if video.is_active:
                    YouTubeVideo.objects.filter(is_active=True).exclude(id=video.id).update(is_active=False)

                try:
                    safe_request_data = {}
                    for key, value in request.data.items():
                        if hasattr(value, 'name'): 
                            safe_request_data[key] = {
                                'filename': value.name,
                                'size': value.size,
                                'content_type': value.content_type
                            }
                        else:
                            safe_request_data[key] = value

                    if 'thumbnail' in request.FILES:
                        file = request.FILES['thumbnail']
                        safe_request_data['thumbnail_info'] = {
                            'filename': file.name,
                            'size': file.size
                        }

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='VIDEO_ADDED',
                        description=f'Uploaded new video: "{video.title}"',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_data=safe_request_data 
                    )
                except Exception as log_error:
                    print("Activity log failed (non-critical):", str(log_error))

                return Response({
                    'status': 'success',
                    'message': 'Video uploaded successfully.'
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            with transaction.atomic():
                vid = request.data.get('video_id')
                if not vid or not str(vid).isdigit():
                    return Response({'status': 'fail', 'message': 'video_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    video = YouTubeVideo.objects.get(id=int(vid), is_deleted=False)
                except YouTubeVideo.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'Video not found.'}, status=status.HTTP_404_NOT_FOUND)

                make_active = str(request.data.get('is_active', '')).lower() == 'true'
                if make_active:
                    active_count = YouTubeVideo.objects.filter(is_active=True, is_deleted=False).exclude(id=video.id).count()
                    if active_count >= 9:
                        return Response({'status': 'fail', 'message': 'Max 10 active videos allowed.'}, status=status.HTTP_400_BAD_REQUEST)
                    YouTubeVideo.objects.filter(is_active=True).exclude(id=video.id).update(is_active=False)

                serializer = VideoContentSerializer(
                    video,
                    data=request.data,
                    partial=True,
                    context={'request': request}
                )
                if not serializer.is_valid():
                    return Response({'status': 'fail', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

                serializer.save(modified_at=timezone.now())

                msg = "Video updated."
                if 'is_active' in request.data:
                    msg = "Video activated!" if serializer.instance.is_active else "Video deactivated."

                safe_request_data = {}
                for key, value in request.data.items():
                    if hasattr(value, 'name'):  
                        safe_request_data[key] = {
                            'filename': value.name,
                            'size': value.size,
                            'content_type': value.content_type
                        }
                    else:
                        safe_request_data[key] = value

                if 'thumbnail' in request.FILES:
                    file = request.FILES['thumbnail']
                    safe_request_data['thumbnail'] = {
                        'filename': file.name,
                        'size': file.size,
                        'content_type': file.content_type
                    }

                try:
                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='VIDEO_UPDATED',
                        description=f'{msg} - "{video.title}"',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_data=safe_request_data
                    )
                except Exception as log_error:
                    print("Activity log failed (non-critical):", log_error)

                return Response({
                    'status': 'success',
                    'message': msg
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    def delete(self, request):
        try:
            with transaction.atomic():
                vid = request.data.get('video_id')
                if not vid or not is_positive_integer(vid):
                    return Response({'status': 'fail', 'message': 'video_id required.'}, status=status.HTTP_400_BAD_REQUEST)

                video = YouTubeVideo.objects.filter(id=vid, is_deleted=False).first()
                if not video:
                    return Response({'status': 'fail', 'message': 'Video not found.'}, status=status.HTTP_404_NOT_FOUND)

                if video.is_active and YouTubeVideo.objects.filter(is_active=True, is_deleted=False).count() <= 1:
                    return Response({
                        'status': 'fail',
                        'message': 'Cannot delete the last active video.'
                    }, status=status.HTTP_404_NOT_FOUND)

                video.is_deleted = True
                video.is_active = False
                video.save()

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='VIDEO_DELETED',
                    description=f'Deleted video: {video.title}',
                    request_data=request.data
                )

                return Response({'status': 'success', 'message': 'Video deleted.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PublicYouTubeVideosView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            if request.META.get('HTTP_HOST') not in ALLOWED_DOMAINS:
                return Response({'status': 'error', 'message': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

            videos = YouTubeVideo.objects.filter(is_active=True, is_deleted=False)[:10]
            if not videos:
                return Response({'status': 'fail', 'message': 'No videos found.', 'data': []}, status=status.HTTP_404_NOT_FOUND)

            data = VideoContentSerializer(videos, many=True, context={
                'request': request,
                'exclude_fields': ['created_by', 'modified_at', 'is_deleted']
            }).data

            return Response({
                'status': 'success',
                'message': 'YouTube videos',
                'data': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)