from rest_framework import serializers

from .models import InstructorApplication


class InstructorApplicationSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstructorApplication

        fields = [
            "id",
            "expertise",
            "experience",
            "motivation",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
            "reviewed_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
            "reviewed_at",
        ]


class AdminInstructorApplicationSerializer(serializers.ModelSerializer):

    applicant_email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = InstructorApplication

        fields = [
            "id",
            "applicant_email",
            "applicant_name",
            "expertise",
            "experience",
            "motivation",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
            "reviewed_at",
        ]

    def get_applicant_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()