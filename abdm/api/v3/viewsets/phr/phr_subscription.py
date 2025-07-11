from logging import getLogger

from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from abdm.api.v3.serializers.phr.phr_subscription import (
    PhrSubscriptionEditSerializer,
    PhrSubscriptionRequestApproveSerializer,
    PhrSubscriptionRequestDenySerializer,
    PhrSubscriptionStatusUpdateSerializer,
)
from abdm.authentication import ABDMAuthentication
from abdm.service.helper import (
    PHR_ACCESS_TOKEN_CACHE_TIMEOUT,
    PHR_ACCESS_TOKEN_PREFIX,
    PHR_REFRESH_TOKEN_CACHE_TIMEOUT,
    PHR_REFRESH_TOKEN_PREFIX,
)
from abdm.service.v3.phr.phr_subscription import PhrSubscriptionService
from abdm.service.v3.phr.profile import PhrProfileService

logger = getLogger(__name__)


@extend_schema(tags=["PHR Subscription"])
class PhrSubscriptionViewSet(GenericViewSet):
    permission_classes = []

    serializer_action_classes = {
        "phr_subscription__request__approve": PhrSubscriptionRequestApproveSerializer,
        "phr_subscription__request__deny": PhrSubscriptionRequestDenySerializer,
        "phr_subscription__status__update": PhrSubscriptionStatusUpdateSerializer,
        "phr_subscription__edit": PhrSubscriptionEditSerializer,
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

    def _get_query_params(self, request):
        status_param = request.query_params.get("status", "ALL")

        try:
            limit = max(int(request.query_params.get("limit", -1)), -1)
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except (ValueError, TypeError):
            return None, None, None

        valid_statuses = ["ALL", "REQUESTED", "EXPIRED", "REVOKED", "GRANTED", "DENIED"]

        if status_param not in valid_statuses:
            return None, None, None

        return status_param, limit, offset

    @action(detail=False, methods=["get"], url_path="requests")
    def phr_subscription__requests(self, request):
        x_token = self._get_x_token(request)
        status_param, limit, offset = self._get_query_params(request)

        if status_param is None:
            return Response(
                {"size": 0, "requests": []}, status=status.HTTP_400_BAD_REQUEST
            )

        subscription_requests = PhrSubscriptionService.phr__subscription__requests(
            {
                "x_token": x_token,
                "status": status_param,
                "limit": limit,
                "offset": offset,
            }
        )

        return Response(subscription_requests, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        url_path="request/(?P<request_id>[^/.]+)",
    )
    def phr_subscription__request(self, request, request_id):
        x_token = self._get_x_token(request)

        subscription_request = PhrSubscriptionService.phr__subscription__request(
            {"x_token": x_token, "request_id": request_id}
        )

        return Response(subscription_request, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        url_path="artefact/(?P<subscription_id>[^/.]+)",
    )
    def phr_subscription__artefact(self, request, subscription_id):
        x_token = self._get_x_token(request)

        subscription_artefact = PhrSubscriptionService.phr__subscription__artefact(
            {"x_token": x_token, "subscription_id": subscription_id}
        )

        return Response(subscription_artefact, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="request/(?P<request_id>[^/.]+)/approve",
    )
    def phr_subscription__request__approve(self, request, request_id):
        validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        result = PhrSubscriptionService.phr__subscription__request__approve(
            {
                "x_token": x_token,
                "request_id": request_id,
                "subscription": validated_data.get("subscription"),
            }
        )

        return Response(
            {"detail": result.get("message")},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="request/(?P<request_id>[^/.]+)/deny",
    )
    def phr_subscription__request__deny(self, request, request_id):
        validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        result = PhrSubscriptionService.phr__subscription__request__deny(
            {
                "x_token": x_token,
                "request_id": request_id,
                "reason": validated_data.get("reason"),
            }
        )

        return Response(
            {"detail": result.get("message")},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="(?P<subscription_id>[^/.]+)/update_status",
    )
    def phr_subscription__status__update(self, request, subscription_id):
        validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        result = PhrSubscriptionService.phr__subscription__status__update(
            {
                "x_token": x_token,
                "subscription_id": subscription_id,
                "enable": validated_data.get("enable"),
            }
        )

        return Response(
            {"detail": result.get("message")},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["put"],
        url_path="(?P<subscription_id>[^/.]+)/edit",
    )
    def phr_subscription__edit(self, request, subscription_id):
        validated_data = self.validate_request(request)
        x_token = self._get_x_token(request)

        result = PhrSubscriptionService.phr__subscription__edit(
            {
                "x_token": x_token,
                "subscription_id": subscription_id,
                "hiu_id": validated_data.get("hiu_id"),
                "subscription_edit_request": validated_data.get(
                    "subscription_edit_request"
                ),
            }
        )

        return Response(
            {"detail": result.get("message")},
            status=status.HTTP_200_OK,
        )

    """
    HIU SUBSCRIPTION REQUEST ACTIONS
    """

    @action(
        detail=False,
        methods=["post"],
        url_path="request/hiu/init",
    )
    def phr_subscription__request__init(self, request):
        # validated_data = self.validate_request(request)
        PhrSubscriptionService.phr__subscription__request__init(request.data)
        return Response(
            {"detail": "Subscription request initiated successfully"},
            status=status.HTTP_200_OK,
        )


class PhrSubscriptionCallbackViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return super().get_serializer_class()

    def validate_request(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return serializer.validated_data

    @action(
        detail=False,
        methods=["post"],
        url_path="hiu/hiecm/subscription-requests/on-init",
    )
    def phr_subscription__request__on__init(self, request):
        # validated_data = self.validate_request(request)
        logger.info(f"SUBSCRIPTION ON INIT: {request.data}")

        # TODO: Implement this
        return Response(
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="hiu/subscription-requests/hiu/notify",
    )
    def phr_subscription__request__on__notify(self, request):
        logger.info(f"SUBSCRIPTION NOTIFY: {request.data}")
        validated_data = request.data.get("notification")

        PhrSubscriptionService.phr__subscription__request__on__notify(
            {
                "acknowledgement": {
                    "status": "OK",
                    "subscriptionRequestId": validated_data.get(
                        "subscriptionRequestId"
                    ),
                },
                "response": {
                    "requestId": validated_data.get("subscription").get("requestId")
                },
            }
        )
        return Response(
            status=status.HTTP_200_OK,
        )
