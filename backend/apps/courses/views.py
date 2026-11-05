
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from django.conf import settings



from .models import Category, Course, CourseInstructor
from .serializers import CategorySerializer, CourseSerializer, PlaybackSessionEndSerializer
from .permissions import IsAssignedInstructorOrAdmin

from .permissions import (
    IsAdmin,
    IsApprovedInstructor,
    IsAdminOrReadOnly,
    IsCourseLeadOrAdmin,
    CanViewCourse,
    check_permission,
    is_admin,
    is_approved_instructor,
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import parser_classes
from .services.bunny import (
    BunnyStreamError,
    create_bunny_video,
    upload_bunny_video,
    delete_bunny_video,
)
from .models import PlaybackSession, LessonProgress, Enrollment
# -----------------------------------
# Permission helper functions
# -----------------------------------

def is_admin(user):
    return (
        user.is_authenticated
        and (user.role == "ADMIN" or user.is_superuser)
    )


def is_approved_instructor(user):
    return (
        user.is_authenticated
        and user.role == "INSTRUCTOR"
        and user.instructor_status == "APPROVED"
    )


def is_course_lead(user, course):
    return course.course_instructors.filter(
        instructor=user,
        role=CourseInstructor.Role.LEAD
    ).exists()


def is_course_instructor(user, course):
    return course.instructors.filter(
        id=user.id
    ).exists()


# -----------------------------------
# CATEGORY VIEWS
# -----------------------------------

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def category_list_create_view(request):

    # GET: List categories
    if request.method == "GET":

        if is_admin(request.user):
            categories = Category.objects.all()
        else:
            categories = Category.objects.filter(is_active=True)

        serializer = CategorySerializer(
            categories,
            many=True
        )

        return Response(serializer.data)

    # POST: Admin only
    if not check_permission(request,IsAdminOrReadOnly):
        return Response(
            {"detail": "Only admins can create categories."},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = CategorySerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def category_detail_view(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id
    )

    # GET: Public can view active categories.
    if request.method == "GET":

        if not category.is_active and not is_admin(request.user):
            return Response(
                {"detail": "Category not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CategorySerializer(category)

        return Response(serializer.data)

    # PATCH and DELETE: Admin only.
    if not check_permission(request, IsAdminOrReadOnly):
        return Response(
            {"detail": "Only admins can manage categories."},
            status=status.HTTP_403_FORBIDDEN
        )

    # PATCH: Update category.
    if request.method == "PATCH":

        serializer = CategorySerializer(
            category,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # DELETE: Deactivate instead of permanently deleting.
    category.is_active = False
    category.save(update_fields=["is_active", "updated_at"])

    return Response(
        {"message": "Category deactivated successfully."},
        status=status.HTTP_200_OK
    )


# -----------------------------------
# COURSE VIEWS
# -----------------------------------

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def course_list_create_view(request):

    # GET: List courses
    if request.method == "GET":

        courses = Course.objects.select_related(
            "category"
        ).prefetch_related(
            "course_instructors__instructor"
        )

        if is_admin(request.user):
            pass

        elif is_approved_instructor(request.user):

            # Approved instructors can see published courses
            # and all courses they are assigned to.
            courses = courses.filter(
                models.Q(status="PUBLISHED")
                | models.Q(instructors=request.user)
            ).distinct()

        else:
            # Public visitors and students see published courses.
            courses = courses.filter(status="PUBLISHED")

        serializer = CourseSerializer(
            courses,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    # POST: Only approved instructors can create courses.
    if not check_permission(request, IsApprovedInstructor):
        return Response(
            {
                "detail": (
                    "Only approved instructors can create courses."
                )
            },
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = CourseSerializer(
        data=request.data,
        context={"request": request}
    )

    if serializer.is_valid():

        with transaction.atomic():
            course = serializer.save()

            if course.status == Course.Status.PUBLISHED:
                course.published_at = timezone.now()
                course.save(update_fields=["published_at"])

        response_serializer = CourseSerializer(
            course,
            context={"request": request}
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def course_detail_view(request, slug):

    course = get_object_or_404(
        Course.objects.select_related(
            "category"
        ).prefetch_related(
            "course_instructors__instructor"
        ),
        slug=slug
    )

    user = request.user

    # GET: Course details
    if request.method == "GET":

        if not check_permission(request, IsAssignedInstructorOrAdmin, course):
          return Response(
        {
            "detail": "Only the lead instructor or admin can manage this course."
        },
        status=status.HTTP_403_FORBIDDEN
    )

        

        serializer = CourseSerializer(
            course,
            context={"request": request}
        )

        return Response(serializer.data)

    # PATCH and DELETE: Lead instructor or admin only.
    can_manage = (
        is_admin(user)
        or (
            is_approved_instructor(user)
            and is_course_lead(user, course)
        )
    )

    if not can_manage:
        return Response(
            {
                "detail": (
                    "Only the lead instructor or an admin "
                    "can manage this course."
                )
            },
            status=status.HTTP_403_FORBIDDEN
        )

    # PATCH: Update course.
    if request.method == "PATCH":

        serializer = CourseSerializer(
            course,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():

            new_status = serializer.validated_data.get(
                "status",
                course.status
            )

            extra_fields = {}

            if (
                new_status == Course.Status.PUBLISHED
                and course.published_at is None
            ):
                extra_fields["published_at"] = timezone.now()

            updated_course = serializer.save(**extra_fields)

            response_serializer = CourseSerializer(
                updated_course,
                context={"request": request}
            )

            return Response(response_serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # DELETE: Permanently delete the course.
    course.delete()

    return Response(
        {"message": "Course deleted successfully."},
        status=status.HTTP_200_OK
    )





from django.shortcuts import get_object_or_404
from .models import Course, Section
from .serializers import SectionSerializer
from .permissions import CanViewCourse, IsCourseLeadOrAdmin, check_permission


from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Course, Section
from .serializers import SectionSerializer


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def course_sections_view(request, course_id):

    course = get_object_or_404(Course, id=course_id)

    # GET: View course sections
    if request.method == "GET":

        if not check_permission(request, CanViewCourse, course):
            return Response(
                {"detail": "Course not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        sections = course.sections.all()

        serializer = SectionSerializer(
            sections,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    # POST: Create section
    if not check_permission(
        request,
        IsAssignedInstructorOrAdmin,
        course
    ):
        return Response(
            {"detail": "Only assigned instructors or admins can create sections."},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = SectionSerializer(
        data=request.data,
        context={"request": request}
    )

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check duplicate order before saving
    order = serializer.validated_data.get("order", 0)

    if Section.objects.filter(
        course=course,
        order=order
    ).exists():
        return Response(
            {
                "success": False,
                "errors": {
                    "order": [
                        f"Section order {order} already exists "
                        f"for course {course.id}."
                    ]
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Save safely and handle concurrent duplicate requests
    try:
        with transaction.atomic():
            section = serializer.save(course=course)

        return Response(
            SectionSerializer(
                section,
                context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED
        )

    except IntegrityError as exc:

        if "unique_section_order_per_course" in str(exc):
            return Response(
                {
                    "success": False,
                    "errors": {
                        "order": [
                            "This section order is already assigned "
                            "to another section in this course."
                        ]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"detail": "Unable to create section due to a database conflict."},
            status=status.HTTP_409_CONFLICT
        )



@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def section_detail_view(request, section_id):

    section = get_object_or_404(
        Section.objects.select_related("course"),
        id=section_id
    )

    course = section.course

    # GET: Retrieve section
    if request.method == "GET":

        if not check_permission(request, CanViewCourse, course):
            return Response(
                {"detail": "Section not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SectionSerializer(
            section,
            context={"request": request}
        )

        return Response(serializer.data)

    # PATCH / DELETE: Check management permission
    if not check_permission(request, IsCourseLeadOrAdmin, course):
        return Response(
            {"detail": "Only the lead instructor or admin can manage sections."},
            status=status.HTTP_403_FORBIDDEN
        )

    # PATCH: Update section
    if request.method == "PATCH":

        serializer = SectionSerializer(
            section,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # DELETE: Delete section
    if request.method == "DELETE":

        section.delete()

        return Response(
            {"message": "Section deleted successfully."},
            status=status.HTTP_200_OK
        )



from .models import Lesson, Section
from .serializers import LessonSerializer, LessonOutlineSerializer

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def section_lessons_view(request, section_id):

    section = get_object_or_404(
        Section.objects.select_related("course"),
        id=section_id
    )

    course = section.course

    # GET: View lessons
    if request.method == "GET":

        if not check_permission(request, CanViewCourse, course):
            return Response(
                {"detail": "Section not found."},
                status=404
            )

        lessons = section.lessons.all()

        serializer = LessonOutlineSerializer(
            lessons,
            many=True
        )

        return Response(serializer.data)

    # POST: Create lesson
    if not check_permission(
        request,
        IsAssignedInstructorOrAdmin,
        course
    ):
        return Response(
            {
                "detail": (
                    "Only assigned instructors or admins "
                    "can create lessons."
                )
            },
            status=403
        )

    serializer = LessonSerializer(
        data=request.data,
        context={"request": request}
    )

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=400
        )

    # Extract the video file before saving the model.
    validated_data = serializer.validated_data

    video_file = validated_data.pop("video", None)

    lesson_type = validated_data.get(
        "lesson_type",
        Lesson.LessonType.VIDEO
    )

    try:

        if lesson_type == Lesson.LessonType.VIDEO:

            # 1. Create a video entry in Bunny.
            video_id = create_bunny_video(
                validated_data["title"]
            )

            # 2. Upload the actual file to Bunny.
            upload_bunny_video(
                video_id,
                video_file
            )

            # 3. Save the lesson with its Bunny video ID.
            lesson = serializer.save(
                section=section,
                bunny_video_id=video_id,
                bunny_video_status=Lesson.VideoStatus.PROCESSING
            )

        else:

            # Text/resource lesson: no Bunny upload.
            lesson = serializer.save(
                section=section
            )

    except BunnyStreamError as error:

        return Response(
            {"detail": str(error)},
            status=502
        )

    response_data = {
        "message": "Lesson created and video uploaded successfully.",
        "lesson": LessonSerializer(
            lesson,
            context={"request": request}
        ).data
    }

    return Response(
        response_data,
        status=201
    )

@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def lesson_detail_view(request, lesson_id):

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id
    )

    course = lesson.section.course

    # --------------------------------
    # GET: Retrieve individual lesson
    # --------------------------------
    if request.method == "GET":

      course = lesson.section.course
      user = request.user

    # Check admin access
      is_admin_user = (
        user.is_authenticated
        and (
            user.role == "ADMIN"
            or user.is_superuser
        )
    )

    # Check assigned instructor access
      is_assigned_instructor = (
        user.is_authenticated
        and user.role == "INSTRUCTOR"
        and user.instructor_status == "APPROVED"
        and course.instructors.filter(id=user.id).exists()
    )

    # Check active enrollment
      is_enrolled = False

      if user.is_authenticated and user.role == "STUDENT":
        is_enrolled = Enrollment.objects.filter(
            student=user,
            course=course,
            status=Enrollment.Status.ACTIVE
        ).exists()

    # Allow access to preview lessons for everyone
    # Allow full access to admins, assigned instructors and enrolled students
      if not lesson.is_preview and not (
        is_admin_user
        or is_assigned_instructor
        or is_enrolled
    ):
        return Response(
            {
                "error": "You must enroll in this course to access this lesson."
            },
            status=status.HTTP_403_FORBIDDEN
        )

      serializer = LessonSerializer(lesson)

      return Response(
        serializer.data,
        status=status.HTTP_200_OK
    )

    # --------------------------------
    # PATCH: Update lesson
    # --------------------------------
    if request.method == "PATCH":

        if not check_permission(
            request,
            IsAssignedInstructorOrAdmin,
            course
        ):
            return Response(
                {"detail": "Only assigned instructors or admins can update lessons."},
                status=403
            )

        serializer = LessonSerializer(
            lesson,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=400
            )

        # Get the optional replacement video.
        video_file = serializer.validated_data.pop(
            "video",
            None
        )

        old_video_id = lesson.bunny_video_id
        new_video_id = None

        try:

            if video_file:

                # 1. Create a new Bunny video.
                new_video_id = create_bunny_video(
                    serializer.validated_data.get(
                        "title",
                        lesson.title
                    )
                )

                # 2. Upload replacement video.
                upload_bunny_video(
                    new_video_id,
                    video_file
                )

                # 3. Update lesson with new Bunny video ID.
                updated_lesson = serializer.save(
                    bunny_video_id=new_video_id,
                    bunny_video_status=Lesson.VideoStatus.PROCESSING
                )

                # 4. Delete old Bunny video after successful replacement.
                if old_video_id and old_video_id != new_video_id:
                    try:
                        delete_bunny_video(old_video_id)
                    except BunnyStreamError:
                        # Keep the updated lesson even if old-video cleanup fails.
                        pass

            else:

                # Update lesson details without replacing the video.
                updated_lesson = serializer.save()

        except BunnyStreamError as error:

            # Clean up a newly created Bunny video if upload failed.
            if new_video_id:
                try:
                    delete_bunny_video(new_video_id)
                except BunnyStreamError:
                    pass

            return Response(
                {"detail": str(error)},
                status=502
            )

        response_serializer = LessonSerializer(
            updated_lesson,
            context={"request": request}
        )

        return Response({
            "message": "Lesson updated successfully.",
            "lesson": response_serializer.data
        })

    # --------------------------------
    # DELETE: Delete lesson
    # --------------------------------
    if request.method == "DELETE":

        if not check_permission(
            request,
            IsAssignedInstructorOrAdmin,
            course
        ):
            return Response(
                {"detail": "Only assigned instructors or admins can delete lessons."},
                status=403
            )

        # Delete the Bunny video first.
        if lesson.bunny_video_id:

            try:
                delete_bunny_video(
                    lesson.bunny_video_id
                )

            except BunnyStreamError as error:
                return Response(
                    {
                        "detail": (
                            "Could not delete the Bunny video. "
                            "The lesson was not deleted."
                        ),
                        "error": str(error)
                    },
                    status=502
                )

        lesson.delete()

        return Response(
            {"message": "Lesson deleted successfully."},
            status=200
        )


from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Enrollment, Course
from .serializers import EnrollmentSerializer

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enroll_course_view(request, course_id):

    # Only students can enroll
    if request.user.role != "STUDENT":
        return Response(
            {"error": "Only students can enroll in courses."},
            status=status.HTTP_403_FORBIDDEN
        )

    course = get_object_or_404(
        Course,
        id=course_id,
        status=Course.Status.PUBLISHED
    )

    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course
    )

    # Reactivate an earlier cancelled enrollment
    if not created and enrollment.status == Enrollment.Status.CANCELLED:
        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.save(update_fields=["status", "updated_at"])
        created = True

    if not created:
        return Response(
            {"message": "You are already enrolled in this course."},
            status=status.HTTP_200_OK
        )

    serializer = EnrollmentSerializer(enrollment)

    return Response(
        {
            "message": "Successfully enrolled in the course.",
            "enrollment": serializer.data
        },
        status=status.HTTP_201_CREATED
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_enrollments_view(request):

    if request.user.role != "STUDENT":
        return Response(
            {"error": "Only students can view their enrollments."},
            status=status.HTTP_403_FORBIDDEN
        )

    enrollments = Enrollment.objects.filter(
        student=request.user,
        status=Enrollment.Status.ACTIVE
    ).select_related("course")

    serializer = EnrollmentSerializer(
        enrollments,
        many=True
    )

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def unenroll_course_view(request, course_id):

    if request.user.role != "STUDENT":
        return Response(
            {"error": "Only students can unenroll from courses."},
            status=status.HTTP_403_FORBIDDEN
        )

    enrollment = get_object_or_404(
        Enrollment,
        student=request.user,
        course_id=course_id,
        status=Enrollment.Status.ACTIVE
    )

    enrollment.status = Enrollment.Status.CANCELLED
    enrollment.save(update_fields=["status", "updated_at"])

    return Response(
        {"message": "Successfully unenrolled from the course."},
        status=status.HTTP_200_OK
    )


from django.utils import timezone
from .models import LessonProgress, Enrollment
from .serializers import (
    LessonProgressSerializer,
    VideoProgressUpdateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_lesson_progress_view(request, course_id, lesson_id):

    user = request.user

    if user.role != "STUDENT":
        return Response(
            {"error": "Only students can update progress."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Verify lesson belongs to course
    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id,
        section__course_id=course_id,
        lesson_type=Lesson.LessonType.VIDEO
    )

    # Verify enrollment
    is_enrolled = Enrollment.objects.filter(
        student=user,
        course_id=course_id,
        status=Enrollment.Status.ACTIVE
    ).exists()

    if not is_enrolled:
        return Response(
            {"error": "You are not enrolled in this course."},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = VideoProgressUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    session_id = serializer.validated_data["session_id"]
    current_position = serializer.validated_data["current_position"]
    reported_duration = serializer.validated_data["duration_seconds"]

    # Verify playback session
    playback_session = get_object_or_404(
        PlaybackSession,
        session_id=session_id,
        student=user,
        lesson=lesson,
        is_active=True
    )

    # Calculate elapsed server time
    now = timezone.now()
    

    if playback_session.last_reported_at:
      inactivity_seconds = (
        now - playback_session.last_reported_at
    ).total_seconds()

      timeout_seconds = (
        settings.PLAYBACK_SESSION_TIMEOUT_MINUTES * 60
    )

      if inactivity_seconds > timeout_seconds:
        playback_session.is_active = False
        playback_session.save(
            update_fields=["is_active", "updated_at"]
        )

        return Response(
            {
                "error": "Playback session expired due to inactivity.",
                "message": "Please start a new playback session."
            },
            status=status.HTTP_410_GONE
        )

    elapsed_seconds = (
        now - playback_session.last_reported_at
    ).total_seconds() if playback_session.last_reported_at else 0

    # Allow reasonable playback advancement
    max_allowed_advance = (elapsed_seconds * 1.5) + 5

    if current_position > playback_session.last_position + max_allowed_advance:
        return Response(
            {
                "error": "Playback position advanced too quickly.",
                "last_position": playback_session.last_position,
                "current_position": current_position
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get progress record
    progress, created = LessonProgress.objects.get_or_create(
        student=user,
        lesson=lesson
    )

    # Prefer duration stored by Bunny when available.
    # Otherwise use the player-reported duration.
    duration_seconds = float(
        lesson.duration
        or progress.duration_seconds
        or reported_duration
    )

    if current_position > duration_seconds:
        return Response(
            {"error": "Invalid playback position."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Update latest playback position
    progress.last_position = current_position

    # Preserve highest position reached
    progress.highest_position = max(
        progress.highest_position,
        current_position
    )

    progress.duration_seconds = duration_seconds

    progress.progress_percentage = min(
        (progress.highest_position / duration_seconds) * 100,
        100
    )

    # Complete at 90%
    if progress.progress_percentage >= 90 and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = now

    progress.save()

    # Update playback session
    playback_session.last_position = current_position
    playback_session.last_reported_at = now
    playback_session.save(
        update_fields=[
            "last_position",
            "last_reported_at",
            "updated_at"
        ]
    )

    return Response(
        {
            "message": "Progress updated successfully.",
            "progress": LessonProgressSerializer(progress).data
        },
        status=status.HTTP_200_OK
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_progress_view(request):

    if request.user.role != "STUDENT":
        return Response(
            {"error": "Only students can view their progress."},
            status=status.HTTP_403_FORBIDDEN
        )

    progress_records = LessonProgress.objects.filter(
        student=request.user
    ).select_related(
        "lesson",
        "lesson__section",
        "lesson__section__course"
    )

    serializer = LessonProgressSerializer(
        progress_records,
        many=True
    )

    return Response(
        serializer.data,
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def course_progress_view(request, course_id):

    if request.user.role != "STUDENT":
        return Response(
            {"error": "Only students can view course progress."},
            status=status.HTTP_403_FORBIDDEN
        )

    enrollment = get_object_or_404(
        Enrollment,
        student=request.user,
        course_id=course_id,
        status=Enrollment.Status.ACTIVE
    )

    progress_records = LessonProgress.objects.filter(
        student=request.user,
        lesson__section__course=enrollment.course
    ).select_related("lesson", "lesson__section")

    total_lessons = Lesson.objects.filter(
        section__course=enrollment.course,
        lesson_type=Lesson.LessonType.VIDEO
    ).count()

    completed_lessons = progress_records.filter(
        is_completed=True
    ).count()

    course_percentage = (
        (completed_lessons / total_lessons) * 100
        if total_lessons > 0 else 0
    )

    serializer = LessonProgressSerializer(
        progress_records,
        many=True
    )

    return Response(
        {
            "course_id": enrollment.course.id,
            "course_title": enrollment.course.title,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "progress_percentage": round(course_percentage, 2),
            "lessons": serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resume_lesson_view(request, course_id, lesson_id):
    user = request.user
    if user.role != "STUDENT":
        return Response(
            {"error": "Only students can access their playback progress."},
            status=status.HTTP_403_FORBIDDEN
        )

    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id,
        section__course_id=course_id
    )

    # Check active enrollment
    is_enrolled = Enrollment.objects.filter(
        student=user,
        course_id=course_id,
        status=Enrollment.Status.ACTIVE
    ).exists()

    if not is_enrolled:
        return Response(
            {"error": "You must be enrolled in this course."},
            status=status.HTTP_403_FORBIDDEN
        )

    progress = LessonProgress.objects.filter(
        student=user,
        lesson=lesson
    ).first()

    if not progress:
        return Response(
            {
                "lesson_id": lesson.id,
                "last_position": 0,
                "progress_percentage": 0,
                "is_completed": False
            },
            status=status.HTTP_200_OK
        )

    return Response(
        LessonProgressSerializer(progress).data,
        status=status.HTTP_200_OK
    )


from .models import PlaybackSession, LessonProgress, Enrollment
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_playback_session_view(request, course_id, lesson_id):

    user = request.user

    # Only students can create playback sessions
    if user.role != "STUDENT":
        return Response(
            {"error": "Only students can start playback sessions."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Verify that the lesson belongs to the specified course
    lesson = get_object_or_404(
        Lesson.objects.select_related("section__course"),
        id=lesson_id,
        section__course_id=course_id,
        lesson_type=Lesson.LessonType.VIDEO
    )

    # Verify active enrollment
    is_enrolled = Enrollment.objects.filter(
        student=user,
        course_id=course_id,
        status=Enrollment.Status.ACTIVE
    ).exists()

    if not is_enrolled:
        return Response(
            {"error": "You must be enrolled in this course."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Retrieve the student's saved progress
    progress = LessonProgress.objects.filter(
        student=user,
        lesson=lesson
    ).first()

    resume_position = (
        progress.last_position if progress else 0
    )

    # Close previous active sessions for this lesson
    PlaybackSession.objects.filter(
        student=user,
        lesson=lesson,
        is_active=True
    ).update(is_active=False)

    # Create a new playback session
    playback_session = PlaybackSession.objects.create(
        student=user,
        lesson=lesson,
        last_position=resume_position,
        last_reported_at=timezone.now()
    )

    return Response(
        {
            "message": "Playback session created successfully.",
            "session_id": str(playback_session.session_id),
            "course_id": course_id,
            "lesson_id": lesson.id,
            "resume_position": resume_position,
            "duration_seconds": lesson.duration,
            "video_player_url": (
                f"https://player.mediadelivery.net/embed/"
                f"{settings.BUNNY_STREAM_LIBRARY_ID}/"
                f"{lesson.bunny_video_id}"
                if lesson.bunny_video_id else None
            )
        },
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_playback_session_view(request, course_id, lesson_id):

    user = request.user

    if user.role != "STUDENT":
        return Response(
            {"error": "Only students can end playback sessions."},
            status=status.HTTP_403_FORBIDDEN
        )
    if expire_playback_session(playback_session):
      return Response(
        {
            "error": "Playback session expired.",
            "message": "Please start a new playback session."
        },
        status=status.HTTP_410_GONE
    )

    # Verify that the lesson belongs to the course
    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        section__course_id=course_id,
        lesson_type=Lesson.LessonType.VIDEO
    )

    # Get session ID from request body
    session_serializer = PlaybackSessionEndSerializer(
        data=request.data
    )
    session_serializer.is_valid(raise_exception=True)

    session_id = session_serializer.validated_data["session_id"]

    # Find the student's playback session
    playback_session = get_object_or_404(
        PlaybackSession,
        session_id=session_id,
        student=user,
        lesson=lesson
    )

    if not playback_session.is_active:
        return Response(
            {"message": "Playback session is already closed."},
            status=status.HTTP_200_OK
        )

    playback_session.is_active = False
    playback_session.save(update_fields=["is_active", "updated_at"])

    return Response(
        {
            "message": "Playback session ended successfully.",
            "session_id": str(playback_session.session_id),
            "is_active": False
        },
        status=status.HTTP_200_OK
    )