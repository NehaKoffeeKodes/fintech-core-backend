from ...views import*
import csv
from io import StringIO



class CityListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if 'file' in request.FILES:
            return self.import_locations_from_csv(request)
        return self.retrieve_locations(request)

    @transaction.atomic
    def import_locations_from_csv(self, request):
        try:
            file = request.FILES['file']
            if not file.name.lower().endswith('.csv'):
                return Response({'ok': False, 'msg': 'Only CSV files allowed.'}, status=status.HTTP_400_BAD_REQUEST)

            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(StringIO(content))

            created_count = 0
            for row in reader:
                row
                cleaned = {k.strip(): v.strip() for k, v in row.items() if v}
                
                serializer = CityLocationSerializer(data=cleaned, context={'request': request})
                if serializer.is_valid():
                    serializer.save()
                    created_count += 1
                else:
                    return Response({
                        'ok': False,
                        'msg': 'Invalid data in CSV row.',
                        'errors': serializer.errors,
                        'row': cleaned
                    }, status=status.HTTP_400_BAD_REQUEST)

            AdminActivityLog.objects.create(
                user=request.user,
                action='BULK_LOCATION_IMPORT',
                description=f'Imported {created_count} locations via CSV',
                request_data={'file': file.name}
            )

            return Response({
                'ok': True,
                'msg': f'{created_count} locations imported successfully!'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'ok': False, 'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve_locations(self, request):
        try:
            page = int(request.data.get('page_no', 1))
            size = int(request.data.get('page_size', 20))
            district_id = request.data.get('district_id')
            city_search = request.data.get('search', '').strip()
            district_name = request.data.get('district_name')

            if page < 1 or size < 1:
                return Response({'ok': False, 'msg': 'Invalid pagination.'}, status=status.HTTP_400_BAD_REQUEST)

            qs = CityLocation.objects.select_related('district').order_by('city_name')

            if district_name:
                try:
                    district = District.objects.get(district_name__icontains=district_name, is_removed=False)
                    qs = qs.filter(district=district)
                except District.DoesNotExist:
                    return Response({'ok': False, 'msg': 'District not found.'}, status=status.HTTP_404_NOT_FOUND)

            if district_id:
                if not is_positive_integer(district_id):
                    return Response({'ok': False, 'msg': 'Invalid district_id.'}, status=status.HTTP_400_BAD_REQUEST)
                qs = qs.filter(district_id=district_id)

            if city_search:
                qs = qs.filter(city_name__icontains=city_search)

            total = qs.count()

            if size == 0 or size is None: 
                serializer = CityLocationSerializer(
                    qs, many=True,
                    context={'request': request, 'exclude_fields': ['created_at', 'updated_at', 'created_by', 'updated_by', 'is_removed']}
                )
                return Response({
                    'ok': True,
                    'msg': 'All locations',
                    'total': total,
                    'data': serializer.data
                }, status=status.HTTP_200_OK)

            paginator = Paginator(qs, size)
            try:
                page_data = paginator.page(page)
            except EmptyPage:
                return Response({'ok': False, 'msg': 'Page out of range.'}, status=status.HTTP_404_NOT_FOUND)

            serializer = CityLocationSerializer(
                page_data.object_list, many=True,
                context={'request': request, 'exclude_fields': ['created_at', 'updated_at', 'created_by', 'updated_by', 'is_removed']}
            )

            add_serial_numbers(page, size, serializer.data, "asc")

            payload = {
                'pages': paginator.num_pages,
                'current': page_data.number,
                'count': total,
                'list': serializer.data
            }

            return Response({
                'ok': True,
                'msg': 'Locations fetched.',
                'result': payload
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'ok': False, 'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)