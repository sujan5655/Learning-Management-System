from celery import shared_task
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from .models import PlaybackSession


@shared_task
def expire_abandoned_playback_sessions():

    timeout_minutes = settings.PLAYBACK_SESSION_TIMEOUT_MINUTES

    expiration_time = timezone.now() - timedelta(
        minutes=timeout_minutes
    )

    expired_count = PlaybackSession.objects.filter(
        is_active=True,
        last_reported_at__lt=expiration_time
    ).update(
        is_active=False
    )

    return expired_count