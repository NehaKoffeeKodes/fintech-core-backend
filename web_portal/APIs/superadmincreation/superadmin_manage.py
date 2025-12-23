from ...views import*
from utils.Api.helpers import *


class SuperAdminManageView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        action = self._detect_action(request.data)
        if action == "create":
            return self._handle_create(request)
        elif action == "list":
            return self._handle_list(request)
        else:
            return Response({
                "status": "fail",
                "message": "Please provide valid data for create or list operation"
            }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        return self._handle_update(request)

    def delete(self, request):
        return self._handle_delete(request)


    def _detect_action(self, data):
        if data.get("first_name") and data.get("last_name"):
            return "create"
        if "page_number" in data or "page_size" in data:
            return "list"
        return None

    def _handle_create(self, request):
        try:
            payload = request.data
            fields_required = ["first_name", "last_name", "user_name", "email", "contact_number"]
            for field in fields_required:
                if not payload.get(field):
                    return Response({
                        "status": "fail",
                        "message": f"{field.replace('_', ' ').title()} is mandatory"
                    }, status=status.HTTP_400_BAD_REQUEST)

            email = payload["email"].strip().lower()
            username = payload["user_name"].strip()
            phone = payload["contact_number"].strip()

            if not validate_email_format(email):
                return Response({"status": "fail", "message": "Please enter a valid email"}, status=status.HTTP_400_BAD_REQUEST)
            if not validate_phone_format(phone):
                return Response({"status": "fail", "message": "Please enter a valid phone number"}, status=status.HTTP_400_BAD_REQUEST)

            if AdminAccount.objects.filter(email=email, is_deleted=False).exists():
                return Response({"status": "fail", "message": "This email is already registered"}, status=status.HTTP_409_CONFLICT)
            if AdminAccount.objects.filter(username=username, is_deleted=False).exists():
                return Response({"status": "fail", "message": "This username is already taken"}, status=status.HTTP_409_CONFLICT)
            if AdminAccount.objects.filter(contact_number=phone, is_deleted=False).exists():
                return Response({"status": "fail", "message": "This phone number is already in use"}, status=status.HTTP_409_CONFLICT)

            temp_pass = generate_secure_password(12)
            new_admin = AdminAccount.objects.create_superuser(
                username=username,
                email=email,
                password=temp_pass,
                first_name=payload["first_name"].strip(),
                last_name=payload["last_name"].strip(),
                contact_number=phone,
            )
            new_admin.has_changed_initial_password = False
            new_admin.save()

            send_welcome_email_direct_smtp(
                to_email=new_admin.email,
                full_name=f"{new_admin.first_name} {new_admin.last_name}",
                username=new_admin.username,
                password=temp_pass
            )

            return Response({
                "status": "success",
                "message": "SuperAdmin account created successfully. Login details sent on email."
            }, status=status.HTTP_201_CREATED)

        except Exception as exc:
            return Response({"status": "error", "message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_list(self, request):
        try:
            page = max(1, int(request.data.get("page_number", 1)))
            size = min(100, max(1, int(request.data.get("page_size", 10))))
            search = request.data.get("search", "").strip()

            base_qs = AdminAccount.objects.filter(
                is_superuser=True,
                is_deleted=False
            ).order_by("-date_joined")

            if search:
                base_qs = base_qs.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(username__icontains=search) |
                    Q(email__icontains=search) |
                    Q(contact_number__icontains=search)
                )

            admin_list = []
            for admin in base_qs:
                admin_list.append({
                    "id": admin.id,
                    "full_name": f"{admin.first_name or ''} {admin.last_name or ''}".strip(),
                    "username": admin.username,
                    "email": admin.email,
                    "phone": admin.contact_number or "",
                    "has_2fa_enabled": bool(admin.google_auth_key),
                    "joined_on": admin.date_joined.strftime("%b %d, %Y")
                })

            paginated_data = add_serial_numbers(admin_list, page, size)

            return Response({
                "status": "success",
                "message": "SuperAdmins fetched successfully",
                "data": paginated_data
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"status": "fail", "message": "Invalid page or size value"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"status": "error", "message": "Failed to load data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_update(self, request):
        try:
            admin_id = request.data.get("admin_id")
            if not admin_id:
                return Response({"status": "fail", "message": "admin_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            admin = AdminAccount.objects.get(id=admin_id, is_superuser=True, is_deleted=False)

            if request.data.get("email"):
                new_email = request.data["email"].strip().lower()
                if new_email != admin.email and AdminAccount.objects.filter(email=new_email, is_deleted=False).exists():
                    return Response({"status": "fail", "message": "Email already in use"}, status=status.HTTP_409_CONFLICT)

            if request.data.get("user_name"):
                new_username = request.data["user_name"].strip()
                if new_username != admin.username and AdminAccount.objects.filter(username=new_username, is_deleted=False).exists():
                    return Response({"status": "fail", "message": "Username already taken"}, status=status.HTTP_409_CONFLICT)

            if request.data.get("contact_number"):
                new_phone = request.data["contact_number"].strip()
                if new_phone != admin.contact_number and AdminAccount.objects.filter(contact_number=new_phone, is_deleted=False).exists():
                    return Response({"status": "fail", "message": "Phone number already in use"}, status=status.HTTP_409_CONFLICT)

            update_map = {
                "first_name": request.data.get("first_name"),
                "last_name": request.data.get("last_name"),
                "user_name": request.data.get("user_name"),
                "email": request.data.get("email"),
                "contact_number": request.data.get("contact_number"),
            }

            for field, value in update_map.items():
                if value is not None:
                    setattr(admin, field, str(value).strip())

            admin.save()

            return Response({
                "status": "success",
                "message": "SuperAdmin profile updated successfully"
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({"status": "fail", "message": "SuperAdmin not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"status": "error", "message": "Update failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_delete(self, request):
        try:
            admin_id = request.data.get("admin_id")
            if not admin_id:
                return Response({"status": "fail", "message": "admin_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            if str(admin_id) == str(request.user.id):
                return Response({"status": "fail", "message": "You cannot delete your own account"}, status=status.HTTP_403_FORBIDDEN)

            admin = AdminAccount.objects.get(id=admin_id, is_superuser=True, is_deleted=False)
            admin.is_deleted = True
            admin.is_active = False
            admin.save()

            return Response({
                "status": "success",
                "message": "SuperAdmin account removed successfully"
            }, status=status.HTTP_200_OK)

        except AdminAccount.DoesNotExist:
            return Response({"status": "fail", "message": "SuperAdmin not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"status": "error", "message": "Deletion failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)