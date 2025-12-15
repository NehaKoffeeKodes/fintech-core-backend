from ...views import *

class StateAPIView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin | IsDistributor | IsRetailer]

    def post(self, request, *args, **kwargs):
        try:
            if 'file' in request.FILES:
                uploaded_csv = request.FILES['file']

                if not uploaded_csv.name.lower().endswith('.csv'):
                    return Response(
                        {"error": "Invalid file format. Only CSV files are accepted."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                file_content = uploaded_csv.read().decode('utf-8-sig')
                csv_reader = csv.DictReader(StringIO(file_content))

                row_count = 0
                for row_num, row_data in enumerate(csv_reader, start=1):
                    row_count += 1
                    region_serializer = StateSerializer(data=row_data)

                    if region_serializer.is_valid():
                        region_serializer.save()
                    else:
                        error_detail = {
                            "row_number": row_num,
                            "errors": region_serializer.errors
                        }
                        return Response(
                            {"error": "Validation failed during CSV upload", "details": error_detail},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                if row_count == 0:
                    return Response(
                        {"error": "Uploaded CSV file is empty."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                return Response(
                    {"message": "Regions successfully imported from CSV file."},
                    status=status.HTTP_201_CREATED
                )
            else:
                return self.get_region_list(request)

        except Exception as e:
            return Response(
                {"status": "error", "message": f"Unexpected error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_region_list(self, request):
        try:
            search_term = request.data.get('state_name', '').strip()
            regions_qs = Region.objects.all().order_by('name')

            if search_term:
                regions_qs = regions_qs.filter(name__icontains=search_term) 

            serializer = StateSerializer(
                regions_qs,
                many=True,
                context={
                    'request': request,
                    'exclude_fields': ["added_on", "added_by", "modified_on", "modified_by", "status"]  
                }
            )

            response_payload = {
                'status': 'success',
                'message': 'Region Data Retrieved Successfully',
                'data': serializer.data
            }

            if not serializer.data:
                response_payload = {
                    'status': 'success',
                    'message': 'No regions found matching the criteria.',
                    'data': []
                }

            return Response(response_payload, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"status": "error", "message": f"Server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )