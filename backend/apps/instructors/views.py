from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.courses.models import Course, Enrollment

from .serializers import InstructorCourseSerializer
from apps.courses.serializers import CourseSerializer
from apps.courses.permissions import is_admin
from apps.courses.models import Course, CourseInstructor

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def instructor_dashboard_view(request):

    user = request.user

    # Only approved instructors can access this dashboard
    if (
        user.role != "INSTRUCTOR"
        or user.instructor_status != "APPROVED"
    ):
        return Response(
            {"error": "Only approved instructors can access this dashboard."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get courses where the instructor is assigned
    courses = Course.objects.filter(
        instructors=user
    ).select_related(
        "category"
    ).distinct()

    published_courses = courses.filter(
        status=Course.Status.PUBLISHED
    )

    draft_courses = courses.filter(
        status=Course.Status.DRAFT
    )

    # Count unique students actively enrolled in assigned courses
    total_students = Enrollment.objects.filter(
        course__instructors=user,
        status=Enrollment.Status.ACTIVE
    ).values("student").distinct().count()

    # Recently created assigned courses
    recent_courses = courses.order_by(
        "-created_at"
    )[:5]

    return Response(
        {
            "statistics": {
                "total_courses": courses.count(),
                "published_courses": published_courses.count(),
                "draft_courses": draft_courses.count(),
                "total_students": total_students,
            },

            "recent_courses": InstructorCourseSerializer(
                recent_courses,
                many=True,
                context={"request": request}
            ).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def instructor_courses_view(request):
    user = request.user

    # GET: List courses assigned to the instructor
    if request.method == "GET":
        if user.role != "INSTRUCTOR" or user.instructor_status != "APPROVED":
            if not is_admin(user):
                return Response(
                    {"error": "Only approved instructors can access courses."},
                    status=status.HTTP_403_FORBIDDEN
                )

        if is_admin(user):
            courses = Course.objects.all()
        else:
            courses = Course.objects.filter(
                instructors=user
            ).distinct()

        courses = courses.select_related("category").order_by("-created_at")

        serializer = CourseSerializer(
            courses,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    # POST: Create a course
    if request.method == "POST":
        if not is_admin(user):
            if user.role != "INSTRUCTOR" or user.instructor_status != "APPROVED":
                return Response(
                    {"error": "Only approved instructors can create courses."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = CourseSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            course = serializer.save()

            return Response(
                CourseSerializer(
                    course,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def instructor_course_detail_view(request, course_id):
    user = request.user

    try:
        course = Course.objects.select_related("category").get(
            id=course_id
        )
    except Course.DoesNotExist:
        return Response(
            {"error": "Course not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check whether the user is assigned to this course
    is_assigned = course.instructors.filter(id=user.id).exists()

    # GET: View course details
    if request.method == "GET":
        if not is_admin(user) and not is_assigned:
            return Response(
                {"error": "You are not assigned to this course."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CourseSerializer(
            course,
            context={"request": request}
        )

        return Response(serializer.data)

    # PATCH: Only lead instructor or admin can update course details
    is_lead_instructor = CourseInstructor.objects.filter(
        course=course,
        instructor=user,
        role=CourseInstructor.Role.LEAD
    ).exists()

    if not is_admin(user) and not is_lead_instructor:
        return Response(
            {"error": "Only the lead instructor or admin can update this course."},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = CourseSerializer(
        course,
        data=request.data,
        partial=True,
        context={"request": request}
    )

    if serializer.is_valid():
        serializer.save()

        return Response(serializer.data)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def instructor_courses_view(request):
    user = request.user

    # GET: List courses assigned to the instructor
    if request.method == "GET":
        if user.role != "INSTRUCTOR" or user.instructor_status != "APPROVED":
            if not is_admin(user):
                return Response(
                    {"error": "Only approved instructors can access courses."},
                    status=status.HTTP_403_FORBIDDEN
                )

        if is_admin(user):
            courses = Course.objects.all()
        else:
            courses = Course.objects.filter(
                instructors=user
            ).distinct()

        courses = courses.select_related("category").order_by("-created_at")

        serializer = CourseSerializer(
            courses,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    # POST: Create a course
    if request.method == "POST":
        if not is_admin(user):
            if user.role != "INSTRUCTOR" or user.instructor_status != "APPROVED":
                return Response(
                    {"error": "Only approved instructors can create courses."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = CourseSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            course = serializer.save()

            return Response(
                CourseSerializer(
                    course,
                    context={"request": request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def instructor_course_detail_view(request, course_id):
    user = request.user

    try:
        course = Course.objects.select_related("category").get(
            id=course_id
        )
    except Course.DoesNotExist:
        return Response(
            {"error": "Course not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check whether the user is assigned to this course
    is_assigned = course.instructors.filter(id=user.id).exists()

    # GET: View course details
    if request.method == "GET":
        if not is_admin(user) and not is_assigned:
            return Response(
                {"error": "You are not assigned to this course."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CourseSerializer(
            course,
            context={"request": request}
        )

        return Response(serializer.data)

    # PATCH: Only lead instructor or admin can update course details
    is_lead_instructor = CourseInstructor.objects.filter(
        course=course,
        instructor=user,
        role=CourseInstructor.Role.LEAD
    ).exists()

    if not is_admin(user) and not is_lead_instructor:
        return Response(
            {"error": "Only the lead instructor or admin can update this course."},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = CourseSerializer(
        course,
        data=request.data,
        partial=True,
        context={"request": request}
    )

    if serializer.is_valid():
        serializer.save()

        return Response(serializer.data)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


from .serializers import (
    InstructorCourseSerializer,
    InstructorStudentSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def instructor_course_students_view(request, course_id):
    user = request.user

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response(
            {"error": "Course not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Only assigned instructors or admins can view students
    is_assigned = course.instructors.filter(id=user.id).exists()

    if not is_admin(user) and not is_assigned:
        return Response(
            {"error": "You are not assigned to this course."},
            status=status.HTTP_403_FORBIDDEN
        )

    enrollments = Enrollment.objects.filter(
        course=course,
        status__in=[
            Enrollment.Status.ACTIVE,
            Enrollment.Status.COMPLETED,
        ]
    ).select_related("student").order_by("-enrolled_at")

    serializer = InstructorStudentSerializer(
        enrollments,
        many=True
    )

    return Response({
        "course_id": course.id,
        "course_title": course.title,
        "total_students": enrollments.count(),
        "students": serializer.data,
    })


from apps.courses.models import Lesson, LessonProgress
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def instructor_course_progress_view(request, course_id):
    user = request.user

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response(
            {"error": "Course not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    is_assigned = course.instructors.filter(id=user.id).exists()

    if not is_admin(user) and not is_assigned:
        return Response(
            {"error": "You are not assigned to this course."},
            status=status.HTTP_403_FORBIDDEN
        )

    total_lessons = Lesson.objects.filter(
        section__course=course,
        lesson_type=Lesson.LessonType.VIDEO
    ).count()

    enrollments = Enrollment.objects.filter(
        course=course,
        status__in=[
            Enrollment.Status.ACTIVE,
            Enrollment.Status.COMPLETED,
        ]
    ).select_related("student")

    students = []

    for enrollment in enrollments:
        completed_lessons = LessonProgress.objects.filter(
            student=enrollment.student,
            lesson__section__course=course,
            lesson__lesson_type=Lesson.LessonType.VIDEO,
            is_completed=True
        ).count()

        progress_percentage = (
            round((completed_lessons / total_lessons) * 100, 2)
            if total_lessons > 0 else 0
        )

        students.append({
            "student_id": enrollment.student.id,
            "student_name": (
                enrollment.student.get_full_name()
                or enrollment.student.email
            ),
            "student_email": enrollment.student.email,
            "enrollment_status": enrollment.status,
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "progress_percentage": progress_percentage,
        })

    return Response({
        "course_id": course.id,
        "course_title": course.title,
        "total_students": len(students),
        "students": students,
    })