from ...views import*

class ManageFundRequestsView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        try:
            if 'bank_account_id' in request.data and 'deposit_value' in request.data:
                return self.submit_deposit_request(request)
            else:
                return self.retrieve_deposit_requests(request)
        except Exception as exc:
            return Response({
                "error": True,
                "message": f"Server error occurred: {str(exc)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def submit_deposit_request(self, request):
        try:
            deposit_method = request.data.get('deposit_method')
            bank_account_id = request.data.get('bank_account_id')
            deposit_value = request.data.get('deposit_value')
            proof_attachment = request.FILES.get('proof_attachment')
            user_note = request.data.get('user_note')
            ref_number = request.data.get('ref_number')        
            utr_value = request.data.get('utr_value')           
            transfer_type = request.data.get('transfer_type')    

            mandatory_fields = ['deposit_method', 'bank_account_id', 'deposit_value', 'proof_attachment', 'user_note']
            validation_error = enforce_required_fields(request.data, mandatory_fields)
            if validation_error:
                return validation_error

            allowed_methods = ['counter_deposit', 'cdm_deposit', 'online_transfer']
            if deposit_method not in allowed_methods:
                return Response({
                    "error": True,
                    "message": f"deposit_method must be one of {allowed_methods}"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                bank_account = DepositBankAccount.objects.get(
                    account_id=bank_account_id,
                    is_archived=False
                )
            except DepositBankAccount.DoesNotExist:
                return Response({
                    "error": True,
                    "message": "Selected bank account does not exist or is archived"
                }, status=status.HTTP_400_BAD_REQUEST)

            if deposit_method == 'online_transfer':
                charges_config = bank_account.digital_transfer_fees or {}
            elif deposit_method == 'counter_deposit':
                charges_config = bank_account.branch_counter_fees or {}
            elif deposit_method == 'cdm_deposit':
                charges_config = bank_account.cdm_deposit_machine_fees or {}
            else:
                charges_config = {}

            min_value = float(charges_config.get('minimum_amount', 0))
            max_value = float(charges_config.get('maximum_amount', 999999999))

            try:
                deposit_value = float(deposit_value)
            except (ValueError, TypeError):
                return Response({
                    "error": True,
                    "message": "Invalid deposit value provided"
                }, status=status.HTTP_400_BAD_REQUEST)

            if not (min_value <= deposit_value <= max_value):
                return Response({
                    "error": True,
                    "message": f"Deposit value must be between ₹{min_value} and ₹{max_value}"
                }, status=status.HTTP_400_BAD_REQUEST)

            if deposit_method in ['counter_deposit', 'cdm_deposit']:
                if not ref_number:
                    return Response({
                        "error": True,
                        "message": "ref_number is required for counter/cdm deposit"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if not (12 <= len(str(ref_number)) <= 16):
                    return Response({
                        "error": True,
                        "message": "ref_number length must be between 12 and 16 digits"
                    }, status=status.HTTP_400_BAD_REQUEST)

            elif deposit_method == 'online_transfer':
                if not utr_value:
                    return Response({
                        "error": True,
                        "message": "utr_value is required for online transfer"
                    }, status=status.HTTP_400_BAD_REQUEST)
                if not transfer_type:
                    return Response({
                        "error": True,
                        "message": "transfer_type is required for online transfer"
                    }, status=status.HTTP_400_BAD_REQUEST)
                valid_transfer_types = ['IMPS', 'RTGS', 'NEFT']
                if transfer_type not in valid_transfer_types:
                    return Response({
                        "error": True,
                        "message": f"transfer_type must be one of {valid_transfer_types}"
                    }, status=status.HTTP_400_BAD_REQUEST)

                if FundDepositRequest.objects.filter(utr_ref=utr_value).exists():
                    return Response({
                        "error": True,
                        "message": "This utr_value is already used"
                    }, status=status.HTTP_400_BAD_REQUEST)

            uploaded_path = store_uploaded_document(proof_attachment, "deposit_proofs")
            if not uploaded_path:
                return Response({
                    "error": True,
                    "message": "Failed to upload proof document"
                }, status=status.HTTP_400_BAD_REQUEST)

            contact_mobile = self.resolve_submitter_contact(request.user)

            if not contact_mobile:
                return Response({
                    "error": True,
                    "message": "Unable to determine submitter mobile number"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                submitter = PortalUser.objects.get(mobile_number=contact_mobile)  
            except PortalUser.DoesNotExist:
                return Response({
                    "error": True,
                    "message": f"No PortalUser found with mobile number: {contact_mobile}"
                }, status=status.HTTP_400_BAD_REQUEST)

            method_flags = {
                "counter_deposit": deposit_method == "counter_deposit",
                "cdm_deposit": deposit_method == "cdm_deposit",
                "online_transfer": deposit_method == "online_transfer",
            }

            deposit_request = FundDepositRequest.objects.create(
                deposit_methods=method_flags,
                linked_bank=bank_account,
                deposit_amount=deposit_value,
                proof_documents={"proof_attachment": uploaded_path},
                user_remarks=user_note,
                reference_id=ref_number if deposit_method in ['counter_deposit', 'cdm_deposit'] else None,
                utr_ref=utr_value if deposit_method == 'online_transfer' else None,
                transfer_mode=transfer_type if deposit_method == 'online_transfer' else None,
                submitted_by=submitter
            )

            record_member_activity({
                "record_id": deposit_request.request_ref,
                "module_name": "DepositRequest",
                "action_type": "CREATE",
                "action_details": "Deposit request submitted successfully",
                "performed_by": request.user
            })

            save_api_log(request, "SubmitDepositRequest", request.data, {"success": True})

            return Response({
                "success": True,
                "message": "Deposit request submitted successfully",
                "request_ref": deposit_request.request_ref
            }, status=status.HTTP_201_CREATED)

        except Exception as exc:
            import traceback
            traceback.print_exc()  
            save_api_log(request, "SubmitDepositRequest", request.data, {"error": str(exc)})
            return Response({
                "error": True,
                "message": f"Debug: {str(exc)} [{type(exc).__name__}]"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve_deposit_requests(self, request):
        try:
            page_no = int(request.data.get('page_no', 1))
            page_limit = int(request.data.get('page_limit', 10))
            search_term = request.data.get('search')
            status_list = request.data.get('status')
            request_ref = request.data.get('request_ref')

            queryset = FundDepositRequest.objects.filter(is_removed=False)
            if not request.user.is_superuser:
                contact_mobile = self.resolve_submitter_contact(request.user)
                if not contact_mobile:
                    return Response({
                        "error": True,
                        "message": "Unable to determine admin mobile"
                    }, status=status.HTTP_400_BAD_REQUEST)
                try:
                    submitter = PortalUser.objects.get(mobile_number=contact_mobile) 
                except PortalUser.DoesNotExist:
                    return Response({
                        "error": True,
                        "message": "Associated PortalUser not found"
                    }, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(submitted_by=submitter)

            if search_term:
                queryset = queryset.filter(
                    Q(utr_ref__icontains=search_term) |
                    Q(reference_id__icontains=search_term)
                )
            if status_list:
                queryset = queryset.filter(status__in=status_list.split(','))
            if request_ref:
                queryset = queryset.filter(request_ref=request_ref)

            queryset = apply_date_range_filter(request.data, queryset, 'submitted_at')
            queryset = queryset.order_by('-submitted_at')

            paginator = Paginator(queryset, page_limit)
            try:
                page_data = paginator.page(page_no)
            except EmptyPage:
                page_data = paginator.page(paginator.num_pages)

            serializer = FundRequestSerializer(page_data, many=True, context={'request': request})

            return Response({
                "success": True,
                "data": {
                    "results": serializer.data,
                    "current_page": page_data.number,
                    "total_pages": paginator.num_pages,
                    "total_count": paginator.count
                }
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                "error": True,
                "message": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def patch(self, request):
        try:
            req_ref = request.data.get('request_ref')
            operation = request.data.get('operation') 
            notes = request.data.get('notes')

            if not req_ref or not operation:
                return Response({
                    "error": True,
                    "message": "request_ref and operation are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            if not request.user.is_superuser:
                return Response({
                    "error": True,
                    "message": "Only super admin can perform this action"
                }, status=status.HTTP_403_FORBIDDEN)

            deposit_req = FundDepositRequest.objects.get(request_ref=req_ref)

            if operation == "APPROVED" and deposit_req.status != "PENDING":
                return Response({"error": True, "message": "Request already processed"}, status=status.HTTP_400_BAD_REQUEST)
            if operation == "REVERSED" and deposit_req.status != "APPROVED":
                return Response({"error": True, "message": "Only approved requests can be reversed"}, status=status.HTTP_400_BAD_REQUEST)

            db_name = get_database_from_domain() or "default"
            switch_to_database(db_name)

            user_wallet = PortalUserBalance.objects.using(db_name).get(user=deposit_req.submitted_by)
            amt = deposit_req.deposit_amount

            if operation == "APPROVED":
                user_wallet.primary_balance += Decimal(str(amt))
                user_wallet.save(using=db_name)
                self.log_wallet_transaction(db_name, deposit_req, amt, "CR", "Deposit Approved")
            elif operation == "REVERSED":
                user_wallet.primary_balance -= Decimal(str(amt))
                user_wallet.save(using=db_name)
                self.log_wallet_transaction(db_name, deposit_req, amt, "DR", "Deposit Reversed")

            deposit_req.status = operation
            if notes:
                deposit_req.admin_reasons = notes

            try:
                reviewer = PortalUser.objects.get(id=1)
            except PortalUser.DoesNotExist:
                reviewer = None  

            deposit_req.reviewed_by = reviewer
            deposit_req.reviewed_at = timezone.now()
            deposit_req.save()

            record_member_activity({
                "record_id": deposit_req.request_ref,
                "module_name": "DepositRequest",
                "action_type": operation,
                "action_details": f"Request {operation.lower()}",
                "performed_by": reviewer
            })

            return Response({
                "success": True,
                "message": f"Request {operation.lower()} successfully"
            }, status=status.HTTP_200_OK)

        except FundDepositRequest.DoesNotExist:
            return Response({"error": True, "message": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"error": True, "message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def delete(self, request):
        try:
            req_ref = request.data.get('request_ref')
            if not req_ref:
                return Response({
                    "error": True,
                    "message": "request_ref is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            deposit_req = FundDepositRequest.objects.get(request_ref=req_ref, is_removed=False)

            if deposit_req.status != "PENDING":
                return Response({
                    "error": True,
                    "message": "Only pending requests can be deleted"
                }, status=status.HTTP_400_BAD_REQUEST)


            is_super_admin = (
                hasattr(request.user, 'is_superuser') and request.user.is_superuser
            ) or (
                hasattr(request.user, 'member_type') and request.user.member_type == "SUPER_ADMIN"
            )

            if deposit_req.submitted_by != request.user and not is_super_admin:
                return Response({
                    "error": True,
                    "message": "Unauthorized action"
                }, status=status.HTTP_403_FORBIDDEN)

            deposit_req.is_removed = True
            deposit_req.save()

            return Response({
                "success": True,
                "message": "Request deleted successfully"
            }, status=status.HTTP_200_OK)

        except FundDepositRequest.DoesNotExist:
            return Response({"error": True, "message": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"error": True, "message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def resolve_submitter_contact(self, user):

        if user.__class__.__name__ == "AdminAccount" or not hasattr(user, 'member_type'):
            try:
                root = PortalUser.objects.get(id=1)
                if root.mobile_number:
                    return root.mobile_number.strip()
                else:
                    print("Warning: Root PortalUser has no mobile_number")
                    return ""
            except PortalUser.DoesNotExist:
                print("Error: Root PortalUser (id=1) does not exist!")
                return ""

        if user.member_type == "SUPER_ADMIN":
            return user.mobile_number.strip() if user.mobile_number else ""

        if hasattr(user, 'created_by') and user.created_by and user.created_by.id == 1:
            try:
                root = PortalUser.objects.get(id=1)
                return root.mobile_number.strip() if root.mobile_number else ""
            except PortalUser.DoesNotExist:
                pass

        return user.mobile_number.strip() if user.mobile_number else ""
    
    
    def log_wallet_transaction(self, db_name, deposit_req, amount, dr_cr, suffix=""):
        GlTrn.objects.using(db_name).create(
            linked_service_id=deposit_req.request_ref,
            member=deposit_req.submitted_by,
            amount=amount,
            entry_nature=dr_cr,
            transaction_type="Fund Deposit",
            final_amount=amount if dr_cr == "CR" else -amount,
            transaction_time=timezone.now()
        )
        WalletHistory.objects.using(db_name).create(
            user=deposit_req.submitted_by,
            action_name=f"Deposit Request {suffix}".strip(),
            changed_amount=amount,
            change_type=dr_cr,
            balance_after=PortalUserBalance.objects.using(db_name).get(user=deposit_req.submitted_by).primary_balance,
            transaction_date=timezone.now()
        )