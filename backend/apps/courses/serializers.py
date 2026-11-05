
import os

from rest_framework import serializers

from .models import Category, Course, CourseInstructor,Enrollment,LessonProgress
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



from django.conf import settings
from rest_framework import serializers
from .models import Section, Lesson


class LessonSerializer(serializers.ModelSerializer):
    video_player_url = serializers.SerializerMethodField()
    video = serializers.FileField(
    write_only=True,
    required=False
)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "lesson_type",
            "bunny_video_id",
            "bunny_video_status",
            "video_player_url",
            "content",
            "resource_file",
            "duration",
            "video",
            
            "order",
            "is_preview",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "bunny_video_id",
            "bunny_video_status",
            "duration",
            "created_at",
            "updated_at",
        ]

    def get_video_player_url(self, obj):
        if not obj.bunny_video_id:
            return None

        library_id = settings.BUNNY_STREAM_LIBRARY_ID

        return (
            f"https://player.mediadelivery.net/embed/"
            f"{library_id}/{obj.bunny_video_id}"
        )

    def validate(self, attrs):
      attrs = super().validate(attrs)

      lesson_type = attrs.get(
        "lesson_type",
        self.instance.lesson_type if self.instance else Lesson.LessonType.VIDEO
    )

      video = attrs.get("video")

    # Don't allow changing the lesson type after creation.
      if (
        self.instance
        and "lesson_type" in attrs
        and attrs["lesson_type"] != self.instance.lesson_type
    ):
        raise serializers.ValidationError({
            "lesson_type": "Lesson type cannot be changed after creation."
        })

      if lesson_type == Lesson.LessonType.VIDEO:
        if not self.instance and not video:
            raise serializers.ValidationError({
                "video": "A video file is required."
            })

        if video:
            allowed_extensions = [
                ".mp4", ".mov", ".webm", ".mkv"
            ]

            extension = os.path.splitext(video.name)[1].lower()

            if extension not in allowed_extensions:
                raise serializers.ValidationError({
                    "video": "Supported formats: MP4, MOV, WEBM and MKV."
                })

      elif video:
        raise serializers.ValidationError({
            "video": "Video files are only allowed for VIDEO lessons."
        })

      return attrs

class LessonOutlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "lesson_type",
            "duration",
            "order",
            "is_preview",
            "bunny_video_status",
        ]
class SectionSerializer(serializers.ModelSerializer):
    lessons = LessonOutlineSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = [
            "id",
            "title",
            "description",
            "order",
            "lessons",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

class EnrollmentSerializer(serializers.ModelSerializer):

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
class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(
        source="lesson.title",
        read_only=True
    )

    course_id = serializers.IntegerField(
        source="lesson.section.course.id",
        read_only=True
    )

    class Meta:
        model = LessonProgress
        fields = [
            "id",
            "course_id",
            "lesson",
            "lesson_title",
            "last_position",
            "duration_seconds",
            "highest_position",
            "progress_percentage",
            "is_completed",
            "completed_at",
            "updated_at",
        ]

        read_only_fields = fields


class VideoProgressUpdateSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    current_position = serializers.FloatField(min_value=0)
    duration_seconds = serializers.FloatField(min_value=0.1)
from rest_framework import serializers


class PlaybackSessionEndSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    watched_seconds = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0
    )