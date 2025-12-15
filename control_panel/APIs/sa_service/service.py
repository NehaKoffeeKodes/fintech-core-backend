from ...views import*

class ServiceConfigManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            page_size = int(request.data.get('page_size', 10))
            page_num = int(request.data.get('page_number', 1))

            if page_size <= 0 or page_num <= 0:
                return Response({
                    'status': 'fail',
                    'message': 'page_size and page_number must be positive integers.'
                }, status=status.HTTP_400_BAD_REQUEST)

            svc_id = request.data.get('service_id')
            query = request.data.get('search')

            base_qs = SaCoreService.objects.filter(removed=False).order_by('-service_id')

            if svc_id:
                base_qs = base_qs.filter(service_id=svc_id)

            if query:
                base_qs = base_qs.filter(
                    Q(service_name__icontains=query) |
                    Q(details__icontains=query)
                )

            paginator = Paginator(base_qs, page_size)

            try:
                current_page = paginator.page(page_num)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Requested page does not exist.'
                }, status=status.HTTP_404_NOT_FOUND)

            serialized_data = SaCoreServiceSerializer(
                current_page.object_list,
                many=True,
                context={
                    'request': request,
                    'exclude_fields': ['added_on', 'modified_on', 'removed', 'modified_by', 'added_by']
                }
            ).data

            payload = {
                'total_pages': paginator.num_pages,
                'current_page': current_page.number,
                'total_items': paginator.count,
                'results': serialized_data
            }

            return Response({
                'status': 'success',
                'message': 'Services retrieved successfully.',
                'data': payload
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({
                'status': 'fail',
                'message': 'Invalid value for page_size or page_number.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                'status': 'error',
                'message': 'Server error occurred.',
                'details': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            svc_id = request.data.get('service_id')
            new_desc = request.data.get('description')

            save_api_log(request, "OwnAPI", request.data, {"status": "in_progress"}, None,
                                service_type="Core Service Update", client_override="tcpl_db")

            if not svc_id:
                return Response({
                    'status': 'fail',
                    'message': 'service_id is mandatory.'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                service = SaCoreService.objects.get(service_id=svc_id, removed=False)
            except SaCoreService.DoesNotExist:
                return Response({
                    'status': 'fail',
                    'message': 'Service not found.'
                }, status=status.HTTP_404_NOT_FOUND)

            updated = False

            if new_desc is not None:
                service.details = new_desc
                updated = True

            # If no description provided, assume toggle active/inactive
            if new_desc is None:
                service.inactive = not service.inactive
                updated = True

                # Sync with linked providers
                ServiceProvider.objects.filter(service=service).update(is_deactive=service.inactive)

            if updated:
                service.modified_on = timezone.now()
                service.modified_by = request.user
                service.save()

                action = "updated" if new_desc is not None else ("deactivated" if service.inactive else "activated")
                success_msg = f'Service {action} successfully.'

                save_api_log(request, "OwnAPI", request.data, {"status": "success", "message": success_msg},
                                    None, service_type="Core Service Update", client_override="tcpl_db")

                return Response({
                    'status': 'success',
                    'message': success_msg
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'No changes provided.'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            save_api_log(request, "OwnAPI", request.data, {"status": "failed", "error": str(exc)},
                                None, service_type="Core Service Update", client_override="tcpl_db")
            return Response({
                'status': 'error',
                'message': 'Update failed due to server error.',
                'details': str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)