
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Category, Course, CourseInstructor
from .serializers import CategorySerializer, CourseSerializer


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

        if not check_permission(request, IsCourseLeadOrAdmin, course):
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
