from ...views import*



class LatestAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get('fetch') == 'list' or 'page_size' in request.data:
            return self._get_news_list(request)
        else:
            return self._add_news(request)

    def _add_news(self, request):
        try:
            with transaction.atomic():
                uploaded_files = request.FILES.getlist('documents')
                saved_paths = self._handle_file_uploads(uploaded_files)

                mutable_data = request.data.copy()
                mutable_data['documents'] = saved_paths

                serializer = LatestAnnouncementSerializer(data=mutable_data, context={'request': request})
                if serializer.is_valid():
                    news = serializer.save(posted_by=request.user)

                    AdminActivityLog.objects.create(
                        table_id=news.news_id,
                        table_name='Latest_announcement',
                        ua_action='create',
                        ua_description=f'Added new update: {news.headline}',
                        created_by=request.user,
                        request_data=request.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Latest news published successfully.'
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            return Response({
                'status': 'error',
                'message': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_file_uploads(self, files):
        paths = []
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'news_documents')
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            if file.size > 15 * 1024 * 1024: 
                raise ValueError("Each document must be under 15 MB.")
            
            safe_name = "".join(c for c in file.name if c.isalnum() or c in "._- ")
            file_path = os.path.join('news_documents', safe_name)
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)

            with open(full_path, 'wb+') as f:
                for chunk in file.chunks():
                    f.write(chunk)
            paths.append(file_path)

        return paths

    def _get_news_list(self, request):
        try:
            page_size = int(request.data.get('page_size', 10))
            page_num = int(request.data.get('page_number', 1))
            news_id = request.data.get('news_id')
            keyword = request.data.get('keyword', '').strip()
            show_hidden = request.data.get('include_hidden', 'false').lower() == 'true'

            if page_size < 1 or page_num < 1:
                return Response({'status': 'fail', 'message': 'Invalid pagination values.'}, status=status.HTTP_400_BAD_REQUEST)

            queryset = Latest_announcement.objects.filter(is_removed=False)
            if not show_hidden:
                queryset = queryset.filter(is_hidden=False)
            if news_id:
                queryset = queryset.filter(news_id=news_id)
            if keyword:
                queryset = queryset.filter(
                    Q(headline__icontains=keyword) | Q(details__icontains=keyword)
                )

            paginator = Paginator(queryset, page_size)
            page = paginator.get_page(page_num)

            serializer = LatestAnnouncementSerializer(
                page.object_list, many=True, context={'request': request}
            )

            return Response({
                'status': 'success',
                'message': 'News updates retrieved.',
                'data': {
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'current_page': page.number,
                    'has_next': page.has_next(),
                    'has_previous': page.has_previous(),
                    'results': serializer.data
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            news_id = request.data.get('news_id')
            if not news_id:
                return Response({'status': 'fail', 'message': 'news_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                try:
                    news = Latest_announcement.objects.select_for_update().get(
                        news_id=news_id, is_removed=False
                    )
                except Latest_announcement.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'News update not found.'}, status=status.HTTP_404_NOT_FOUND)

                if len(request.data) == 1 or (len(request.data) == 2 and 'news_id' in request.data):
                    news.is_hidden = not news.is_hidden
                    news.save()
                    action = 'hide' if news.is_hidden else 'unhide'
                    msg = f'News update {"archived" if news.is_hidden else "made live"} successfully.'

                    AdminActivityLog.objects.create(
                        table_id=news.news_id, table_name='Latest_announcement',
                        ua_action=action, ua_description=msg,
                        created_by=request.user
                    )
                    return Response({'status': 'success', 'message': msg})

                files = request.FILES.getlist('documents')
                if files:
                    new_paths = self._handle_file_uploads(files)
                    current = news.documents or []
                    news.documents = current + new_paths

                serializer = LatestAnnouncementSerializer(
                    news, data=request.data, partial=True, context={'request': request}
                )
                if serializer.is_valid():
                    serializer.save()

                    AdminActivityLog.objects.create(
                        table_id=news.news_id, table_name='Latest_announcement',
                        ua_action='update', ua_description='Updated news content',
                        created_by=request.user, request_data=request.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'News update modified successfully.'
                    })

                return Response({'status': 'fail', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            news_id = request.data.get('news_id')
            if not news_id:
                return Response({'status': 'fail', 'message': 'news_id required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                news = Latest_announcement.objects.get(news_id=news_id, is_removed=False)
                news.is_removed = True
                news.save()

                AdminActivityLog.objects.create(
                    table_id=news.news_id, table_name='Latest_announcement',
                    ua_action='delete', ua_description='Removed news update',
                    created_by=request.user
                )

                return Response({
                    'status': 'success',
                    'message': 'News update removed permanently.'
                })

        except Latest_announcement.DoesNotExist:
            return Response({'status': 'fail', 'message': 'News not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)