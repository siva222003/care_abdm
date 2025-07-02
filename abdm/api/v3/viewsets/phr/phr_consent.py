from logging import getLogger

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from abdm.api.v3.serializers.phr.phr_consent import (
    PhrConsentApprovalRequestSerializer,
    PhrConsentDenySerializer,
    PhrConsentRevokeSerializer,
)
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

    serializer_action_classes = {
        "phr_consent__request__approve": PhrConsentApprovalRequestSerializer,
        "phr_consent__request__deny": PhrConsentDenySerializer,
        "phr_consent__request__revoke": PhrConsentRevokeSerializer,
    }

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

    @action(detail=False, methods=["get"], url_path="requests")
    def phr_consent__requests(self, request):
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

        return Response(consent_requests, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=False,
        methods=["get"],
        url_path="request/(?P<request_id>[^/.]+)",
    )
    def phr_consent__request(self, request, request_id):
        x_token = self._get_x_token(request)

        consent_request = PhrConsentService.phr__consent__request(
            {"x_token": x_token, "request_id": request_id}
        )

        return Response(consent_request, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"], url_path="artefacts")
    def phr_consent__artefacts(self, request):
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

        return Response(consent_artefacts, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=False,
        methods=["get"],
        url_path="request/(?P<request_id>[^/.]+)/artefacts",
    )
    def phr_consent__request__artefacts(self, request, request_id):
        x_token = self._get_x_token(request)
        consent_request_artefacts = PhrConsentService.phr__consent__request__artefacts(
            {"x_token": x_token, "request_id": request_id}
        )

        return Response(consent_request_artefacts, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=False,
        methods=["get"],
        url_path="artefact/(?P<artefact_id>[^/.]+)",
    )
    def phr_consent__artefact(self, request, artefact_id):
        x_token = self._get_x_token(request)
        consent_artefact = PhrConsentService.phr__consent__artefact(
            {"x_token": x_token, "artefact_id": artefact_id}
        )

        return Response(consent_artefact, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=False,
        methods=["post"],
        url_path="request/(?P<request_id>[^/.]+)/approve",
    )
    def phr_consent__request__approve(self, request, request_id):
        validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        result = PhrConsentService.phr__consent__request__approve(
            {
                "x_token": x_token,
                "request_id": request_id,
                "consents": validated_data.get("consents"),
            }
        )

        return Response(
            {"detail": result.get("message")},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="request/(?P<request_id>[^/.]+)/deny",
    )
    def phr_consent__request__deny(self, request, request_id):
        validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        PhrConsentService.phr__consent__request__deny(
            {
                "x_token": x_token,
                "request_id": request_id,
                "reason": validated_data.get("reason"),
            }
        )

        return Response(
            {"detail": "Consent request denied successfully"},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["post"], url_path="revoke")
    def phr_consent__request__revoke(self, request):
        validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        result = PhrConsentService.phr__consent__request__revoke(
            {
                "x_token": x_token,
                "consents": validated_data.get("consents"),
            }
        )

        return Response(
            {"detail": result.get("message")},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["post"], url_path="auto-approve")
    def phr_consent__auto__approve(self, request):
        # validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        result = PhrConsentService.phr__consent__auto__approve(
            {
                "x_token": x_token,
                "auto_approve_request": {
                    "isApplicableForAllHIPs": True,
                    "hiu": {"id": "IN3210000018"},
                    "includedSources": [
                        {
                            "purpose": {
                                "text": "Self Requested",
                                "code": "PATRQT",
                                "refUri": "www.abdm.gov.in",
                            },
                            "hip": None,
                            "period": {
                                "from": "2025-07-02T02:59:59.059Z",
                                "to": "2125-06-08T02:59:29.059Z",
                            },
                        }
                    ],
                    "excludedSources": None,
                },
            }
        )

        return Response(
            {"detail": result.get("message")},
            status=status.HTTP_202_ACCEPTED,
        )
