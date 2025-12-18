from ...views import*


class SaManageChargesView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 10))
            fee_id = request.query_params.get('fee_id')
            keyword = request.query_params.get('search', '').strip()

            if page < 1 or limit < 1:
                return Response({
                    "success": False,
                    "message": "Invalid pagination values"
                }, status=status.HTTP_400_BAD_REQUEST)

            queryset = AdditionalFee.objects.filter(is_removed=False)

            if fee_id:
                queryset = queryset.filter(fee_id=fee_id)

            if keyword:
                queryset = queryset.filter(
                    Q(title__icontains=keyword) | Q(category__icontains=keyword)
                )

            paginator = Paginator(queryset, limit)
            page_data = paginator.page(page)

            serializer = SaAdditionalChargesSerializer(page_data, many=True)

            response_payload = {
                "success": True,
                "message": "Extra charges retrieved successfully",
                "pagination": {
                    "current_page": page,
                    "total_pages": paginator.num_pages,
                    "total_records": paginator.count,
                    "page_size": limit
                },
                "results": serializer.data
            }

            return Response(response_payload, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "message": "Server error occurred",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            fee_id = request.data.get('fee_id')
            category = request.data.get('category')
            amount = request.data.get('amount')
            tax_id = request.data.get('tax_code')

           
            if not fee_id:
                return Response({"success": False, "message": "fee_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            fee = AdditionalFee.objects.get(fee_id=fee_id, is_removed=False)

           
            if not any([category, amount, tax_id]):
                fee.is_active = not fee.is_active
                fee.save()
                action = "activated" if fee.is_active else "deactivated"
                return Response({
                    "success": True,
                    "message": f"Charge {action} successfully"
                }, status=status.HTTP_200_OK)

            
            if tax_id:
                tax_obj = GSTCode.objects.get(gst_id=tax_id)
                fee.tax_code = tax_obj

            if category is not None:
                fee.category = category
            if amount is not None:
                fee.amount = amount

            fee.save()

            return Response({
                "success": True,
                "message": "Extra charge updated successfully"
            }, status=status.HTTP_200_OK)

        except AdditionalFee.DoesNotExist:
            return Response({"success": False, "message": "Charge not found"}, status=status.HTTP_404_NOT_FOUND)
        except GSTCode.DoesNotExist:
            return Response({"success": False, "message": "Invalid tax code"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "success": False,
                "message": "Update failed",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            fee_id = request.data.get('fee_id')
            if not fee_id:
                return Response({"success": False, "message": "fee_id required"}, status=status.HTTP_400_BAD_REQUEST)

            charge = AdditionalFee.objects.get(fee_id=fee_id, is_removed=False)
            print('charge:',charge)
            charge.is_removed = True
            charge.save()

            return Response({
                "success": True,
                "message": "Charge removed successfully"
            }, status=status.HTTP_200_OK)

        except AdditionalFee.DoesNotExist:
            return Response({"success": False, "message": "Charge not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "success": False,
                "message": "Delete failed"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)