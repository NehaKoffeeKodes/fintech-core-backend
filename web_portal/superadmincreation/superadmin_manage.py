from ..views import*


class SuperAdminManage(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            if request.data.get('first_name') and request.data.get('last_name'):
                return self._create_admin(request)
            elif request.data.get('page_number') or request.data.get('page_size'):
                return self._list_admins(request)
            else:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid request. Provide either admin creation data or pagination parameters.'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_admin(self, request):
        data = request.data
        required_fields = ['first_name', 'last_name', 'user_name', 'email', 'contact_number']

        for field in required_fields:
            if not data.get(field):
                return Response({
                    'status': 'fail',
                    'message': f'{field.replace("_", " ").title()} is required'
                }, status=status.HTTP_400_BAD_REQUEST)

        email = data['email'].strip().lower()
        username = data['user_name'].strip()
        contact = data['contact_number'].strip()

        if not validate_email_format(email):
            return Response({'status': 'fail', 'message': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)
        if not validate_phone_format(contact):
            return Response({'status': 'fail', 'message': 'Invalid phone number format'}, status=status.HTTP_400_BAD_REQUEST)

        if AdminAccount.objects.filter(email=email, is_deleted=False).exists():
            return Response({'status': 'fail', 'message': 'Email already registered'}, status=status.HTTP_409_CONFLICT)
        if AdminAccount.objects.filter(username=username, is_deleted=False).exists():
            return Response({'status': 'fail', 'message': 'Username already taken'}, status=status.HTTP_409_CONFLICT)
        if AdminAccount.objects.filter(contact_number=contact, is_deleted=False).exists():
            return Response({'status': 'fail', 'message': 'Phone number already in use'}, status=status.HTTP_409_CONFLICT)

        temp_password = generate_secure_password(12)

        try:
            new_admin = AdminAccount.objects.create_superuser(
                username=username,
                email=email,
                password=temp_password,
                first_name=data['first_name'].strip(),
                last_name=data['last_name'].strip(),
                contact_number=contact,
                alternate_contact_number=data.get('alternate_contact_number', '').strip(),
                notes=data.get('notes', '').strip()
            )
            new_admin.has_changed_initial_password = False
            new_admin.save()

            send_welcome_email_direct_smtp(
                to_email=new_admin.email,
                full_name=f"{new_admin.first_name} {new_admin.last_name}",
                username=new_admin.username,
                password=temp_password
            )

            return Response({
                'status': 'success',
                'message': 'SuperAdmin created successfully. Login credentials sent to email.'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to create admin account'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _list_admins(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            search = request.data.get('search', '').strip()

            if page < 1 or size < 1 or size > 100:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid pagination parameters'
                }, status=status.HTTP_400_BAD_REQUEST)

            queryset = AdminAccount.objects.filter(
                is_superuser=True,
                is_deleted=False
            ).order_by('-date_joined')

            if search:
                queryset = queryset.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(username__icontains=search) |
                    Q(email__icontains=search) |
                    Q(contact_number__icontains=search)
                )

            admins_data = [
                {
                    'id': admin.id,
                    'first_name': admin.first_name or '',
                    'last_name': admin.last_name or '',
                    'user_name': admin.username,
                    'email': admin.email,
                    'contact_number': admin.contact_number or '',
                    'alternate_contact_number': admin.alternate_contact_number or '',
                    'notes': admin.notes or '',
                    'has_2fa': bool(admin.google_auth_key),
                    'created_at': admin.date_joined.strftime('%Y-%m-%d %H:%M:%S')
                }
                for admin in queryset
            ]

            paginated = add_serial_numbers(admins_data, page, size)

            return Response({
                'status': 'success',
                'message': 'Admins retrieved successfully',
                'data': paginated
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({
                'status': 'fail',
                'message': 'Page number and page size must be valid integers'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Failed to fetch admin list'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        admin_id = request.data.get('admin_id')
        if not admin_id:
            return Response({
                'status': 'fail',
                'message': 'admin_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin = AdminAccount.objects.get(id=admin_id, is_superuser=True, is_deleted=False)

            update_fields = [
                'first_name', 'last_name', 'username',
                'email', 'contact_number', 'alternate_contact_number', 'notes'
            ]

            updated = False
            for field in update_fields:
                value = request.data.get(field)
                if value is not None:
                    value = str(value).strip()
                    if getattr(admin, field) != value:
                        setattr(admin, field, value)
                        updated = True

            if updated:
                admin.save()
            return Response({
                'status': 'success',
                'message': 'Profile updated successfully'
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Admin not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Update failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        admin_id = request.data.get('admin_id')
        if not admin_id:
            return Response({
                'status': 'fail',
                'message': 'admin_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if str(admin_id) == str(request.user.id):
            return Response({
                'status': 'fail',
                'message': 'You cannot delete your own account'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            admin = AdminAccount.objects.get(id=admin_id, is_superuser=True, is_deleted=False)
            admin.is_deleted = True
            admin.is_active = False
            admin.save()

            return Response({
                'status': 'success',
                'message': 'Admin account removed successfully'
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': 'Admin not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Deletion failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)