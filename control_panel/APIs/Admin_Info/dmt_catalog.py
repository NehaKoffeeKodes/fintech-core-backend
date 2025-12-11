from ...views import *

class ServiceRoutingControlView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            if request.data.get('fetch_vendors'):
                return self.get_vendor_list(request)
            elif request.data.get('fetch_routing'):
                return self.get_current_routing(request)
            else:
                return Response({
                    "success": False,
                    "message": "Invalid request type. Use 'fetch_vendors' or 'fetch_routing'."
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "success": False,
                "message": "Something went wrong",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_vendor_list(self, request):
        try:
            vendors = ServiceProvider.objects.filter(
                service__title='Money Transfer',
                is_removed=False,
                is_inactive=False
            ).values('vendor_code', 'display_label')

            return Response({
                "success": True,
                "message": "Vendors fetched successfully",
                "data": list(vendors)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "message": "Failed to fetch vendors"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_current_routing(self, request):
        service_id = request.data.get('service_key')

        if not service_id:
            return Response({
                "success": False,
                "message": "service_key is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = SaCoreService.objects.get(service_key=service_id)
            current_order = service.routing_order or []

            return Response({
                "success": True,
                "message": "Current routing order retrieved",
                "routing_data": current_order
            }, status=status.HTTP_200_OK)

        except SaCoreService.DoesNotExist:
            return Response({
                "success": False,
                "message": "Service not found"
            }, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        try:
            service_key = request.data.get('service_key')
            new_order_ids = request.data.get('order_ids')  

            if not service_key:
                return Response({"success": False, "message": "service_key required"}, status=400)
            if not new_order_ids:
                return Response({"success": False, "message": "order_ids required"}, status=400)

            if isinstance(new_order_ids, str):
                new_order_ids = [int(x.strip()) for x in new_order_ids.split(',') if x.strip().isdigit()]
            elif isinstance(new_order_ids, list):
                new_order_ids = [int(x) for x in new_order_ids if isinstance(x, (int, str)) and str(x).isdigit()]
            else:
                return Response({"success": False, "message": "Invalid order_ids format"}, status=400)

            service = SaCoreService.objects.get(service_key=service_key)
            current_routing = service.routing_order or []

            if not current_routing:
                return Response({
                    "success": False,
                    "message": "No existing routing found to update"
                }, status=status.HTTP_404_NOT_FOUND)

            for entry in current_routing:
                if 'vendor_id' in entry:
                    vid = int(entry['vendor_id'])
                    if vid in new_order_ids:
                        new_priority = new_order_ids.index(vid) + 1
                        entry['priority'] = str(new_priority)

            service.routing_order = current_routing
            service.save()

            return Response({
                "success": True,
                "message": "Routing priority updated successfully",
                "updated_order": current_routing
            }, status=status.HTTP_200_OK)

        except SaCoreService.DoesNotExist:
            return Response({"success": False, "message": "Service not found"}, status=404)
        except Exception as e:
            return Response({
                "success": False,
                "message": "Update failed",
                "detail": str(e)
            }, status=500)