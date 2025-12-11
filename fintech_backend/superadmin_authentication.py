from ..web_portal.views import*


class SecureAdminAuth(JWTAuthentication):

    def authenticate(self, request: Request) -> Optional[Tuple[AdminAccount, str]]:
        header_token = self._extract_header_token(request)
        if not header_token:
            return None

        raw_token = self._parse_raw_token(header_token)
        if not raw_token:
            return None

        try:
            admin_user = self._validate_admin_token(request, raw_token)
            if not admin_user:
                raise exceptions.AuthenticationFailed('Invalid or unauthorized token')

            return (admin_user, raw_token)

        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
            raise exceptions.AuthenticationFailed('Authentication service temporarily unavailable')

    def _extract_header_token(self, request: Request) -> Optional[str]:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        return auth_header.split('Bearer ', 1)[1].strip()

    def _parse_raw_token(self, token_str: str) -> Optional[str]:
        if not token_str or len(token_str) < 20:
            return None
        return token_str

    def _validate_admin_token(self, request: Request, raw_token: str) -> Optional[AdminAccount]:
        try:
            token = AccessToken(raw_token)
            payload = token.payload

            user_id = self._extract_user_id(payload)
            if not user_id:
                return None

            if not self._has_admin_role(payload):
                return None

            admin_user = self._get_admin_user(user_id)
            if not admin_user:
                return None

            self._enforce_security_policy(request, admin_user, payload)
            return admin_user

        except InvalidToken:
            return None
        except Exception as e:
            return None

    def _extract_user_id(self, payload: dict) -> Optional[int]:
        for claim in ('user_id', 'sub', 'uid', 'id'):
            value = payload.get(claim)
            if isinstance(value, int):
                return value
        return None

    def _has_admin_role(self, payload: dict) -> bool:
        role = payload.get('role') or payload.get('scope') or payload.get('type') or ''
        return str(role).upper() in ('SUPERADMIN', 'ADMIN', 'SUPER_ADMIN')

    def _get_admin_user(self, user_id: int) -> Optional[AdminAccount]:
        try:
            return AdminAccount.objects.only('id', 'username', 'is_active', 'is_deleted').get(
                id=user_id, is_active=True, is_deleted=False
            )
        except AdminAccount.DoesNotExist:
            return None

    def _enforce_security_policy(self, request: Request, user: AdminAccount, payload: dict):
        if not user.is_active:
            raise exceptions.AuthenticationFailed('Account is deactivated')
        if user.is_deleted:
            raise exceptions.AuthenticationFailed('Account has been removed')
        if not getattr(user, 'has_changed_initial_password', False):
            raise exceptions.AuthenticationFailed('Initial password not changed')

    @classmethod
    def generate_admin_token(cls, admin_user: AdminAccount, lifetime_seconds: int = 86400) -> str:
        token = AccessToken.for_user(admin_user)
        token.set_exp(lifetime=timedelta(seconds=lifetime_seconds))

        token['user_id'] = admin_user.id
        token['role'] = 'SUPERADMIN'
        token['username'] = admin_user.username
        token['scope'] = 'admin superadmin'
        token['permissions'] = 'full_access'

        return str(token)