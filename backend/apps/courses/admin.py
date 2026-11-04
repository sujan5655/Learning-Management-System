from django.contrib import admin
from .models import Category, Course, CourseInstructor


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "is_active",
        "created_at",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "get_instructors",
        "category",
        "level",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "level",
        "category",
    )

    search_fields = (
        "title",
        "instructors__email",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }

    def get_instructors(self, obj):
        return ", ".join(
            instructor.email
            for instructor in obj.instructors.all()
        )

    get_instructors.short_description = "Instructors"


@admin.register(CourseInstructor)
class CourseInstructorAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "course",
        "instructor",
        "role",
        "assigned_at",
    )

    list_filter = (
        "role",
        "assigned_at",
    )

    search_fields = (
        "course__title",
        "instructor__email",
    )


from .models import Section, Lesson

admin.site.register(Section)
admin.site.register(Lesson)