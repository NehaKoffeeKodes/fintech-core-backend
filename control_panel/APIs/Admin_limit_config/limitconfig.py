from ...views import*

class TransactionRuleManagementView(APIView):
    authentication_classes = [SecureJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            if 'page_number' in request.data:
                return self.get_all_rules(request)
            
            elif 'user_id' in request.data and 'provider_id' in request.data:
                return self.add_new_rule(request)
            
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid request parameters'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_new_rule(self, request):
        try:
            user_id = request.data.get('user_id')
            provider_id = request.data.get('provider_id')
            single_max = request.data.get('single_txn_limit')
            daily_max = request.data.get('daily_limit')
            monthly_max = request.data.get('monthly_limit')
            daily_count = request.data.get('daily_txn_count')
            monthly_count = request.data.get('monthly_txn_count')
            required = ['user_id', 'provider_id', 'single_txn_limit', 'daily_limit', 
                       'monthly_limit', 'daily_txn_count', 'monthly_txn_count']
            for field in required:
                if request.data.get(field) is None:
                    return Response({
                        'status': 'fail',
                        'message': f'{field} is required'
                    }, status=status.HTTP_400_BAD_REQUEST)

            if LimitConfig.objects.filter(
                user_account_id=user_id, 
                provider_id=provider_id
            ).exists():
                return Response({
                    'status': 'fail',
                    'message': 'A rule already exists for this user and provider'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                LimitConfig.objects.create(
                    user_account_id=user_id,
                    provider_id=provider_id,
                    max_per_transaction=Decimal(single_max),
                    max_daily_total=Decimal(daily_max),
                    max_monthly_total=Decimal(monthly_max),
                    max_daily_transactions=daily_count,
                    max_monthly_transactions=monthly_count,
                    is_enabled=True
                )

            return Response({
                'status': 'success',
                'message': 'Transaction rule created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error creating rule: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_all_rules(self, request):
        try:
            page = int(request.data.get('page_number', 1))
            size = int(request.data.get('page_size', 10))
            user_name = request.data.get('user_name')
            provider_name = request.data.get('provider_name')
            rules = LimitConfig.objects.select_related('user_account', 'provider').order_by('-rule_id')

            if user_name:
                rules = rules.filter(user_account__username__icontains=user_name)
            if provider_name:
                rules = rules.filter(provider__name__icontains=provider_name)

            paginator = Paginator(rules, size)
            try:
                current_page = paginator.page(page)
            except:
                current_page = paginator.page(paginator.num_pages)

            serializer = LimitConfigSerializer(current_page, many=True)

            response_data = {
                'current_page': current_page.number,
                'total_pages': paginator.num_pages,
                'total_records': paginator.count,
                'results': serializer.data
            }

            return Response({
                'status': 'success',
                'message': 'Transaction rules fetched successfully',
                'data': response_data
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({
                'status': 'fail',
                'message': 'page_number and page_size must be valid numbers'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)