from ...views import *


def format_validation_errors(error_dict):
    error_list = []
    for field, messages in error_dict.items():
        for msg in messages:
            error_list.append(f"{field}: {msg}")
    return " | ".join(error_list)


class AdminManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data

            if 'page_number' in data and 'page_size' in data:
                return self.handle_list_request(request)

            elif 'name' in data and 'mobile_number' in data:
                return self.register_new_admin(request)

            return Response(
                {'status': 'error', 'message': 'Invalid request format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as exc:
            save_api_log(
                request, "InternalAPI", request.data,
                {"status": "error", "error": str(exc)},
                service_type ="Admin Creation", client_override ="fintach_backend_db"
            )
            return Response(
                {'status': 'error', 'message': 'Unexpected server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def register_new_admin(self, request):
        input_data = request.data.copy()

        try:
            admin_name = input_data.get('name')
            mobile_number = input_data.get('mobile_number')
            email = input_data.get('email', '')

            save_api_log(
                request, "InternalAPI", input_data,
                {"status": "processing"},
                service_type ="Admin Registration", client_override ="fintach_backend_db"
            )

            def save_uploaded_file(uploaded_file, folder):
                if not uploaded_file:
                    raise ValidationError("Uploaded file missing")

                if uploaded_file.size > 10 * 1024 * 1024:
                    raise ValidationError("File exceeds 10MB limit")

                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                name, ext = os.path.splitext(uploaded_file.name)
                safe_name = name.replace(" ", "_")

                relative_path = os.path.join(
                    folder, f"{safe_name}_{timestamp}{ext}"
                )
                full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                try:
                    with open(full_path, 'wb') as destination:
                        for chunk in uploaded_file.chunks():
                            destination.write(chunk)
                finally:
                    uploaded_file.close()

                return relative_path
            
            mandatory_docs = DocumentTemplate.objects.filter(
                mandatory=True,
                active=True,
                soft_deleted=False
            )

            required_slugs = [d.document_slug for d in mandatory_docs]

            uploaded_kyc_paths = {}
            for slug in required_slugs:
                if slug in request.FILES:
                    uploaded_kyc_paths[slug] = save_uploaded_file(
                        request.FILES[slug], 'kyc_documents'
                    )

            db_identifier = f"admin_db_{admin_name.lower().replace(' ', '_')}"

            with transaction.atomic():
                admin_serializer = AdminSerializer(
                    data=input_data, context={'request': request}
                )

                if not admin_serializer.is_valid():
                    return Response(
                        {
                            'status': 'fail',
                            'message': format_validation_errors(
                                admin_serializer.errors
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                new_admin = admin_serializer.save(created_by=request.user)
                new_admin.docs_files = uploaded_kyc_paths
                new_admin.db_name = db_identifier
                new_admin.charges.set(
                    Charges.objects.filter(charge_category="to_proprovide")
                )
                new_admin.save()

                input_data['admin_id'] = new_admin.pk
                contract_serializer = AdminContractSerializer(
                    data=input_data,
                    context={'request': request, 'admin_instance': new_admin}
                )

                if not contract_serializer.is_valid():
                    return Response(
                        {
                            'status': 'fail',
                            'message': format_validation_errors(
                                contract_serializer.errors
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                contract_instance = contract_serializer.save(created_by=request.user)

                try:
                    log_user = request.user if (hasattr(request, 'user') and request.user.is_authenticated) else None
                    
                    admin_id = contract_instance.admin.id if contract_instance.admin else None
                    
                    AdminActivityLog.objects.create(
                        user=log_user,
                        action="CREATE",
                        description="Admin contract created successfully",
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT'),
                        request_data={
                            "admin_id": admin_id,
                            "contract_id": contract_instance.contract_id,
                            "base_amount": str(contract_instance.base_amount or 0),
                            "gst_component": str(contract_instance.gst_component or 0),
                            "contract_status": contract_instance.contract_status,
                            "response": contract_serializer.data
                        }
                    )
                except Exception as e:
                    print("Failed to create activity log:", str(e))  
                    
            if not setup_admin_database(db_identifier):
                raise Exception("Database creation failed")

            if not run_migrations_for_admin(db_identifier):
                raise Exception("Migration failed")

            portal_user = PortalUser.objects.using(db_identifier).create(
                full_name=admin_name,
                email_address=email.lower().strip() if email else None,
                mobile_number=mobile_number,
                member_type='SUPER_ADMIN',
                account_status='PENDING_REVIEW',
                registered_by=None,
            )

            master_data(db_identifier)  
            
            PortalUserInfo.objects.using(db_identifier).create(
                user_account=portal_user,
                aadhaar_number=new_admin.aadhaar or None,
                pan_number=new_admin.pan or None,
                supporting_documents=list(uploaded_kyc_paths.values()),
                state_ref_id=new_admin.registered_state_id,
                city_ref_id=new_admin.registered_city_id,
                pincode=new_admin.pin_code or None,
            )

            PortalUserBalance.objects.using(db_identifier).create(
                user=portal_user,           
                primary_balance=0.000      
            )

            save_api_log(
                request, "InternalAPI", input_data,
                {"status": "success", "admin_id": new_admin.pk},
                service_type ="Admin Registration", client_override ="fintach_backend_db"
            )

            return Response(
                {
                    'status': 'success',
                    'message': 'Admin registered successfully',
                    'admin_id': new_admin.pk
                },
                status=status.HTTP_201_CREATED
            )

        except ValidationError as ve:
            return Response(
                {'status': 'fail', 'message': str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            save_api_log(
                request, "InternalAPI", input_data,
                {"status": "error", "message": str(e)},
                service_type ="Admin Registration", client_override ="fintach_backend_db"
            )
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def handle_list_request(self, request):
        try:
            payload = request.data
            page_num = int(payload.get('page_number', 1))
            page_size = int(payload.get('page_size', 10))

            queryset = Admin.objects.filter(
                is_deleted=False
            ).order_by('-pk')

            search = payload.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(company_name__icontains=search)
                )

            paginator = Paginator(queryset, page_size)
            page = paginator.get_page(page_num)

            serializer = AdminSerializer(
                page, many=True, context={'request': request}
            )

            return Response(
                {
                    'status': 'success',
                    'data': {
                        'total_items': paginator.count,
                        'total_pages': paginator.num_pages,
                        'current_page': page_num,
                        'results': serializer.data
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception:
            return Response(
                {'status': 'error', 'message': 'Fetch failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        admin_id = request.data.get('admin_id')
        new_status = request.data.get('admin_status')
        reason = request.data.get('status_reason')

        try:
            admin = Admin.objects.get(admin_id=admin_id)
            portal_user = PortalUser.objects.using(
                admin.db_name
            ).get(pu_mobile_number=admin.mobile_number)

            portal_user.pu_status = new_status
            portal_user.pu_reason = reason
            portal_user.save(using=admin.db_name)

            admin.admin_status = new_status
            admin.reason = reason
            admin.save()

            return Response(
                {'status': 'success', 'message': 'Status updated'},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        admin_id = request.data.get('admin_id')

        try:
            admin = Admin.objects.get(admin_id=admin_id)
            admin.is_deactive = not admin.is_deactive
            admin.save()

            return Response(
                {'status': 'success', 'message': 'Status toggled'},
                status=status.HTTP_200_OK
            )

        except Admin.DoesNotExist:
            return Response(
                {'status': 'fail', 'message': 'Admin not found'},
                status=status.HTTP_404_NOT_FOUND
            )
