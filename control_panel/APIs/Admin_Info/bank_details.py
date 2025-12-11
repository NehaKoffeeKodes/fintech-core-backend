from ...views import*

logger = logging.getLogger(__name__)


class ManageDepositBanksAPIView(APIView):
    authentication_classes = [SecureJWTAuthentication]  
    permission_classes =  [IsSuperAdmin | IsAdmin]


    def post(self, request):
        if 'enabled_channels' in request.data:
            return self.create_bank_account(request)

        if 'page' in request.query_params or 'size' in request.query_params:
            return self.list_bank_accounts(request)

        return Response(
            {"error": True, "message": "Invalid action. Use proper fields."},
            status=status.HTTP_400_BAD_REQUEST
        )

    def create_bank_account(self, request):
        try:
            required = ['enabled_channels', 'bank_title', 'ifsc_code', 'branch_location',
                        'holder_name', 'account_number', 'account_kind']

            error_response = enforce_required_fields(request.data, required)
            if error_response:
                return error_response

            channels = request.data['enabled_channels']
            bank_title = request.data['bank_title'].strip()
            ifsc = request.data['ifsc_code'].strip().upper()
            branch = request.data['branch_location'].strip()
            holder = request.data['holder_name'].strip()
            acc_no = request.data['account_number'].strip()
            acc_kind = request.data['account_kind'].strip()

            online_fees = request.data.get('digital_transfer_fees')
            cdm_fees = request.data.get('cdm_deposit_fees')
            counter_fees = request.data.get('branch_counter_fees')

            if not contains_only_letters_spaces_underscore(bank_title):
                return Response({"error": True, "message": "Invalid bank name format."}, status=400)

            if not is_legitimate_ifsc(ifsc):
                return Response({"error": True, "message": "Invalid IFSC code format."}, status=400)

            if not contains_only_letters_spaces_underscore(branch):
                return Response({"error": True, "message": "Invalid branch name."}, status=400)

            if not contains_only_letters_spaces_underscore(acc_kind):
                return Response({"error": True, "message": "Invalid account type."}, status=400)

            if not is_valid_account_no(acc_no):
                return Response({"error": True, "message": "Account number must be 8-16 digits."}, status=400)

            def parse_json(field_name, value):
                if not value:
                    return None
                try:
                    return json.loads(value) if isinstance(value, str) else value
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON in {field_name}")

            online_fees = parse_json("digital_transfer_fees", online_fees)
            cdm_fees = parse_json("cdm_deposit_fees", cdm_fees)
            counter_fees = parse_json("branch_counter_fees", counter_fees)

            if DepositBankAccount.objects.filter(
                ifsc_code=ifsc,
                account_number=acc_no,
                is_archived=False
            ).exists():
                return Response({"error": True, "message": "Bank with this IFSC & Account already exists."}, status=400)

            DepositBankAccount.objects.create(
                enabled_channels=channels if isinstance(channels, list) else json.loads(channels),
                bank_title=bank_title,
                ifsc_code=ifsc,
                branch_location=branch,
                holder_name=holder,
                account_number=acc_no,
                account_kind=acc_kind,
                digital_transfer_fees=online_fees,
                cdm_deposit_machine_fees=cdm_fees,
                branch_counter_fees=counter_fees,
                added_by=request.user
            )

            return Response({
                "success": True,
                "message": "Bank account added successfully."
            }, status=status.HTTP_201_CREATED)

        except ValueError as ve:
            return Response({"error": True, "message": str(ve)}, status=400)
        except Exception as e:
            logger.error(f"Bank creation failed: {e}")
            return Response({"error": True, "message": "Server error."}, status=500)
        
    def get(self, request):
        return self.list_bank_accounts(request)

    def list_bank_accounts(self, request):
        try:
            page = request.query_params.get('page', '1')
            size = request.query_params.get('size', '10')
            page = int(page)
            size = int(size)

            error = validate_paging_inputs(str(page), str(size))
            if error:
                return error

            queryset = DepositBankAccount.objects.filter(is_archived=False).order_by('-added_at')

            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(bank_title__icontains=search) |
                    Q(ifsc_code__icontains=search) |
                    Q(account_number__icontains=search)
                )

            channel = request.query_params.get('channel')
            if channel:
                queryset = [b for b in queryset if b.enabled_channels.get(channel, False)]

            bank_id = request.query_params.get('bank_id')
            if bank_id:
                try:
                    bank = queryset.get(account_id=bank_id)
                    active_channels = {k: v for k, v in bank.enabled_channels.items() if v}
                    return Response({
                        "success": True,
                        "data": {
                            "bank_id": bank.account_id,
                            "enabled_channels": active_channels,
                            "bank_title": bank.bank_title,
                            "ifsc_code": bank.ifsc_code,
                            "branch_location": bank.branch_location,
                            "holder_name": bank.holder_name,
                            "account_number": bank.account_number,
                            "account_kind": bank.account_kind,
                            "digital_transfer_fees": bank.digital_transfer_fees,
                            "cdm_deposit_fees": bank.cdm_deposit_fees,
                            "branch_counter_fees": bank.branch_counter_fees,
                            "is_enabled": bank.is_enabled
                        }
                    })
                except DepositBankAccount.DoesNotExist:
                    return Response({"error": True, "message": "Bank not found."}, status=404)

            paginator = Paginator(queryset, size)
            if page > paginator.num_pages:
                page = paginator.num_pages

            page_obj = paginator.get_page(page)

            results = []
            for bank in page_obj:
                active = {k: v for k, v in bank.enabled_channels.items() if v}
                results.append({
                    "bank_id": bank.account_id,
                    "enabled_channels": active,
                    "bank_title": bank.bank_title,
                    "ifsc_code": bank.ifsc_code,
                    "branch_location": bank.branch_location,
                    "account_number": bank.account_number,
                    "account_kind": bank.account_kind,
                    "is_enabled": bank.is_enabled
                })

            return Response({
                "success": True,
                "data": {
                    "results": results,
                    "current_page": page,
                    "total_pages": paginator.num_pages,
                    "total_items": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous()
                }
            })

        except Exception as e:
            logger.error(f"List banks error: {e}")
            return Response({"error": True, "message": "Server error."}, status=500)

    def delete(self, request):
        error = enforce_required_fields(request.data, ['bank_id'])
        if error:
            return error

        try:
            bank_id = int(request.data['bank_id'])
            bank = DepositBankAccount.objects.get(account_id=bank_id, is_archived=False)
            bank.is_archived = True
            bank.modified_by = request.user
            bank.save()
            return Response({"success": True, "message": "Bank removed successfully."})
        except ValueError:
            return Response({"error": True, "message": "Invalid bank ID."}, status=400)
        except DepositBankAccount.DoesNotExist:
            return Response({"error": True, "message": "Bank not found."}, status=404)


    def patch(self, request): 
        error = enforce_required_fields(request.data, ['bank_id'])
        if error:
            return error

        try:
            bank = DepositBankAccount.objects.get(
                account_id=request.data['bank_id'],
                is_archived=False
            )

            if len(request.data) == 1:  
                if bank.funddepositrequest_set.filter(is_removed=False).exists():
                    return Response({
                        "error": True,
                        "message": "Cannot disable bank with active fund requests."
                    }, status=400)

                bank.is_enabled = not bank.is_enabled
                bank.modified_by = request.user
                bank.save()

                return Response({
                    "success": True,
                    "message": f"Bank {'enabled' if bank.is_enabled else 'disabled'} successfully."
                })

            updates = {}
            fields_to_validate = {
                'bank_title': contains_only_letters_spaces_underscore,
                'ifsc_code': is_legitimate_ifsc,
                'branch_location': contains_only_letters_spaces_underscore,
                'account_kind': contains_only_letters_spaces_underscore,
                'account_number': is_valid_account_no,
            }

            for field, validator in fields_to_validate.items():
                value = request.data.get(field)
                if value is not None:
                    if not validator(str(value).strip()):
                        return Response({"error": True, "message": f"Invalid {field.replace('_', ' ')}."}, status=400)
                    updates[field] = str(value).strip()

            if 'enabled_channels' in request.data:
                updates['enabled_channels'] = request.data['enabled_channels']

            for charge_field in ['digital_transfer_fees', 'cdm_deposit_fees', 'branch_counter_fees']:
                if request.data.get(charge_field) is not None:
                    try:
                        updates[charge_field.replace('_fees', '_deposit_machine_fees') if 'cdm' in charge_field else charge_field] = (
                            json.loads(request.data[charge_field]) if isinstance(request.data[charge_field], str) else request.data[charge_field]
                        )
                    except json.JSONDecodeError:
                        return Response({"error": True, "message": f"Invalid JSON in {charge_field}"}, status=400)

            for key, val in updates.items():
                setattr(bank, key, val)

            bank.modified_by = request.user
            bank.save()

            return Response({"success": True, "message": "Bank details updated successfully."})

        except DepositBankAccount.DoesNotExist:
            return Response({"error": True, "message": "Bank not found."}, status=404)
        except Exception as e:
            logger.error(f"Bank update failed: {e}")
            return Response({"error": True, "message": "Update failed."}, status=500)