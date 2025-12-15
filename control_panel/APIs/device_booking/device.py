from ...views import*

class GadgetPurchaseAPIView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

    def post(self, request):
        if 'item' in request.data and 'qty' in request.data:
            return self.calculate_purchase_summary(request)
        elif 'grand_total' in request.data and 'ordered_qty' in request.data:
            return self.place_new_purchase(request)
        elif 'page_num' in request.data or 'page_size' in request.data:
            return self.list_all_purchases(request)
        else:
            return Response({'status': 'fail', 'message': 'Invalid request format.'}, status=status.HTTP_400_BAD_REQUEST)

    def calculate_purchase_summary(self, request):
        try:
            item_id = request.data.get('item')
            qty = int(request.data.get('qty'))

            if qty <= 0:
                return Response({'status': 'fail', 'message': 'Quantity should be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

            item = GadgetItem.objects.get(item_id=item_id)
            total_cost = float(item.cost) * qty

            summary = {
                "item_id": item.item_id,
                "item_title": item.title,
                "unit_cost": float(item.cost),
                "requested_qty": qty,
                "grand_total": total_cost
            }

            return Response({
                'status': 'success',
                'message': 'Purchase summary generated.',
                'data': summary
            }, status=status.HTTP_200_OK)
        except GadgetItem.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def place_new_purchase(self, request):
        try:
            item_id = request.data.get('item')
            total_amount = Decimal(str(request.data.get('grand_total')))
            qty = int(request.data.get('ordered_qty'))

            item = GadgetItem.objects.get(item_id=item_id)
            current_user = PortalUser.objects.get(id=request.user.id)
            user_wallet = PortalUserBalance.objects.get(pu=current_user)

            if user_wallet.main_wallet < total_amount:
                return Response({'status': 'fail', 'message': 'Not enough balance in main wallet.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                ref_code = f'PUR-{uuid.uuid4().hex[:10].upper()}'
                GadgetPurchase.objects.create(
                    item=item,
                    per_unit_cost=item.cost,
                    ordered_qty=qty,
                    remaining_qty=qty,
                    grand_total=total_amount,
                    order_ref=ref_code,
                    buyer_name=current_user.pu_name,
                    buyer_phone=current_user.pu_contact_no,
                    initiated_by=request.user.id
                )

                user_wallet.main_wallet -= total_amount
                user_wallet.lien_wallet += total_amount
                user_wallet.save()

                HoldTransaction.objects.create(
                    ref_id=ref_code,
                    user=current_user,
                    hold_amount=total_amount
                )

            return Response({'status': 'success', 'message': 'Purchase order placed successfully.'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list_all_purchases(self, request):
        try:
            page_num = int(request.data.get('page_num', 1))
            page_size = int(request.data.get('page_size', 10))
            search_term = request.data.get('search', '')
            status = request.data.get('status', '')
            order_ref = request.data.get('order_ref', '')
            tracking = request.data.get('tracking', '')

            token = request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
            payload = TokenBackend(algorithm='HS256').decode(token, verify=False)
            user_role = payload.get('role')

            if user_role == 'ADMIN':
                db = get_database_from_domain()
                admin = Admin.objects.get(db_name=db)
                switch_to_database(admin.db_name)
                qs = GadgetPurchase.objects.filter(buyer_phone=admin.contact_no).order_by('-initiated_on')
            else:
                qs = GadgetPurchase.objects.all().order_by('-initiated_on')

            if order_ref:
                qs = qs.filter(order_ref__iexact=order_ref)
            if tracking:
                qs = qs.filter(tracking_no__iexact=tracking)
            if search_term:
                qs = qs.filter(Q(buyer_name__icontains=search_term) | Q(order_ref__icontains=search_term))
            if status:
                qs = qs.filter(status=status)

            qs = apply_date_range_filter(request, qs)

            paginator = Paginator(qs, page_size)
            try:
                page_data = paginator.page(page_num)
            except EmptyPage:
                return Response({'status': 'fail', 'message': 'Page out of range.'}, status=status.HTTP_404_NOT_FOUND)

            serialized = PurchaseRecordSerializer(page_data, many=True).data
            host = request.META.get('HTTP_HOST')

            for rec in serialized:
                item_obj = GadgetItem.objects.filter(item_id=rec['item']).first()
                if item_obj:
                    img_path = item_obj.images.get("device_image") if item_obj.images else None
                    rec['item_title'] = item_obj.title
                    rec['item_info'] = item_obj.info
                    rec['item_image_url'] = f"https://{host}/media/{img_path}" if img_path else None

                rec['initiated_on'] = datetime.strptime(rec['initiated_on'], "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%d %H:%M:%S")

            return Response({
                'status': 'success',
                'message': 'Purchase records retrieved.',
                'data': {
                    'total_pages': paginator.num_pages,
                    'current_page': page_num,
                    'total_records': paginator.count,
                    'records': serialized
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            purchase_id = request.data.get('purchase_id')
            new_status = request.data.get('status')
            tracking_no = request.data.get('tracking_no', '')
            courier = request.data.get('courier', '')
            serial_codes = request.data.get('serials', '')

            if not purchase_id or not new_status:
                return Response({'status': 'fail', 'message': 'Purchase ID and status required.'}, status=status.HTTP_400_BAD_REQUEST)

            purchase = GadgetPurchase.objects.get(purchase_id=purchase_id)
            admin = Admin.objects.get(contact_no=purchase.buyer_phone)
            switch_to_database(admin.db_name)

            portal_user = PortalUser.objects.using(admin.db_name).get(pu_contact_no=admin.contact_no)
            wallet = PortalUserBalance.objects.using(admin.db_name).get(pu=portal_user)

            if request.user.pu_role == 'ADMIN' and new_status == 'CANCELLED' and purchase.status == 'PENDING':
                refund_amt = Decimal(str(purchase.grand_total))
                wallet.main_wallet += refund_amt
                wallet.lien_wallet -= refund_amt
                wallet.save(using=admin.db_name)
                purchase.status = 'CANCELLED'
                purchase.save()
                return Response({'status': 'success', 'message': 'Purchase cancelled.'})

            if purchase.status not in ['PENDING', 'PARTIALLY APPROVED']:
                return Response({'status': 'fail', 'message': 'Only pending orders can be processed.'})

            if new_status == 'REJECTED':
                refund = Decimal(purchase.remaining_qty) * purchase.per_unit_cost
                wallet.main_wallet += refund
                wallet.lien_wallet -= refund
                wallet.save(using=admin.db_name)
                purchase.status = 'REJECTED'
                purchase.save()
                return Response({'status': 'success', 'message': 'Purchase rejected.'})

            if new_status in ['APPROVED', 'PARTIALLY APPROVED']:
                serial_list = [s.strip() for s in serial_codes.split(',') if s.strip()]
                if not serial_list:
                    return Response({'status': 'fail', 'message': 'Serial numbers required for approval.'})

                approve_count = len(serial_list)
                deduct_amount = purchase.per_unit_cost * approve_count

                if wallet.lien_wallet < deduct_amount:
                    return Response({'status': 'fail', 'message': 'Insufficient lien balance.'})

                with transaction.atomic():
                    valid_serials = ItemSerial.objects.filter(
                        item=purchase.item,
                        serial_code__in=serial_list,
                        deleted=False,
                        deactivated=False
                    )

                    if valid_serials.count() != approve_count:
                        return Response({'status': 'fail', 'message': 'Invalid or duplicate serials.'})

                    wallet.lien_wallet -= deduct_amount
                    wallet.save(using=admin.db_name)

                    purchase.item.available_stock -= approve_count
                    purchase.item.save()

                    ad_item, _ = AdGadgetItem.objects.using(admin.db_name).get_or_create(
                        title=purchase.item.title,
                        defaults={
                            'category': AdGadgetCategory.objects.using(admin.db_name).filter(name=purchase.item.category.name).first(),
                            'info': purchase.item.info,
                            'cost': purchase.item.cost,
                            'images': purchase.item.images,
                            'stock': approve_count,
                            'created_by': portal_user.id
                        }
                    )
                    ad_item.stock += approve_count
                    ad_item.save(using=admin.db_name)

                    current_serials = purchase.allocated_serials.get('serial_numbers', []) if purchase.allocated_serials else []
                    new_serials = []
                    for s in valid_serials:
                        s.deactivated = True
                        s.assigned_user = admin.pk
                        s.save()
                        new_serials.append(s.serial_code)

                        AdItemSerial.objects.using(admin.db_name).create(
                            item=ad_item,
                            serial_code=s.serial_code,
                            created_by=portal_user.id
                        )

                    purchase.allocated_serials = {'serial_numbers': current_serials + new_serials}
                    purchase.tracking_no = tracking_no
                    purchase.shipping_partner = courier
                    purchase.status = 'APPROVED' if approve_count == purchase.remaining_qty else 'PARTIALLY APPROVED'
                    purchase.remaining_qty -= approve_count
                    purchase.save()

                    for cat in GadgetCategory.objects.filter(deleted=False, inactive=False):
                        AdGadgetCategory.objects.using(admin.db_name).get_or_create(
                            name=cat.name,
                            parent=cat.parent,
                            defaults={'info': cat.details}
                        )

                    label = super_admin_action_label("Gadget Purchase", deduct_amount, purchase.order_ref, "Admin")
                    WalletHistory.objects.using(admin.db_name).create(
                        pu=portal_user,
                        action_type='Debit for Gadget',
                        wl_label=label,
                        effectvie_wallet='main_wallet',
                        effectvie_amt=deduct_amount,
                        effective_type='DR',
                        current_balance=wallet.main_wallet,
                        wl_trn_dt=timezone.now()
                    )

                return Response({'status': 'success', 'message': f'Purchase {purchase.status.lower()} successfully.'})

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)