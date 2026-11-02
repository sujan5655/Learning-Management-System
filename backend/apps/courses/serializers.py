
from rest_framework import serializers

from .models import Category, Course, CourseInstructor
from apps.accounts.models import User


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "updated_at",
        ]


class CourseInstructorSerializer(serializers.ModelSerializer):

    instructor_email = serializers.EmailField(
        source="instructor.email",
        read_only=True
    )

    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseInstructor

        fields = [
            "id",
            "instructor",
            "instructor_email",
            "instructor_name",
            "role",
            "assigned_at",
        ]

        read_only_fields = [
            "id",
            "instructor_email",
            "instructor_name",
            "assigned_at",
        ]

    def get_instructor_name(self, obj):
        return (
            f"{obj.instructor.first_name} "
            f"{obj.instructor.last_name}"
        ).strip()


class CourseSerializer(serializers.ModelSerializer):

    instructors = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            role="INSTRUCTOR",
            instructor_status="APPROVED"
        ),
        many=True,
        write_only=True,
        required=False
    )

    instructor_details = CourseInstructorSerializer(
        source="course_instructors",
        many=True,
        read_only=True
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    class Meta:
        model = Course

        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "description",
            "thumbnail",
            "category",
            "category_name",
            "level",
            "status",
            "instructors",
            "instructor_details",
            "published_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "This category is not active."
            )

        return value

    def validate_instructors(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one instructor must be assigned."
            )

        return value

    def create(self, validated_data):

        instructors = validated_data.pop("instructors", [])

        creator = self.context["request"].user

        # Creator must always be the lead instructor.
        assigned_instructors = [creator]

        # Add the other instructors without duplicates.
        for instructor in instructors:
            if instructor.pk != creator.pk:
                assigned_instructors.append(instructor)

        course = Course.objects.create(**validated_data)

        for index, instructor in enumerate(assigned_instructors):

            CourseInstructor.objects.create(
                course=course,
                instructor=instructor,
                role=(
                    CourseInstructor.Role.LEAD
                    if index == 0
                    else CourseInstructor.Role.CO_INSTRUCTOR
                )
            )

        return course

    def update(self, instance, validated_data):

        instructors = validated_data.pop("instructors", None)

        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)

        instance.save()

        # Only replace assignments when the API receives instructors.
        if instructors is not None:

            instance.course_instructors.all().delete()

            for index, instructor in enumerate(instructors):

                CourseInstructor.objects.create(
                    course=instance,
                    instructor=instructor,
                    role=(
                        CourseInstructor.Role.LEAD
                        if index == 0
                        else CourseInstructor.Role.CO_INSTRUCTOR
                    )
                )

        return instance