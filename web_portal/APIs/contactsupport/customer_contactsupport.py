from ...views import*

class ContactSupportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get('action') == 'list' or 'page_size' in request.data:
            return self._list_tickets(request)
        else:
            return self._submit_ticket_from_admin(request)

    def _submit_ticket_from_admin(self, request):
        try:
            with transaction.atomic():
                serializer = ContactSupportSerializer(data=request.data)
                if serializer.is_valid():
                    ticket = serializer.save(handled_by=request.user)

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action='create',
                        description=f'Admin created support ticket for {ticket.customer_name}',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT'),
                        request_data=request.data
                    )

                    return Response({
                        'status': 'success',
                        'message': 'Support ticket raised successfully.'
                    }, status=status.HTTP_201_CREATED)

                return Response({
                    'status': 'fail',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _list_tickets(self, request):
        try:
            page_size = int(request.data.get('page_size', 10))
            page_no = int(request.data.get('page_number', 1))
            ticket_id = request.data.get('ticket_id')
            status_filter = request.data.get('status')
            search = request.data.get('search', '').strip()

            if page_size < 1 or page_no < 1:
                return Response({'status': 'fail', 'message': 'Invalid pagination.'}, status=status.HTTP_400_BAD_REQUEST)

            qs = ContactSupport.objects.filter(is_archived=False)

            if ticket_id:
                qs = qs.filter(ticket_id=ticket_id)
            if status_filter:
                qs = qs.filter(current_status=status_filter)
            if search:
                qs = qs.filter(
                    Q(customer_name__icontains=search) |
                    Q(customer_email__icontains=search) |
                    Q(issue_title__icontains=search)
                )

            paginator = Paginator(qs, page_size)
            page = paginator.get_page(page_no)

            serializer = ContactSupportSerializer(page, many=True)

            return Response({
                'status': 'success',
                'message': 'Support tickets loaded.',
                'data': {
                    'total': paginator.count,
                    'pages': paginator.num_pages,
                    'current': page.number,
                    'results': serializer.data
                }
            })

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            ticket_id = request.data.get('ticket_id')
            new_status = request.data.get('current_status')

            if not ticket_id or not new_status:
                return Response({'status': 'fail', 'message': 'ticket_id and status required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                ticket = ContactSupport.objects.select_for_update().get(
                    ticket_id=ticket_id, is_archived=False
                )
                old = ticket.get_current_status_display()
                ticket.current_status = new_status
                ticket.handled_by = request.user
                ticket.save()

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='update',
                    description=f'Admin created support ticket for {ticket.customer_name}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT'),
                    request_data=request.data
                )

                return Response({
                    'status': 'success',
                    'message': f'Ticket status updated to {ticket.get_current_status_display()}.'
                })

        except ContactSupport.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            ticket_id = request.data.get('ticket_id')
            if not ticket_id:
                return Response({'status': 'fail', 'message': 'ticket_id required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                ticket = ContactSupport.objects.get(ticket_id=ticket_id, is_archived=False)
                ticket.is_archived = True
                ticket.save()

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='delete',
                    description=f'Admin created support ticket for {ticket.customer_name}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT'),
                    request_data=request.data
                )

                return Response({
                    'status': 'success',
                    'message': 'Support ticket deleted successfully.'
                })

        except ContactSupport.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AddContactSupportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ContactSupportSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'status': 'success',
                    'message': 'Thank you! Your support ticket has been submitted. We’ll get back to you soon.'
                }, status=status.HTTP_201_CREATED)

            return Response({
                'status': 'fail',
                'message': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': 'Service temporarily down.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)