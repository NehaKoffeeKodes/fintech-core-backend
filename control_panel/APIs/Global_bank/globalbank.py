from ...views import*


class GlobalBankInstitutionView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        try:
            if 'full_name' in request.data and 'short_code' in request.data:
                return self.add_new_institution(request)
            elif request.data.get('download_blank'):
                return self.download_template(request)
            elif request.data.get('export_data'):
                return self.export_all_data(request)
            elif 'excel_upload' in request.FILES:
                return self.upload_and_import(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.list_institutions(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_new_institution(self, request):
        try:
            name = request.data.get('full_name')
            code = request.data.get('short_code')
            ifsc = request.data.get('universal_ifsc')

            GlobalBankInstitution.objects.create(
                full_name=name,
                short_code=code,
                universal_ifsc=ifsc
            )
            return Response({'status': 'success', 'message': 'Institution added successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def download_template(self, request):
        try:
            columns = ['Bank Name', 'Bank Short Name', 'Bank Global IFSC', 'Fino ID', 'NSDL ID', 'Airtel ID', 'Payout', 'Fund Request', 'Is Deactive']
            file_url = create_template_excel(columns)
            full_link = f"https://{request.get_host()}{file_url}"
            return Response({'status': 'success', 'message': 'Template ready', 'data': full_link}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def export_all_data(self, request):
        try:
            mapping = {
                'institution_id': 'Bank ID',
                'full_name': 'Bank Name',
                'short_code': 'Bank Short Name',
                'universal_ifsc': 'Bank Global IFSC',
                'fino_mapping': 'Fino ID',
                'nsdl_mapping': 'NSDL ID',
                'airtel_mapping': 'Airtel ID',
                'supports_payout': 'Payout',
                'supports_funding': 'Fund Request',
                'is_inactive': 'Is Deactive',
            }
            qs = GlobalBankInstitution.objects.all().order_by('institution_id')
            url = export_institutions_to_excel(qs, mapping, "institutions_list")
            full_url = f"https://{request.get_host()}{url}"
            return Response({'status': 'success', 'message': 'Export completed', 'data': full_url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def upload_and_import(self, request):
        try:
            excel_file = request.FILES.get('excel_upload')
            if not excel_file:
                return Response({'status': 'fail', 'message': 'No file received'}, status=status.HTTP_400_BAD_REQUEST)

            count = process_bank_import_from_excel(excel_file)
            return Response({'status': 'success', 'message': f'{count} institutions imported'}, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response({'status': 'fail', 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_institutions(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            query = request.data.get('search', '').strip()
            funding = request.data.get('supports_funding')
            payout = request.data.get('supports_payout')

            qs = GlobalBankInstitution.objects.all().order_by('-institution_id')

            if funding is not None:
                qs = qs.filter(supports_funding=True)
            if payout is not None:
                qs = qs.filter(supports_payout=True)
            if query:
                qs = qs.filter(
                    Q(full_name__icontains=query) |
                    Q(short_code__icontains=query)
                )

            paginator = Paginator(qs, size)
            try:
                page_data = paginator.page(page)
            except EmptyPage:
                page_data = paginator.page(paginator.num_pages)

            serializer = GlobalBankInstitutionSerializer(page_data, many=True)
            result = serializer.data

            for item in result:
                item['fino_mapping'] = item['fino_mapping'].get('bank_id') if isinstance(item['fino_mapping'], dict) else None
                item['nsdl_mapping'] = item['nsdl_mapping'].get('bank_id') if isinstance(item['nsdl_mapping'], dict) else None
                item['airtel_mapping'] = item['airtel_mapping'].get('bank_id') if isinstance(item['airtel_mapping'], dict) else None

            return Response({
                'status': 'success',
                'message': 'Data fetched',
                'data': {
                    'total_pages': paginator.num_pages,
                    'current_page': page_data.number,
                    'total_count': paginator.count,
                    'results': result
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            inst_id = request.data.get('institution_id')
            if not inst_id:
                return Response({'status': 'fail', 'message': 'Institution ID required'}, status=status.HTTP_400_BAD_REQUEST)

            institution = GlobalBankInstitution.objects.get(institution_id=inst_id)

            updated = False
            msg = ""

            fields_to_update = ['full_name', 'short_code', 'universal_ifsc']
            json_fields = ['fino_mapping', 'nsdl_mapping', 'airtel_mapping']

            for field in fields_to_update:
                value = request.data.get(field)
                if value is not None:
                    setattr(institution, field, value)
                    updated = True

            for jfield in json_fields:
                value = request.data.get(jfield)
                if value is not None:
                    institution.__setattr__(jfield, {"bank_id": value})
                    updated = True

            if request.data.get('supports_payout') is not None:
                institution.supports_payout = not institution.supports_payout
                msg = f"Payout {'enabled' if institution.supports_payout else 'disabled'}"
            elif request.data.get('supports_funding') is not None:
                institution.supports_funding = not institution.supports_funding
                msg = f"Funding {'enabled' if institution.supports_funding else 'disabled'}"
            else:
                institution.is_inactive = not institution.is_inactive
                msg = f"Institution {'deactivated' if institution.is_inactive else 'activated'}"

            if updated or msg:
                institution.save()

            final_msg = msg or "Institution details updated successfully"
            return Response({'status': 'success', 'message': final_msg}, status=status.HTTP_200_OK)

        except GlobalBankInstitution.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Institution not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)