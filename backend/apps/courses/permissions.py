
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import CourseInstructor


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


class IsAdmin(BasePermission):
    """
    Only administrators can access the view.
    """

    def has_permission(self, request, view):
        return is_admin(request.user)


class IsApprovedInstructor(BasePermission):
    """
    Only approved instructors can access the view.
    """

    def has_permission(self, request, view):
        return is_approved_instructor(request.user)


class IsAdminOrReadOnly(BasePermission):
    """
    Anyone can read.
    Only admins can create, update or delete.
    """

    def has_permission(self, request, view):

        if request.method in SAFE_METHODS:
            return True

        return is_admin(request.user)


class IsCourseLeadOrAdmin(BasePermission):
    """
    Only the lead instructor or admin can manage a course.
    """

    def has_permission(self, request, view):

        user = request.user

        return (
            is_admin(user)
            or is_approved_instructor(user)
        )

    def has_object_permission(self, request, view, obj):

        user = request.user

        if is_admin(user):
            return True

        if not is_approved_instructor(user):
            return False

        return CourseInstructor.objects.filter(
            course=obj,
            instructor=user,
            role=CourseInstructor.Role.LEAD
        ).exists()


class CanViewCourse(BasePermission):
    """
    Public users can view published courses.
    Assigned instructors can also view their own courses.
    Admins can view every course.
    """

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):

        user = request.user

        if obj.status == "PUBLISHED":
            return True

        if is_admin(user):
            return True

        if not user.is_authenticated:
            return False

        return obj.instructors.filter(
            id=user.id
        ).exists()



def check_permission(request, permission_class, obj=None):

    permission = permission_class()

    # Check general permission
    if not permission.has_permission(request, None):
        return False

    # Check object permission if an object is provided
    if obj is not None:
        return permission.has_object_permission(
            request,
            None,
            obj
        )

    return True




class IsAssignedInstructorOrAdmin(BasePermission):
    """
    Allows admins and all approved instructors
    assigned to the course.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            is_admin(user)
            or is_approved_instructor(user)
        )

    def has_object_permission(self, request, view, obj):
        user = request.user

        if is_admin(user):
            return True

        if not is_approved_instructor(user):
            return False

        return obj.instructors.filter(id=user.id).exists()

