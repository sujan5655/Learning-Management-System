from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.courses.models import PlaybackSession


def expire_playback_session(playback_session):

    if not playback_session.is_active:
        return True

    timeout_minutes = settings.PLAYBACK_SESSION_TIMEOUT_MINUTES

    expiration_time = timezone.now() - timedelta(
        minutes=timeout_minutes
    )

    if (
        playback_session.last_reported_at
        and playback_session.last_reported_at < expiration_time
    ):
        playback_session.is_active = False

        playback_session.save(
            update_fields=["is_active", "updated_at"]
        )

        return True

    return False