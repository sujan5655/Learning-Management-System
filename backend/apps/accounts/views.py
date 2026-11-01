
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import User
from .serializers import RegisterSerializer, UserProfileSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        return Response(
            {
                "message": "Registration successful.",
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def user_profile_view(request):

    if request.method == "GET":

        serializer = UserProfileSerializer(request.user)

        return Response(serializer.data)

    elif request.method == "PATCH":

        serializer = UserProfileSerializer(
            request.user,
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



from .models import User, InstructorApplication
from .instructor_serializers import (
    InstructorApplicationSerializer,
    
    AdminInstructorApplicationSerializer,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from .models import InstructorApplication
from .instructor_serializers import InstructorApplicationSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def instructor_application_view(request):

    user = request.user

    # GET: Return application history
    if request.method == "GET":

        applications = InstructorApplication.objects.filter(
            user=user
        )

        serializer = InstructorApplicationSerializer(
            applications,
            many=True
        )

        return Response(serializer.data)

    # POST: Submit a new application

    if user.role != "STUDENT":
        return Response(
            {"detail": "Only students can apply to become instructors."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Check whether the user already has a pending application
    pending_application = InstructorApplication.objects.filter(
        user=user,
        status="PENDING"
    ).exists()

    if pending_application:
        return Response(
            {
                "detail": (
                    "You already have a pending application. "
                    "You can edit your existing application instead."
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = InstructorApplicationSerializer(
        data=request.data
    )

    if serializer.is_valid():
        serializer.save(user=user)

        return Response(
            {
                "message": "Instructor application submitted successfully.",
                "application": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_instructor_application_view(request, application_id):

    application = get_object_or_404(
        InstructorApplication,
        id=application_id,
        user=request.user
    )

    # Only pending applications can be edited
    if application.status != "PENDING":
        return Response(
            {
                "detail": "Only pending applications can be edited."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = InstructorApplicationSerializer(
        application,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()

        return Response(
            {
                "message": "Application updated successfully.",
                "application": serializer.data
            },
            status=status.HTTP_200_OK
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_instructor_applications_view(request):

    if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
        return Response(
            {"error": "Only administrators can access applications."},
            status=status.HTTP_403_FORBIDDEN
        )

    applications = InstructorApplication.objects.select_related(
        "user"
    ).all()

    serializer = AdminInstructorApplicationSerializer(
        applications,
        many=True
    )

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review_instructor_application_view(request, application_id):

    if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
        return Response(
            {"error": "Only administrators can review applications."},
            status=status.HTTP_403_FORBIDDEN
        )

    application = get_object_or_404(
        InstructorApplication.objects.select_related("user"),
        id=application_id
    )

    if application.status != InstructorApplication.Status.PENDING:
        return Response(
            {"error": "This application has already been reviewed."},
            status=status.HTTP_400_BAD_REQUEST
        )

    action = request.data.get("action")

    if action not in ["approve", "reject"]:
        return Response(
            {"error": "Action must be approve or reject."},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():

        if action == "approve":

            application.status = InstructorApplication.Status.APPROVED

            application.user.role = User.Role.INSTRUCTOR
            application.user.instructor_status = User.InstructorStatus.APPROVED

            application.rejection_reason = ""

        else:

            rejection_reason = request.data.get("rejection_reason", "").strip()

            if not rejection_reason:
                return Response(
                    {"error": "A rejection reason is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application.status = InstructorApplication.Status.REJECTED

            application.user.instructor_status = User.InstructorStatus.REJECTED

            application.rejection_reason = rejection_reason

        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()

        application.user.save(
            update_fields=["role", "instructor_status"]
        )

        application.save()

    return Response(
        {
            "message": f"Application {action}d successfully.",
            "application": AdminInstructorApplicationSerializer(application).data
        },
        status=status.HTTP_200_OK
    )
