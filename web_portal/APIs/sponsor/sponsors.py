from ...views import*

class SponsorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data

        if 'page' in payload or 'limit' in payload:
            return self.fetch_sponsors(request)

        elif all(k in payload for k in ['title', 'details']) or request.FILES.getlist('banner'):
            return self.register_new_sponsor(request)

        return Response({
            "status": "failed",
            "error": "Invalid payload structure"
        }, status=status.HTTP_400_BAD_REQUEST)

    def register_new_sponsor(self, request):
        try:
            name = request.data.get('title')
            description = request.data.get('details')
            images = request.FILES.getlist('banner')

            if Sponsor.objects.filter(title__iexact=name, is_archived=False).exists():
                return Response({
                    "status": "failed",
                    "error": f"Sponsor titled '{name}' already exists."
                }, status=status.HTTP_409_CONFLICT)

            image_path = self.upload_images(images, 'uploads/sponsors/banners/')
            if image_path is False:
                return Response({
                    "status": "failed",
                    "error": "Only JPG, JPEG, or PNG images are allowed."
                }, status=status.HTTP_400_BAD_REQUEST)

            Sponsor.objects.create(
                title=name,
                details=description,
                banner_image=image_path[0] if image_path else None,
                added_by=request.user
            )

            return Response({
                "status": "success",
                "message": "Sponsor registered successfully"
            }, status=status.HTTP_201_CREATED)

        except Exception as exc:
            return Response({
                "status": "error",
                "error": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_sponsors(self, request):
        response_template = {
            "total_count": 0,
            "total_pages": 0,
            "current_page": 1,
            "page_size": 10,
            "items": []
        }

        try:
            page = int(request.data.get('page', 1))
            limit = int(request.data.get('limit', 10))
            sponsor_id = request.data.get('sponsor_id')
            keyword = request.data.get('keyword')

            if page < 1 or limit < 1:
                return Response({
                    "status": "failed",
                    "error": "Page and limit must be positive integers"
                }, status=status.HTTP_400_BAD_REQUEST)

            queryset = Sponsor.objects.filter(is_archived=False).order_by('-sponsor_code')

            if sponsor_id:
                queryset = queryset.filter(sponsor_code=sponsor_id)
                if not queryset.exists():
                    return Response({
                        "status": "failed",
                        "error": "No sponsor found with given ID"
                    }, status=status.HTTP_404_NOT_FOUND)

            elif keyword:
                queryset = queryset.filter(
                    Q(title__icontains=keyword) | Q(details__icontains=keyword)
                )

            total = queryset.count()
            total_pages = (total + limit - 1) // limit
            start = (page - 1) * limit
            end = start + limit
            paginated = queryset[start:end]

            serialized = SponsorDataSerializer(paginated, many=True, context={'request': request})

            base_url = request.build_absolute_uri('/').rstrip('/')
            for item in serialized.data:
                if item.get('banner_image'):
                    raw_path = item['banner_image'].lstrip('/')
                    if raw_path.startswith('uploads/'):
                        raw_path = raw_path.replace('uploads/', '', 1)
                    item['banner_image'] = f"{base_url}/uploads/sponsors/banners/{os.path.basename(raw_path)}"

            response_template.update({
                "total_count": total,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": limit,
                "items": serialized.data
            })

            return Response({
                "status": "success",
                "message": "Sponsors retrieved",
                "data": response_template
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({
                "status": "failed",
                "error": "Invalid page or limit value"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({
                "status": "error",
                "error": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request):
        try:
            sid = request.data.get('sponsor_id')
            if not sid or not str(sid).isdigit():
                return Response({
                    "status": "failed",
                    "error": "Valid sponsor_id is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            sponsor = Sponsor.objects.filter(sponsor_code=sid, is_archived=False).first()
            if not sponsor:
                return Response({
                    "status": "failed",
                    "error": "Sponsor not found"
                }, status=status.HTTP_404_NOT_FOUND)

            new_title = request.data.get('title')
            new_desc = request.data.get('details')
            new_images = request.FILES.getlist('banner')

            if new_title and new_title.lower() != sponsor.title.lower():
                if Sponsor.objects.filter(title__iexact=new_title, is_archived=False).exclude(sponsor_code=sid).exists():
                    return Response({
                        "status": "failed",
                        "error": "Another sponsor with this title already exists"
                    }, status=status.HTTP_409_CONFLICT)
                sponsor.title = new_title

            if new_desc is not None:
                sponsor.details = new_desc

            if new_images:
                paths = self.upload_images(new_images, 'uploads/sponsors/banners/')
                if paths is False:
                    return Response({
                        "status": "failed",
                        "error": "Invalid image format. Only PNG/JPG allowed."
                    }, status=status.HTTP_400_BAD_REQUEST)
                sponsor.banner_image = paths[0]

            if not any([new_title, new_desc, new_images]):
                active_count = Sponsor.objects.filter(is_hidden=True, is_archived=False).count()
                if active_count <= 1 and sponsor.is_hidden:
                    return Response({
                        "status": "failed",
                        "error": "At least one sponsor must remain visible"
                    }, status=status.HTTP_400_BAD_REQUEST)
                sponsor.is_hidden = not sponsor.is_hidden

            sponsor.last_updated = timezone.now()
            sponsor.save()

            msg = "Sponsor visibility toggled" if not any([new_title, new_desc, new_images]) else "Sponsor updated"
            return Response({
                "status": "success",
                "message": msg
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                "status": "error",
                "error": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            with transaction.atomic():
                sid = request.data.get('sponsor_id')
                if not sid:
                    return Response({
                        "status": "failed",
                        "error": "sponsor_id required"
                    }, status=status.HTTP_400_BAD_REQUEST)

                sponsor = Sponsor.objects.filter(sponsor_code=sid, is_archived=False).first()
                if not sponsor:
                    return Response({
                        "status": "failed",
                        "error": "Sponsor not found"
                    }, status=status.HTTP_404_NOT_FOUND)

                visible_count = Sponsor.objects.filter(is_hidden=True, is_archived=False).count()
                if visible_count <= 1 and sponsor.is_hidden:
                    return Response({
                        "status": "failed",
                        "error": "Cannot remove last visible sponsor"
                    }, status=status.HTTP_400_BAD_REQUEST)

                sponsor.is_archived = True
                sponsor.is_hidden = False
                sponsor.save()

                return Response({
                    "status": "success",
                    "message": "Sponsor removed successfully"
                }, status=status.HTTP_200_OK)

        except Exception as exc:
            return Response({
                "status": "error",
                "error": str(exc)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def upload_images(self, file_list, folder):
        if not file_list:
            return []

        os.makedirs(folder, exist_ok=True)
        saved_paths = []

        for file in file_list:
            if not hasattr(file, 'name'):
                return False
            ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
            if ext not in ['jpg', 'jpeg', 'png']:
                return False

            clean_name = ''.join(c for c in file.name if c.isalnum() or c in '._-')
            full_path = os.path.join(folder, clean_name)

            with open(full_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            saved_paths.append(f"/{full_path}")

        return saved_paths



class PublicSponsorView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            host = request.META.get('HTTP_HOST', 'localhost')
            allowed_hosts = ['yourdomain.com', 'localhost']  

            if host not in allowed_hosts:
                return Response({"status": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

            sponsors = Sponsor.objects.filter(is_hidden=True, is_archived=False)
            if not sponsors.exists():
                return Response({
                    "status": "empty",
                    "message": "No active sponsors"
                }, status=status.HTTP_200_OK)

            data = SponsorDataSerializer(sponsors, many=True, context={'request': request}).data

            base = f"http://{host}"
            for item in data:
                if item.get('banner_image'):
                    path = item['banner_image'].lstrip('/')
                    item['banner_image'] = f"{base}/{path}"

            return Response({
                "status": "success",
                "data": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)