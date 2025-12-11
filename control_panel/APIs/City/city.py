from ...views import*


class CityListView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    # permission_classes = [IsSuperAdmin | IsAdmin | IsDistributor | IsRetailer]
    permission_classes = [IsSuperAdmin | IsAdmin ]
    
    def post(self, request):
        try:
            if request.FILES.get('file'):
                return self._process_csv_upload(request)
            return self._get_Location_list(request)

        except Exception as exc:
            return Response({
                "success": False,
                "message": "An unexpected error occurred",
                "error": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _process_csv_upload(self, request):
        file_obj = request.FILES.get('file')

        if not file_obj or not file_obj.name.lower().endswith('.csv'):
            return Response({
                "success": False,
                "message": "Valid CSV file is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_content = file_obj.read().decode('utf-8')
            csv_reader = csv.DictReader(StringIO(file_content))
            created_count = 0

            for index, row in enumerate(csv_reader, start=2):
                cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k}

                serializer = LocationDataSerializer(data=cleaned_row, model=Location)
                if serializer.is_valid():
                    serializer.save()
                    created_count += 1
                else:
                    return Response({
                        "success": False,
                        "message": f"Error in row {index}",
                        "errors": serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "success": True,
                "message": f"{created_count} localities imported successfully."
            }, status=status.HTTP_201_CREATED)

        except UnicodeDecodeError:
            return Response({
                "success": False,
                "message": "Invalid CSV encoding. Please use UTF-8."
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "success": False,
                "message": "CSV processing failed",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_Location_list(self, request):
        try:
            search_term = request.data.get('search', '').strip()
            state_name = request.data.get('state_name', '').strip()
            region_id = request.data.get('state_id')
            page = int(request.data.get('page_number', 1))
            limit = request.data.get('page_size', '20')

            if state_name:
                try:
                    region_obj = Region.objects.get(name__iexact=state_name)
                    region_id = region_obj.region_id
                except Region.DoesNotExist:
                    return Response({
                        "success": False,
                        "message": "Region not found with given name."
                    }, status=status.HTTP_404_NOT_FOUND)

            localities = Location.objects.select_related('region').filter(active=True).order_by('title')

            if region_id:
                localities = localities.filter(region_id=region_id)
            if search_term:
                localities = localities.filter(title__icontains=search_term)

            total_records = localities.count()

            if str(limit) == "0":
                serializer = LocationDataSerializer(
                    localities,
                    many=True,
                    model=Location,
                    context={
                        'remove_fields': ['created_at', 'created_by', 'updated_at', 'updated_by', 'active']
                    }
                )
                response_payload = {
                    "total_pages": 1,
                    "current_page": 1,
                    "total_items": total_records,
                    "results": serializer.data
                }
                return Response({
                    "success": True,
                    "message": "All localities retrieved",
                    "data": response_payload
                }, status=status.HTTP_200_OK)

            paginator = Paginator(localities, limit)
            try:
                current_page = paginator.page(page)
            except EmptyPage:
                return Response({
                    "success": False,
                    "message": "Requested page is out of range.",
                    "data": {
                        "total_pages": paginator.num_pages,
                        "current_page": page,
                        "total_items": total_records,
                        "results": []
                    }
                }, status=status.HTTP_200_OK)

            serializer = LocationDataSerializer(
                current_page.object_list,
                many=True,
                model=Location,
                context={
                    'remove_fields': ['created_at', 'created_by', 'updated_at', 'updated_by', 'active']
                }
            )

            response_payload = {
                "total_pages": paginator.num_pages,
                "current_page": current_page.number,
                "total_items": total_records,
                "results": serializer.data
            }

            return Response({
                "success": True,
                "message": "Localities retrieved successfully",
                "data": response_payload
            }, status=status.HTTP_200_OK)

        except ValueError as ve:
            return Response({
                "success": False,
                "message": "Invalid pagination parameters",
                "error": str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "success": False,
                "message": "Failed to retrieve localities",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)