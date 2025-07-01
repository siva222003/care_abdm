from logging import getLogger

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from abdm.service.helper import (
    PHR_ACCESS_TOKEN_CACHE_TIMEOUT,
    PHR_ACCESS_TOKEN_PREFIX,
    PHR_REFRESH_TOKEN_CACHE_TIMEOUT,
    PHR_REFRESH_TOKEN_PREFIX,
)
from abdm.service.v3.phr.phr_consent import PhrConsentService
from abdm.service.v3.phr.profile import PhrProfileService
from abdm.settings import plugin_settings as settings

logger = getLogger(__name__)


class PhrConsentViewSet(GenericViewSet):
    permission_classes = []

    serializer_action_classes = {}

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return super().get_serializer_class()

    def validate_request(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return serializer.validated_data

    def _get_x_token(self, request):
        # abha_address = self._normalize_abha_address(request.user.abha_address)
        abha_address = "dora8sbx@sbx"

        access_key = f"{PHR_ACCESS_TOKEN_PREFIX}{abha_address}"
        refresh_key = f"{PHR_REFRESH_TOKEN_PREFIX}{abha_address}"

        x_token = cache.get(access_key)
        if x_token:
            return x_token

        refresh_token = cache.get(refresh_key)

        result = PhrProfileService.phr__request__token({"r_token": refresh_token})
        tokens = result.get("tokens") or {}

        access_token = tokens.get("token")
        new_refresh_token = tokens.get("refreshToken")

        cache.set(access_key, access_token, timeout=PHR_ACCESS_TOKEN_CACHE_TIMEOUT)
        cache.set(
            refresh_key, new_refresh_token, timeout=PHR_REFRESH_TOKEN_CACHE_TIMEOUT
        )

        return access_token

    def _normalize_abha_address(self, address):
        if not address.endswith(f"@{settings.ABDM_CM_ID}"):
            return f"{address}@{settings.ABDM_CM_ID}"
        return address

    def _get_tokens(self, abha_address, id):
        refresh_token = RefreshToken()
        refresh_token["abha_address"] = self._normalize_abha_address(abha_address)
        refresh_token["id"] = id
        return {
            "refresh_token": str(refresh_token),
            "access_token": str(refresh_token.access_token),
        }

    @action(detail=False, methods=["get"], url_path="get_consent_requests")
    def phr_consent_requests(self, request):
        x_token = self._get_x_token(request)
        status_query = request.query_params.get("status", "ALL")
        limit = request.query_params.get("limit", -1)
        offset = request.query_params.get("offset", 0)

        all_status = ["ALL", "REQUESTED", "EXPIRED", "REVOKED", "GRANTED", "DENIED"]

        if status_query not in all_status:
            return Response(
                {"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
            )

        consent_requests = PhrConsentService.phr__consent__requests(
            {
                "x_token": x_token,
                "status": status_query,
                "limit": limit,
                "offset": offset,
            }
        )

        return Response(
            consent_requests,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="get_consent_request/(?P<request_id>[^/.]+)",
    )
    def phr_consent_request(self, request, request_id):
        x_token = self._get_x_token(request)

        consent_request = PhrConsentService.phr__consent__request(
            {"x_token": x_token, "request_id": request_id}
        )

        return Response(consent_request, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="get_consent_artefacts")
    def phr_consent_artefacts(self, request):
        x_token = self._get_x_token(request)
        status_query = request.query_params.get("status", "ALL")
        limit = request.query_params.get("limit", -1)
        offset = request.query_params.get("offset", 0)

        all_status = ["ALL", "REQUESTED", "EXPIRED", "REVOKED", "GRANTED", "DENIED"]

        if status_query not in all_status:
            return Response(
                {"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
            )

        consent_artefacts = PhrConsentService.phr__consent__artefacts(
            {
                "x_token": x_token,
                "status": status_query,
                "limit": limit,
                "offset": offset,
            }
        )

        return Response(consent_artefacts, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="(?P<request_id>[^/.]+)/approve_consent_request",
    )
    def approve_consent_request(self, request, request_id):
        x_token = self._get_x_token(request)
        consents = request.data.get(
            "consents",
            [
                {
                    "hip": {"id": "IN3210000018"},
                    "hiTypes": [
                        "Prescription",
                        "DiagnosticReport",
                        "OPConsultation",
                        "DischargeSummary",
                        "ImmunizationRecord",
                        "HealthDocumentRecord",
                        "WellnessRecord",
                    ],
                    "careContexts": [],
                    "permission": {
                        "accessMode": "VIEW",
                        "dateRange": {
                            "from": "2025-06-01T02:34:12.000Z",
                            "to": "2025-07-01T02:34:12.000Z",
                        },
                        "dataEraseAt": "2025-07-31T02:34:12.000Z",
                        "frequency": {"unit": "HOUR", "value": 1, "repeats": 0},
                    },
                },
            ],
        )

        consent_request = PhrConsentService.phr__consent__request__approve(
            {"x_token": x_token, "request_id": request_id, "consents": consents}
        )

        return Response(consent_request, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="(?P<request_id>[^/.]+)/deny_consent_request",
    )
    def deny_consent_request(self, request, request_id):
        x_token = self._get_x_token(request)
        reason = request.data.get("reason")

        consent_request = PhrConsentService.phr__consent__request__deny(
            {"x_token": x_token, "request_id": request_id, "reason": reason}
        )

        return Response(consent_request, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="revoke_consent_request")
    def revoke_consent_request(self, request):
        x_token = self._get_x_token(request)
        consents = request.data.get("consents")

        consent_request = PhrConsentService.phr__consent__request__revoke(
            {"x_token": x_token, "consents": consents}
        )

        return Response(consent_request, status=status.HTTP_200_OK)
