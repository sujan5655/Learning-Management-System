from django.shortcuts import get_object_or_404, render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.courses.models import Course, Enrollment

from .serializers import StudentEnrollmentSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_dashboard_view(request):

    user = request.user

    # Only students can access this dashboard
    if user.role != "STUDENT":
        return Response(
            {"error": "Only students can access this dashboard."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get all enrollments belonging to this student
    enrollments = Enrollment.objects.filter(
        student=user
    ).select_related(
        "course",
        "course__category"
    )

    active_enrollments = enrollments.filter(
        status=Enrollment.Status.ACTIVE
    )

    completed_enrollments = enrollments.filter(
        status=Enrollment.Status.COMPLETED
    )

    # Latest enrolled courses
    recent_enrollments = enrollments.order_by(
        "-enrolled_at"
    )[:5]

    # Courses the student is currently learning
    continue_learning = active_enrollments.order_by(
        "-updated_at"
    )[:5]

    return Response(
        {
            "statistics": {
                "total_enrolled_courses": enrollments.count(),
                "active_courses": active_enrollments.count(),
                "completed_courses": completed_enrollments.count(),
            },

            "recent_enrollments": StudentEnrollmentSerializer(
                recent_enrollments,
                many=True,
                context={"request": request}
            ).data,

            "continue_learning": StudentEnrollmentSerializer(
                continue_learning,
                many=True,
                context={"request": request}
            ).data,
        },
        status=status.HTTP_200_OK
    )


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


from apps.courses.models import (
    Enrollment,
    Lesson,
    LessonProgress,
)

from apps.courses.serializers import LessonProgressSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_progress_view(request):

    user = request.user

    if user.role != "STUDENT":
        return Response(
            {"error": "Only students can view their progress."},
            status=status.HTTP_403_FORBIDDEN
        )

    progress_records = LessonProgress.objects.filter(
        student=user
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

    user = request.user

    if user.role != "STUDENT":
        return Response(
            {"error": "Only students can view course progress."},
            status=status.HTTP_403_FORBIDDEN
        )

    enrollment = get_object_or_404(
        Enrollment,
        student=user,
        course_id=course_id,
        status=Enrollment.Status.ACTIVE
    )

    progress_records = LessonProgress.objects.filter(
        student=user,
        lesson__section__course=enrollment.course
    ).select_related(
        "lesson",
        "lesson__section"
    )

    total_lessons = Lesson.objects.filter(
        section__course=enrollment.course,
        lesson_type=Lesson.LessonType.VIDEO
    ).count()

    completed_lessons = progress_records.filter(
        is_completed=True
    ).count()

    course_percentage = (
        (completed_lessons / total_lessons) * 100
        if total_lessons else 0
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