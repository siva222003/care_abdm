from rest_framework.serializers import (
    CharField,
    ChoiceField,
    DateTimeField,
    IntegerField,
    ListField,
    Serializer,
    UUIDField,
    ValidationError,
)

from abdm.models.base import AccessMode, HealthInformationType


class CareContextSerializer(Serializer):
    patient_reference = UUIDField(required=True)
    care_context_reference = CharField(required=True, max_length=255)

    def to_representation(self, instance):
        return {
            "patientReference": instance.get("patient_reference"),
            "careContextReference": instance.get("care_context_reference"),
        }


class HipSerializer(Serializer):
    id = CharField(required=True, max_length=50)
    name = CharField(required=True, max_length=255)
    type = CharField(required=True, max_length=10)


class DateRangeSerializer(Serializer):
    from_time = DateTimeField(source="from_time", required=True)
    to_time = DateTimeField(source="to_time", required=True)

    def to_representation(self, instance):
        return {"from": instance.get("from_time"), "to": instance.get("to_time")}


class FrequencySerializer(Serializer):
    unit = ChoiceField(choices=["HOUR", "DAY", "WEEK", "MONTH", "YEAR"], required=True)
    value = IntegerField(required=True, min_value=1)
    repeats = IntegerField(required=True, min_value=0)


class PermissionSerializer(Serializer):
    access_mode = ChoiceField(choices=AccessMode.choices, required=True)
    date_range = DateRangeSerializer(required=True)
    data_erase_at = DateTimeField(required=True)
    frequency = FrequencySerializer(required=True)

    def to_representation(self, instance):
        return {
            "accessMode": instance.get("access_mode"),
            "dateRange": instance.get("date_range"),
            "dataEraseAt": instance.get("data_erase_at"),
            "frequency": instance.get("frequency"),
        }


class PhrConsentApprovalSerializer(Serializer):
    care_contexts = ListField(
        child=CareContextSerializer(), required=True, allow_empty=False
    )
    hi_types = ListField(
        child=ChoiceField(choices=HealthInformationType.choices),
        required=True,
        allow_empty=False,
    )
    hip = HipSerializer(required=True)
    permission = PermissionSerializer(required=True)

    def to_representation(self, instance):
        return {
            "careContexts": instance.get("care_contexts"),
            "hiTypes": instance.get("hi_types"),
            "hip": instance.get("hip"),
            "permission": instance.get("permission"),
        }


class PhrConsentApprovalRequestSerializer(Serializer):
    consents = ListField(
        child=PhrConsentApprovalSerializer(),
        required=True,
        allow_empty=False,
    )

    def validate_consents(self, value):
        if not value:
            raise ValidationError("At least one consent object must be provided.")

        for i, consent in enumerate(value):
            if not consent.get("careContexts"):
                raise ValidationError(f"Consent {i + 1}: careContexts cannot be empty.")

            if not consent.get("hiTypes"):
                raise ValidationError(f"Consent {i + 1}: hiTypes cannot be empty.")

        return value


class PhrConsentDenySerializer(Serializer):
    reason = CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        default="Successfully denied the consent request",
    )


class PhrConsentRevokeSerializer(Serializer):
    consents = ListField(
        child=UUIDField(required=True), required=True, allow_empty=False
    )
