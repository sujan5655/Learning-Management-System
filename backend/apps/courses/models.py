from django.db import models

# Create your models here.

from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Category(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Course(models.Model):

    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    instructors = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    through="CourseInstructor",
    related_name="teaching_courses",
    limit_choices_to={"role": "INSTRUCTOR"}
)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="courses"
    )

    title = models.CharField(
        max_length=255
    )

    slug = models.SlugField(
        max_length=280,
        unique=True,
        blank=True
    )

    short_description = models.CharField(
        max_length=300
    )

    description = models.TextField()

    thumbnail = models.ImageField(
        upload_to="courses/thumbnails/",
        blank=True,
        null=True
    )

    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1

            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]



class CourseInstructor(models.Model):

    class Role(models.TextChoices):
        LEAD = "LEAD", "Lead Instructor"
        CO_INSTRUCTOR = "CO_INSTRUCTOR", "Co-Instructor"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="course_instructors"
    )

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_assignments"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CO_INSTRUCTOR
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "instructor"],
                name="unique_course_instructor"
            )
        ]

    def __str__(self):
        return f"{self.instructor.email} - {self.course.title}"



class Section(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sections"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_section_order_per_course"
            )
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"



class Lesson(models.Model):

    class LessonType(models.TextChoices):
        VIDEO = "VIDEO", "Video"
        TEXT = "TEXT", "Text"
        RESOURCE = "RESOURCE", "Resource"

    class VideoStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="lessons"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Lesson type
    lesson_type = models.CharField(
        max_length=20,
        choices=LessonType.choices,
        default=LessonType.VIDEO
    )

    # Bunny Stream video information
    bunny_video_id = models.CharField(
        max_length=100,
        blank=True
    )

    bunny_video_status = models.CharField(
        max_length=20,
        choices=VideoStatus.choices,
        default=VideoStatus.PENDING
    )

    # Text lesson content
    content = models.TextField(blank=True)

    # Downloadable resources
    resource_file = models.FileField(
        upload_to="lessons/resources/",
        blank=True,
        null=True
    )

    # Video duration in seconds
    duration = models.PositiveIntegerField(default=0)

    # Lesson organization
    order = models.PositiveIntegerField(default=0)

    # Whether visitors can access this lesson without enrolling
    is_preview = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "order"],
                name="unique_lesson_order_per_section"
            )
        ]

    def __str__(self):
        return f"{self.section.title} - {self.title}"



class Enrollment(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    enrolled_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment"
            )
        ]

        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.email} - {self.course.title}"



class LessonProgress(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress"
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="student_progress"
    )

    # Last playback position in seconds
    last_position = models.FloatField(default=0)

    # Video duration in seconds
    duration_seconds = models.FloatField(default=0)
    highest_position = models.FloatField(default=0)

    # Calculated by the backend
    progress_percentage = models.FloatField(default=0)

    is_completed = models.BooleanField(default=False)

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lesson"],
                name="unique_student_lesson_progress"
            )
        ]

        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.student.email} - {self.lesson.title}"

import uuid
class PlaybackSession(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playback_sessions"
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="playback_sessions"
    )

    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    # Latest playback position reported by this session
    last_position = models.FloatField(default=0)

    # Time when the last progress update was received
    last_reported_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.email} - {self.lesson.title}"

        