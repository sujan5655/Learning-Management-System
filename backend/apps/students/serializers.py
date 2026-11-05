from rest_framework import serializers

from apps.courses.models import Enrollment


class StudentEnrollmentSerializer(serializers.ModelSerializer):

    course_title = serializers.CharField(
        source="course.title",
        read_only=True
    )

    course_slug = serializers.CharField(
        source="course.slug",
        read_only=True
    )

    course_thumbnail = serializers.ImageField(
        source="course.thumbnail",
        read_only=True
    )

    category_name = serializers.CharField(
        source="course.category.name",
        read_only=True
    )

    course_level = serializers.CharField(
        source="course.level",
        read_only=True
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "course",
            "course_title",
            "course_slug",
            "course_thumbnail",
            "category_name",
            "course_level",
            "status",
            "enrolled_at",
            "updated_at",
        ]

        read_only_fields = fields