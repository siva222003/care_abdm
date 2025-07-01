from typing import Literal, TypedDict


class PhrConsentRequestsBody(TypedDict):
    x_token: str
    limit: int
    offset: int
    status: list[Literal["ALL", "REQUESTED", "EXPIRED", "REVOKED", "GRANTED", "DENIED"]]


class PhrConsentRequestsResponse(TypedDict):
    pass


class PhrConsentRequestBody(TypedDict):
    x_token: str
    request_id: str


class PhrConsentRequestResponse(TypedDict):
    pass


class PhrConsentArtefactsBody(TypedDict):
    x_token: str
    limit: int
    offset: int
    status: list[Literal["ALL", "REQUESTED", "EXPIRED", "REVOKED", "GRANTED", "DENIED"]]


class PhrConsentArtefactsResponse(TypedDict):
    pass


class PhrConsentRequestApproveBody(TypedDict):
    x_token: str
    request_id: str
    consents: list[dict]


class PhrConsentRequestApproveResponse(TypedDict):
    message: str
    consents: list[str]


class PhrConsentRequestDenyBody(TypedDict):
    x_token: str
    request_id: str
    reason: str


class PhrConsentRequestDenyResponse(TypedDict):
    pass


class PhrConsentRequestRevokeBody(TypedDict):
    x_token: str
    consents: list[str]


class PhrConsentRequestRevokeResponse(TypedDict):
    message: str
