from ...views import*


ALLOWED_DOMAINS = ["localhost:3000","127.0.0.1:8000",]

class CustomerTestimonialView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if 'page' in request.data or 'per_page' in request.data:
            return self.get_Testimonial_list(request)
        elif all(k in request.data for k in ['customer_name', 'customer_email', 'rating', 'feedback']):
            return self.add_new_Testimonial(request)
        return Response({
            'status': 'fail',
            'message': 'Invalid request format.'
        }, status=status.HTTP_400_BAD_REQUEST)

    def add_new_Testimonial(self, request):
        try:
            name = request.data['customer_name'].strip()
            email = request.data['customer_email'].lower().strip()
            rating = int(request.data['rating'])
            feedback = request.data['feedback'].strip()

            if Customer_Testimonial.objects.filter(customer_name__iexact=name, customer_email=email, is_hidden=False).exists():
                return Response({
                    'status': 'fail',
                    'message': 'A Testimonial from this customer already exists.'
                }, status=status.HTTP_400_BAD_REQUEST)

            active_count = Customer_Testimonial.objects.filter(is_approved=True, is_hidden=False).count()
            should_approve = active_count >= 10

            Customer_Testimonial.objects.create(
                customer_name=name,
                customer_email=email,
                rating=rating,
                feedback=feedback,
                is_approved=should_approve,
                added_by=request.user
            )

            AdminActivityLog.objects.create(
                user=request.user,
                action='Testimonial_CREATED',
                description=f'Added new customer Testimonial by {name}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_data=request.data
            )

            return Response({
                'status': 'success',
                'message': 'Testimonial submitted successfully and awaiting approval.' if not should_approve else 'Testimonial added and displayed instantly.'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_Testimonial_list(self, request):
        empty_payload = {"total": 0, "page": 1, "per_page": 10, "data": []}

        try:
            page = int(request.data.get('page', 1) or 1)
            page = max(page, 1)

            per_page = int(request.data.get('per_page', 10) or 10)
            per_page = max(per_page, 1)

            testimonial_id = request.data.get('Testimonial_id')
            keyword = request.data.get('search', '').strip()
            queryset = Customer_Testimonial.objects.filter(is_hidden=False).order_by('-id')

            if testimonial_id is not None:
                if not str(testimonial_id).isdigit():
                    return Response({'status': 'fail', 'message': 'Testimonial_id must be a number'}, status=400)
                queryset = queryset.filter(id=int(testimonial_id))

            if keyword:
                queryset = queryset.filter(
                    Q(customer_name__icontains=keyword) |
                    Q(customer_email__icontains=keyword) |
                    Q(feedback__icontains=keyword)
                )

            total_count = queryset.count()
            start = (page - 1) * per_page
            items = list(queryset[start:start + per_page])   
            
            if testimonial_id is not None and len(items) == 0:
                return Response({'status': 'fail', 'message': 'Testimonial not found'}, status=status.HTTP_404_NOT_FOUND)

            serializer = CustomerTestimonialSerializer(items, many=True)
            data_list = serializer.data  
            
            add_serial_numbers(data_list=data_list,page=page,page_size=per_page,order="desc")

            result = {
                'total': total_count,
                'page': page,
                'per_page': per_page,
                'data': data_list
            }

            return Response({
                'status': 'success',
                'message': 'Testimonials fetched',
                'result': result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'details': str(e),
                'result': empty_payload
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
    def patch(self, request):
        try:
            rid = request.data.get('testimonial_id') 
            if not rid or not is_positive_integer(rid):
                return Response({
                    'status': 'fail',
                    'message': 'Valid testimonial_id is required.'
                }, status=status.HTTP_400_BAD_REQUEST)

            testimonial = Customer_Testimonial.objects.filter(id=rid, is_hidden=False).first()
            
            if not testimonial:  
                return Response({
                    'status': 'fail',
                    'message': 'Testimonial not found.'
                }, status=status.HTTP_404_NOT_FOUND)

            success_message = "Testimonial updated successfully."
            fields_updated = False

            if 'customer_name' in request.data:
                testimonial.customer_name = request.data['customer_name'].strip()
                fields_updated = True

            if 'customer_email' in request.data:
                testimonial.customer_email = request.data['customer_email'].lower().strip()
                fields_updated = True

            if 'rating' in request.data:
                try:
                    rating = int(request.data['rating'])
                    if not 1 <= rating <= 5:
                        return Response({'status': 'fail', 'message': 'Rating must be between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)
                    testimonial.rating = rating
                    fields_updated = True
                except ValueError:
                    return Response({'status': 'fail', 'message': 'Rating must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

            if 'feedback' in request.data:
                testimonial.feedback = request.data['feedback'].strip()
                fields_updated = True

            if not fields_updated:
                active_count = Customer_Testimonial.objects.filter(is_approved=True, is_hidden=False).count()

                if not testimonial.is_approved and active_count >= 10:
                    return Response({
                        'status': 'fail',
                        'message': 'Maximum 10 testimonials can be displayed. Please hide one first.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if testimonial.is_approved and active_count <= 1:
                    return Response({
                        'status': 'fail',
                        'message': 'At least one testimonial must remain visible.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                testimonial.is_approved = not testimonial.is_approved
                success_message = "Testimonial is now LIVE on website!" if testimonial.is_approved else "Testimonial hidden from website."

            testimonial.updated_at = timezone.now()
            testimonial.save()

            AdminActivityLog.objects.create(
                user=request.user,
                action='TESTIMONIAL_UPDATED',
                description=f'Updated testimonial ID {rid} - {success_message}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_data=request.data
            )

            return Response({
                'status': 'success',
                'message': success_message
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            rid = request.data.get('testimonial_id')
            if not rid or not is_positive_integer(rid):
                return Response({'status': 'fail', 'message': 'testimonial_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                Testimonial = Customer_Testimonial.objects.select_for_update().get(id=rid, is_hidden=False)
                if Testimonial.is_approved and Customer_Testimonial.objects.filter(is_approved=True, is_hidden=False).count() <= 1:
                    return Response({
                        'status': 'fail',
                        'message': 'Cannot delete the last active Testimonial.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                Testimonial.is_hidden = True
                Testimonial.is_approved = False
                Testimonial.save()

                AdminActivityLog.objects.create(
                    user=request.user,
                    action='Testimonial_DELETED',
                    description=f'Soft deleted Testimonial ID {rid}',
                    request_data=request.data
                )

            return Response({'status': 'success', 'message': 'Testimonial removed successfully.'}, status=status.HTTP_200_OK)

        except Testimonial.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Testimonial not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicTestimonialsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            host = request.META.get('HTTP_HOST')
            if host not in ALLOWED_DOMAINS:
                return Response({'status': 'error', 'message': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

            Testimonials = Customer_Testimonial.objects.filter(is_approved=True, is_hidden=False)[:10]
            if not Testimonials:
                return Response({'status': 'fail', 'message': 'No Testimonials available.', 'data': []}, status=status.HTTP_404_NOT_FOUND)

            data = CustomerTestimonialSerializer(Testimonials, many=True, context={
                'exclude_fields': ['added_by', 'updated_at', 'is_hidden']
            }).data

            return Response({
                'status': 'success',
                'message': 'Customer Testimonials',
                'data': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)