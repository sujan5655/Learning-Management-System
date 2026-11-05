from rest_framework import serializers

from apps.courses.models import Course, Enrollment


class InstructorCourseSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    total_students = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "thumbnail",
            "category_name",
            "level",
            "status",
            "total_students",
            "created_at",
            "published_at",
        ]

    def get_total_students(self, obj):

        return Enrollment.objects.filter(
            course=obj,
            status=Enrollment.Status.ACTIVE
        ).values("student").distinct().count()


from apps.courses.models import Enrollment


class InstructorStudentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(
        source="student.email",
        read_only=True
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student_name",
            "student_email",
            "status",
            "enrolled_at",
        ]

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.email