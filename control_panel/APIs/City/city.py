from ...views import *


class CityAPIView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin | IsDistributor | IsRetailer]

    def post(self, request, *args, **kwargs):
        try:
            if 'file' in request.FILES:
                uploaded_file = request.FILES['file']

                if not uploaded_file.name.lower().endswith('.csv'):
                    return Response(
                        {"error": "Only CSV files are allowed."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                file_content = uploaded_file.read().decode('utf-8')
                csv_reader = csv.DictReader(StringIO(file_content))

                for row_index, row in enumerate(csv_reader, start=1):
                    city_serializer = CitySerializer(data=row)
                    if city_serializer.is_valid():
                        city_serializer.save()
                    else:
                        error_msg = f"Validation error in row {row_index}: {city_serializer.errors}"
                        return Response(
                            {"error": error_msg},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                return Response(
                    {"message": "Cities uploaded and processed successfully via CSV."},
                    status=status.HTTP_201_CREATED
                )

            else:
                return self.retrieve_cities(request)

        except Exception as e:
            return Response(
                {"status": "error", "message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve_cities(self, request):
        try:
            page_num = request.data.get('page_number', 1)
            page_sz = request.data.get('page_size', 20)
            state_identifier = request.data.get('state_id')
            search_city = request.data.get('search')
            state_search_name = request.data.get('state_name')

            try:
                page_num = int(page_num)
                page_sz = int(page_sz)
                if page_num < 1:
                    raise ValueError
                if page_sz < 0:
                    raise ValueError
            except (TypeError, ValueError):
                return Response(
                    {"status": "fail", "message": "page_number must be >= 1 and page_size must be >= 0"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if state_search_name:
                try:
                    state_obj = Region.objects.get(state_name__iexact=state_search_name.strip())
                    state_identifier = state_obj.id
                except Region.DoesNotExist:
                    return Response(
                        {"status": "fail", "message": "State with given name not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )

            city_queryset = Location.objects.all().order_by('city_name')

            if state_identifier:
                city_queryset = city_queryset.filter(state_id=state_identifier)
            if search_city:
                city_queryset = city_queryset.filter(city_name__icontains=search_city.strip())

            if str(page_sz) == "0":
                serializer = CitySerializer(
                    city_queryset,
                    many=True,
                    context={
                        'request': request,
                        'exclude_fields': ["created_at", "is_active", "create_by", "update_at", "update_by", "state_id"]
                    }
                )
                response_payload = {
                    'total_pages': 1,
                    'current_page': 1,
                    'total_items': city_queryset.count(),
                    'results': serializer.data
                }
                return Response(
                    {"status": "success", "message": "All City Data Retrieved", "data": response_payload},
                    status=status.HTTP_200_OK
                )

            paginator = Paginator(city_queryset, page_sz)
            try:
                current_page = paginator.page(page_num)
            except EmptyPage:
                return Response(
                    {"status": "fail", "message": "Requested page does not exist."},
                    status=status.HTTP_404_NOT_FOUND
                )

            if not current_page.object_list.exists():
                empty_payload = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                return Response(
                    {"status": "success", "message": "No cities found matching criteria.", "data": empty_payload},
                    status=status.HTTP_200_OK
                )

            serialized_data = CitySerializer(
                current_page.object_list,
                many=True,
                context={
                    'request': request,
                    'exclude_fields': ["created_at", "is_active", "create_by", "update_at", "update_by", "state_id"]
                }
            )

            paginated_payload = {
                'total_pages': paginator.num_pages,
                'current_page': current_page.number,
                'total_items': paginator.count,
                'results': serialized_data.data
            }

            return Response(
                {"status": "success", "message": "City Data Retrieved Successfully", "data": paginated_payload},
                status=status.HTTP_200_OK
            )

        except ValidationError as ve:
            return Response(
                {"status": "fail", "message": str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Region.DoesNotExist:
            return Response(
                {"status": "fail", "message": "Referenced state does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )