from ...views import*

ALLOWED_DOMAIN = getattr(settings, "ALLOWED_DOMAIN", ["127.0.0.1:8000", "localhost:8000", "localhost:3000"])

class NewsUpdateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            current_domain = request.META.get('HTTP_HOST')
            if current_domain not in ALLOWED_DOMAIN:
                return Response({
                    "status": "error",
                    "message": "Access denied from this domain."
                }, status=status.HTTP_403_FORBIDDEN)

            email_input = request.data.get("email", "").strip()
            if not email_input:
                return Response({
                    "status": "error",
                    "message": "Email is required."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                EmailValidator()(email_input)
            except ValidationError:
                return Response({
                    "status": "error",
                    "message": "Please provide a valid email address."
                }, status=status.HTTP_400_BAD_REQUEST)

            if NewsUpdateRecord.objects.filter(subscriber_email__iexact=email_input).exists():
                return Response({
                    "status": "error",
                    "message": "You're already subscribed!"
                }, status=status.HTTP_208_ALREADY_REPORTED)

            with transaction.atomic():
                name_part = email_input.split('@')[0].split('.')[0].title()
                subscriber = NewsUpdateRecord.objects.create(
                    subscriber_email=email_input,
                    full_name=name_part
                )

            return Response({
                "status": "success",
                "message": "Thank you! You've been subscribed successfully."
            }, status=status.HTTP_201_CREATED)

        except Exception as exc:
            return Response({
                "status": "error",
                "message": "Something went wrong. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ManageNewsUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request): 
        try:
            page_limit = request.data.get('page_size')
            page_num = request.data.get('page_number', 1)
            sort_order = request.data.get('order_by', 'desc')
            search_term = request.data.get('search')
            specific_id = request.data.get('record_id')

            if not page_limit or not str(page_limit).isdigit() or int(page_limit) < 1:
                return Response({"status": "fail", "message": "Valid page_size is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not str(page_num).isdigit() or int(page_num) < 1:
                page_num = 1

            base_qs = NewsUpdateRecord.objects.filter(is_removed=False)

            if specific_id:
                base_qs = base_qs.filter(record_id=specific_id)

            if search_term:
                base_qs = base_qs.filter(
                    Q(full_name__icontains=search_term) |
                    Q(subscriber_email__icontains=search_term)
                )

            base_qs = base_qs.order_by('-record_id') if sort_order != 'asc' else base_qs.order_by('record_id')

            paginator = Paginator(base_qs, page_limit)
            try:
                current_page = paginator.page(page_num)
            except EmptyPage:
                current_page = paginator.page(paginator.num_pages)

            serializer = NewsUpdateRecordSerializer(
                current_page.object_list,
                many=True,
                context={'exclude_fields': ['is_removed', 'modified_by']}
            )

            response_payload = {
                "total_pages": paginator.num_pages,
                "current_page": current_page.number,
                "total_records": paginator.count,
                "data": serializer.data
            }

            if not base_qs.exists():
                return Response({
                    "status": "success",
                    "message": "No subscribers found.",
                    "data": response_payload
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "success",
                "message": "Subscribers fetched successfully.",
                "data": response_payload
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "fail",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request): 
        try:
            record_id = request.data.get('record_id')
            new_email = request.data.get('email')
            suspend_status = request.data.get('is_suspended')

            instance = NewsUpdateRecord.objects.filter(record_id=record_id, is_removed=False).first()
            if not instance:
                return Response({"status": "error", "message": "Subscriber not found."}, status=status.HTTP_404_NOT_FOUND)

            active_count = NewsUpdateRecord.objects.filter(is_suspended=False, is_removed=False).count()
            if active_count <= 1 and not instance.is_suspended and suspend_status is True:
                return Response({
                    "status": "fail",
                    "message": "At least one active subscriber is required."
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = NewsUpdateRecordSerializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                if new_email:
                    new_email = new_email.strip().lower()
                    if NewsUpdateRecord.objects.exclude(record_id=record_id).filter(subscriber_email=new_email).exists():
                        return Response({"status": "error", "message": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)
                    name_from_email = new_email.split('@')[0].split('.')[0].title()
                    serializer.save(modified_by=request.user, full_name=name_from_email)
                else:
                    serializer.save(modified_by=request.user)

                action_msg = "Subscriber updated."
                if suspend_status is not None:
                    action_msg = "Subscriber deactivated." if suspend_status else "Subscriber activated."

                AdminActivityLog.objects.create(
                    user=request.user,                
                    action='update',
                    description=action_msg,
                    request_data=request.data,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )

                return Response({"status": "success", "message": action_msg}, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            record_id = request.data.get('record_id')
            if not record_id:
                return Response({"status": "fail", "message": "record_id is required."}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                subscriber = NewsUpdateRecord.objects.filter(record_id=record_id, is_removed=False).first()
                if not subscriber:
                    return Response({"status": "fail", "message": "Subscriber not found or already removed."}, status=status.HTTP_404_NOT_FOUND)

                subscriber.is_removed = True
                subscriber.save()

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='soft_delete',
                    description=f"Removed subscriber: {subscriber.subscriber_email}",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )

                return Response({
                    "status": "success",
                    "message": "Subscriber removed successfully."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)