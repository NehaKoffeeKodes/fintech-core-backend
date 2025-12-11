from site import abs_paths
from admin_hub.models import PortalUserLog
from control_panel import master_data
from utils.database.admin_database_manage import run_migrations_for_admin, setup_admin_database
from ...views import *


def build_error_response(errors):
    """Helper to convert serializer errors into clean string"""
    if isinstance(errors, dict):
        return " | ".join([f"{k}: {', '.join(v)}" for k, v in errors.items()])
    return str(errors)


class AdminManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data

            if 'page_number' in data or 'page_size' in data:
                return self.list_admins(request)

            if 'name' in data and 'contact_no' in data:
                return self.create_admin(request)

            return Response(
                {"status": "error", "message": "Invalid request format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as exc:
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_admin(self, request):
        try:
            with transaction.atomic():
                data = request.data.copy()
                name = data.get('name')
                contact_no = data.get('contact_no')
                email = data.get('email', '')

                db_name = f"admin_db_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
                kyc_paths = self._handle_document_uploads(data, 'kyc_docs/')
                if not kyc_paths and DocumentTemplate.objects.filter(is_required=True).exists():
                    raise ValidationError("Required KYC documents are missing.")

                serializer = AdminSerializer(
                    data=data,
                    context={'request': request}
                )
                serializer.is_valid(raise_exception=True)
                admin = serializer.save(
                    created_by=request.user,
                    db_name=db_name,
                    document_bundle=kyc_paths
                )
                
                default_charges = ChargeRule.objects.filter(
                    charge_beneficiary='admin_SHARE'
                ).values_list('pk', flat=True)
                admin.assigned_charges = list(default_charges)
                admin.save()

                contract_data = {
                    "admin": admin.pk,
                    "base_amount": data.get('contract_amount'),
                    "contract_status": "DRAFT",
                    "signed_document": data.get('agreement_document')
                }
                contract_serializer = AdminContractSerializer(
                    data=contract_data,
                    context={'request': request}
                )
                contract_serializer.is_valid(raise_exception=True)
                contract_serializer.save(created_by=request.user)

                self.log_activity(
                    table_name='admin_profile',
                    action='create',
                    description=f"Created admin: {admin.business_name}",
                    instance_id=admin.pk,
                    request=request
                )

            if not setup_admin_database(db_name):
                raise Exception("Failed to create tenant database")

            if not run_migrations_for_admin(db_name):
                raise Exception("Migration failed for tenant database")

            portal_user = PortalUser.objects.using(db_name).create(
                full_name=name,
                phone=contact_no,
                email=email,
                role='admin_ADMIN',
                is_active=True
            )

            PortalUserBalance.objects.using(db_name).create(
                user=portal_user,
                balance=Decimal('0.00')
            )

            master_data(db_name)

            return Response({
                "status": "success",
                "message": "admin onboarded successfully",
                "admin_id": admin.pk,
                "database": db_name
            }, status=status.HTTP_201_CREATED)

        except ValidationError as ve:
            return Response({"status": "fail", "message": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_admins(self, request):
        try:
            queryset = ServiceProvider.objects.filter(is_deleted=False)
            search = request.data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(business_name__icontains=search) |
                    Q(email_id__icontains=search) |
                    Q(mobile__icontains=search)
                )

            is_active = request.data.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=bool(is_active))
                
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))

            paginator = Paginator(queryset.order_by('-joined_on'), size)
            page_obj = paginator.get_page(page)

            serializer = AdminSerializer(
                page_obj.object_list,
                many=True,
                context={'request': request}
            )
            results = []
            for item in serializer.data:
                if item.get('db_name'):
                    try:
                        switch_to_database(item['db_name'])
                        wallet = PortalUserBalance.objects.using(item['db_name']).first()
                        item['current_balance'] = float(wallet.balance) if wallet else 0.0
                    except:
                        item['current_balance'] = 0.0
                results.append(item)

            return Response({
                "status": "success",
                "data": {
                    "total": paginator.count,
                    "pages": paginator.num_pages,
                    "current_page": page_obj.number,
                    "results": results
                }
            })

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

    def put(self, request):
        try:
            data = request.data

            if 'admin_id' in data:
                if 'new_status' in data:
                    return self.update_admin_status(request)
                else:
                    return self.update_admin_profile(request)

            return Response({"status": "error", "message": "Invalid update request"}, status=400)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

    def update_admin_status(self, request):
        admin_id = request.data.get('admin_id')
        new_status = request.data.get('new_status')  
        reason = request.data.get('reason')

        try:
            admin = ServiceProvider.objects.get(pk=admin_id)
            old_status = "Active" if admin.is_active else "Suspended"

            admin.is_active = (new_status == "ACTIVE")
            admin.suspension_reason = reason
            admin.save()

            if admin.db_name:
                try:
                    switch_to_database(admin.db_name)
                    PortalUser.objects.using(admin.db_name).filter(role='admin_ADMIN').update(
                        is_active=admin.is_active
                    )
                except:
                    pass  

            self._log_activity('admin_profile', 'status_change', f"Status: {old_status} → {new_status}", admin.pk, request)

            return Response({
                "status": "success",
                "message": f"admin {'activated' if admin.is_active else 'suspended'} successfully"
            })

        except ServiceProvider.DoesNotExist:
            return Response({"status": "fail", "message": "admin not found"}, status=404)

    def update_admin_profile(self, request):
        try:
            with transaction.atomic():
                admin_id = request.data.get('admin_id')
                admin = ServiceProvider.objects.get(pk=admin_id).first()

                if not admin:
                    return Response({"status": "fail", "message": "admin not found"}, status=404)

                if any(f in request.FILES for f in ['pan_copy', 'aadhaar_front', 'gst_certificate']):
                    paths = self._handle_document_uploads(request.data, 'updated_docs/')
                    admin.document_bundle.update(abs_paths)
                    admin.save()

                serializer = AdminSerializer(
                    admin, data=request.data, partial=True, context={'request': request}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response({
                    "status": "success",
                    "message": "admin profile updated successfully"
                })

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

    def delete(self, request):
        try:
            admin_id = request.data.get('admin_id')
            if not admin_id:
                return Response({"status": "fail", "message": "admin_id required"}, status=400)

            admin = ServiceProvider.objects.get(pk=admin_id)
            admin.is_active = not admin.is_active
            admin.save()

            if admin.db_name:
                switch_to_database(admin.db_name)
                PortalUser.objects.using(admin.db_name).filter(role='admin_ADMIN').update(
                    is_active=admin.is_active
                )
                PortalUserLog.objects.using(admin.db_name).update(token_expired=not admin.is_active)

            action = "blocked" if not admin.is_active else "unblocked"
            self._log_activity('admin_profile', 'block' if not admin.is_active else 'unblock',
                               f"admin {action}: {admin.business_name}", admin.pk, request)

            return Response({
                "status": "success",
                "message": f"admin {action} successfully"
            })

        except ServiceProvider.DoesNotExist:
            return Response({"status": "fail", "message": "admin not found"}, status=404)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)

    def _handle_document_uploads(self, data, folder):
        uploads = {}
        for key, file in data.items():
            if hasattr(file, 'read'):  
                if file.size > 15 * 1024 * 1024:
                    raise ValidationError(f"{key}: File too large (max 15MB)")

                filename = f"{key}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.name}"
                path = os.path.join(settings.MEDIA_ROOT, folder, filename)

                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb+') as f:
                    for chunk in file.chunks():
                        f.write(chunk)

                uploads[key] = os.path.join(folder, filename).replace('\\', '/')
        return uploads

    def log_activity(self, table_name, action, description, instance_id, request):
        AdminActivityLog.objects.create(
            table_name=table_name,
            record_id=instance_id,
            action=action,
            description=description,
            performed_by=request.user,
            ip_address=self._get_client_ip(request)
        )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')