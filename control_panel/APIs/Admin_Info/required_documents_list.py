from ...views import *

class ManageDocumentTemplatesView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        if request.data.get('page_number') or request.data.get('page_size'):
            return self.list_templates(request)
        else:
            return self.create_template(request)

    def create_template(self, request):
        try:
            with transaction.atomic():
                serializer = DocumentTemplateSerializer(data=request.data)
                if serializer.is_valid():
                    template = serializer.save(added_by=request.user)

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action="CREATE",
                        entity="DocumentTemplate",
                        admin_id=template.template_id,
                        description=f"Created document: {template.display_name}",
                        ip_address=request.META.get('REMOTE_ADDR')
                    )

                    return Response({
                        "success": True,
                        "message": "Document template added successfully"
                    }, status=status.HTTP_201_CREATED)

                errors = [str(err) for err in serializer.errors.values()]
                return Response({
                    "success": False,
                    "message": " | ".join(errors)
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "success": False,
                "message": f"Server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            with transaction.atomic():
                template_id = request.data.get('template_id')
                if not template_id:
                    return Response({"success": False, "message": "template_id required"}, status=status.HTTP_400_BAD_REQUEST)

                template = DocumentTemplate.objects.filter(
                    template_id=template_id, soft_deleted=False
                ).first()

                if not template:
                    return Response({"success": False, "message": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

                serializer = DocumentTemplateSerializer(template, data=request.data, partial=True)
                if serializer.is_valid():
                    updated_template = serializer.save()

                    AdminActivityLog.objects.create(
                        user=request.user,
                        action="UPDATE",
                        entity="DocumentTemplate",
                        admin_id=updated_template.template_id,
                        description=f"Updated: {updated_template.display_name}"
                    )

                    return Response({
                        "success": True,
                        "message": "Template updated successfully"
                    }, status=status.HTTP_200_OK)

                errors = [str(e) for e in serializer.errors.values()]
                return Response({"success": False, "message": " ".join(errors)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            with transaction.atomic():
                template_id = request.data.get('template_id')
                if not template_id:
                    return Response({"success": False, "message": "template_id required"}, status=status.HTTP_400_BAD_REQUEST)

                template = DocumentTemplate.objects.filter(
                    template_id=template_id, soft_deleted=False
                ).first()

                if not template:
                    return Response({"success": False, "message": "Template not found or already deleted"}, status=status.HTTP_404_NOT_FOUND)

                template.soft_deleted = True
                template.active = False
                template.save()

                AdminActivityLog.objects.create(
                    user=request.user,
                    action="DELETE",
                    entity="DocumentTemplate",
                    admin_id=template.template_id,
                    description=f"Deleted template: {template.display_name}"
                )

                return Response({
                    "success": True,
                    "message": "Template removed successfully"
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_templates(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            search = request.data.get('search', '')
            template_id = request.data.get('template_id')

            if page < 1 or size < 1:
                return Response({"success": False, "message": "Invalid pagination"}, status=status.HTTP_400_BAD_REQUEST)

            queryset = DocumentTemplate.objects.filter(soft_deleted=False, active=True)

            if template_id:
                queryset = queryset.filter(template_id=template_id)

            if search:
                queryset = queryset.filter(
                    Q(display_name__icontains=search) |
                    Q(internal_code__icontains=search)
                )

            total = queryset.count()
            if total == 0:
                return Response({
                    "success": True,
                    "message": "No templates found",
                    "data": {"total": 0, "results": []}
                }, status=status.HTTP_200_OK)

            paginator = Paginator(queryset.order_by('-template_id'), size)
            try:
                page_data = paginator.page(page)
            except EmptyPage:
                page_data = []

            serializer = DocumentTemplateSerializer(page_data, many=True)

            return Response({
                "success": True,
                "message": "Templates fetched",
                "data": {
                    "total": total,
                    "page": page,
                    "page_size": size,
                    "results": serializer.data
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)