from ...views import*


class ManageFundRequestsView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        if 'bank_id' in request.data and 'amount' in request.data:
            return self.create_request(request)
        else:
            return self.list_requests(request)

    def create_request(self, request):
        try:
            required = ['bank_id', 'amount', 'channel', 'proof_image', 'note']
            error = enforce_required_fields(request.data, required)
            if error:
                return error

            channel = request.data['channel']
            bank_id = request.data['bank_id']
            amount = float(request.data['amount'])
            note = request.data['note']
            proof_file = request.FILES.get('proof_image')

            valid_channels = ['counter_deposit', 'cdm_deposit', 'online_transfer']
            if channel not in valid_channels:
                return Response({"error": True, "message": f"Channel must be one of: {valid_channels}"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                bank = DepositBankAccount.objects.get(account_id=bank_id, is_archived=False)
            except DepositBankAccount.DoesNotExist:
                return Response({"error": True, "message": "Bank account not found"}, status=status.HTTP_404_NOT_FOUND)

            charges = {}
            if channel == 'online_transfer':
                charges = bank.digital_transfer_fees or {}
            elif channel == 'counter_deposit':
                charges = bank.branch_counter_fees or {}
            elif channel == 'cdm_deposit':
                charges = bank.cdm_deposit_machine_fees or {}

            min_amt = float(charges.get('minimum_amount', 0))
            max_amt = float(charges.get('maximum_amount', 99999999))
            if not (min_amt <= amount <= max_amt):
                return Response({
                    "error": True,
                    "message": f"Amount must be between ₹{min_amt} and ₹{max_amt}"
                }, status=status.HTTP_400_BAD_REQUEST)

            proof_path = store_uploaded_document(proof_file, "fund_proofs")
            if not proof_path:
                return Response({"error": True, "message": "Failed to upload proof"}, status=status.HTTP_400_BAD_REQUEST)

           

            admin_contact = self.get_admin_contact(request.user)
            admin_user = PortalUser.objects.get(mobile=admin_contact)

            deposit_data = {
                "counter_deposit": channel == "counter_deposit",
                "cdm_deposit": channel == "cdm_deposit",
                "online_transfer": channel == "online_transfer",
            }

            fund_req = FundDepositRequest.objects.create(
                deposit_methods=deposit_data,
                linked_bank=bank,
                deposit_amount=amount,
                proof_documents={"proof_image": proof_path},
                user_remarks=note,
                submitted_by=admin_user
            )

            record_member_activity({
                "record_id": fund_req.request_ref,
                "module_name": "FundRequest",
                "action_type": "CREATE",
                "action_details": "New fund deposit request created",
                "performed_by": request.user
            })

            save_api_log(request, "CreateFundRequest", request.data, {"success": True})

            return Response({
                "success": True,
                "message": "Fund request created successfully",
                "request_id": fund_req.request_ref
            }, status=201)

        except Exception as e:
            save_api_log(request, "CreateFundRequest", request.data, {"error": str(e)})
            return Response({"error": True, "message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def get(self, request):
        return self.list_requests(request)

    def list_requests(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            size = int(request.query_params.get('size', 10))
            search = request.query_params.get('search')
            status_filter = request.query_params.get('status')
            req_id = request.query_params.get('id')

            queryset = FundDepositRequest.objects.filter(is_removed=False)

            if request.user.member_type == "SUPER_ADMIN":
                pass  
            else:
                admin_contact = self.get_admin_contact(request.user)
                admin = PortalUser.objects.get(mobile=admin_contact)
                queryset = queryset.filter(submitted_by=admin)

            if search:
                queryset = queryset.filter(
                    Q(utr_ref__icontains=search) |
                    Q(reference_id__icontains=search)
                )
            if status_filter:
                queryset = queryset.filter(status__in=status_filter.split(','))
            if req_id:
                queryset = queryset.filter(request_ref=req_id)

            queryset = apply_date_range_filter(request.query_params, queryset, 'submitted_at')
            paginator = Paginator(queryset.order_by('-submitted_at'), size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            serializer = FundRequestSerializer(page_obj, many=True, context={'request': request})

            return Response({
                "success": True,
                "data": {
                    "results": serializer.data,
                    "current_page": page_obj.number,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                }
            })

        except Exception as e:
            return Response({"error": True, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request):
        try:
            req_id = request.data.get('request_id')
            action = request.data.get('action')  
            reason = request.data.get('reason')

            if not req_id or not action:
                return Response({"error": True, "message": "request_id and action required"}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.member_type != "SUPER_ADMIN":
                return Response({"error": True, "message": "Only super admin can approve"}, status=status.HTTP_403_FORBIDDEN)

            fund_req = FundDepositRequest.objects.get(request_ref=req_id)

            if action == "APPROVED" and fund_req.status != "PENDING":
                return Response({"error": True, "message": "Already processed"}, status=status.HTTP_400_BAD_REQUEST)
            if action == "REVERSED" and fund_req.status != "APPROVED":
                return Response({"error": True, "message": "Can only reverse approved requests"}, status=status.HTTP_400_BAD_REQUEST)

            admin_contact = fund_req.submitted_by.mobile
            db_name = get_database_from_domain() or "default"
            switch_to_database(db_name)

            wallet = PortalUserBalance.objects.using(db_name).get(user=fund_req.submitted_by)
            amount = fund_req.deposit_amount

            if action == "APPROVED":
                wallet.main_balance += Decimal(str(amount))
                wallet.save(using=db_name)
                self.create_wallet_entry(db_name, fund_req, amount, "CR", "Fund Added")

            elif action == "REVERSED":
                wallet.main_balance -= Decimal(str(amount))
                wallet.save(using=db_name)
                self.create_wallet_entry(db_name, fund_req, amount, "DR", "Reversed")

            fund_req.status = action
            if reason:
                fund_req.admin_reasons = reason
            fund_req.reviewed_by = request.user
            fund_req.reviewed_at = timezone.now()
            fund_req.save()

            record_member_activity({
                "record_id": fund_req.request_ref,
                "module_name": "FundRequest",
                "action_type": action,
                "action_details": f"Request {action.lower()}",
                "performed_by": request.user
            })

            return Response({"success": True, "message": f"Request {action.lower()} successfully"})

        except Exception as e:
            return Response({"error": True, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        req_id = request.data.get('request_id')
        if not req_id:
            return Response({"error": True, "message": "request_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            req = FundDepositRequest.objects.get(request_ref=req_id, is_removed=False)
            if req.status != "PENDING":
                return Response({"error": True, "message": "Only pending requests can be deleted"}, status=status.HTTP_400_BAD_REQUEST)

            if req.submitted_by != request.user and request.user.member_type != "SUPER_ADMIN":
                return Response({"error": True, "message": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)

            req.is_removed = True
            req.save()

            return Response({"success": True, "message": "Request deleted"})

        except FundDepositRequest.DoesNotExist:
            return Response({"error": True, "message": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    def get_admin_contact(self, user):
        if user.member_type == "SUPER_ADMIN":
            return user.mobile

        if user.created_by and user.created_by.id == 1:
            return PortalUser.objects.get(id=1).mobile
        return user.mobile

    def create_wallet_entry(self, db_name, fund_req, amount, dr_cr, label_suffix=""):
        GlTrn.objects.using(db_name).create(
            linked_service_id=fund_req.request_ref,
            member=fund_req.submitted_by,
            amount=amount,
            entry_nature=dr_cr,
            transaction_type="Fund Deposit",
            final_amount=amount if dr_cr == "CR" else -amount,
            transaction_time=timezone.now()
        )
        WalletHistory.objects.using(db_name).create(
            user=fund_req.submitted_by,
            action_name=f"Fund Request {label_suffix}".strip(),
            changed_amount=amount,
            change_type=dr_cr,
            balance_after=PortalUserBalance.objects.using(db_name).get(user=fund_req.submitted_by).main_balance,
            transaction_date=timezone.now()
        )