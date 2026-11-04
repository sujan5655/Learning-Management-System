
import hashlib
import time
import requests

from django.conf import settings


BUNNY_API_URL = "https://video.bunnycdn.com"
BUNNY_TUS_URL = "https://video.bunnycdn.com/tusupload"


class BunnyStreamError(Exception):
    pass


def get_bunny_credentials():
    library_id = settings.BUNNY_STREAM_LIBRARY_ID
    api_key = settings.BUNNY_STREAM_API_KEY

    if not library_id or not api_key:
        raise BunnyStreamError(
            "Bunny Stream credentials are not configured."
        )

    return str(library_id), api_key


def create_bunny_video(title):
    """
    Create an empty video entry in Bunny Stream.
    """

    library_id, api_key = get_bunny_credentials()

    url = (
        f"{BUNNY_API_URL}/library/"
        f"{library_id}/videos"
    )

    headers = {
        "AccessKey": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    payload = {
        "title": title
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        video_id = data.get("guid")

        if not video_id:
            raise BunnyStreamError(
                "Bunny did not return a video ID."
            )

        return video_id

    except requests.RequestException as error:
        raise BunnyStreamError(
            f"Failed to create Bunny video: {error}"
        ) from error


def generate_tus_upload_credentials(video_id):
    """
    Generate temporary credentials for direct
    resumable TUS upload from the browser.
    """

    library_id, api_key = get_bunny_credentials()

    # Upload authorization expires in 6 hours.
    expiration_time = int(time.time()) + (6 * 60 * 60)

    signature_data = (
        library_id
        + api_key
        + str(expiration_time)
        + str(video_id)
    )

    signature = hashlib.sha256(
        signature_data.encode("utf-8")
    ).hexdigest()

    return {
        "endpoint": BUNNY_TUS_URL,
        "library_id": library_id,
        "video_id": video_id,
        "signature": signature,
        "expiration_time": expiration_time,
    }

def upload_bunny_video(video_id, video_file):
    """
    Upload an actual video file to an existing Bunny Stream video.
    The file is streamed from Django to Bunny.
    """
    library_id, api_key = get_bunny_credentials()

    url = (
        f"{BUNNY_API_URL}/library/"
        f"{library_id}/videos/{video_id}"
    )

    headers = {
        "AccessKey": api_key,
        "Accept": "application/json",
        "Content-Type": "application/octet-stream",
    }

    try:
        video_file.seek(0)

        response = requests.put(
            url,
            headers=headers,
            data=video_file,
            timeout=(30, 1800),
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:
        raise BunnyStreamError(
            f"Failed to upload video to Bunny Stream: {error}"
        ) from error


def get_bunny_video_details(video_id):
    library_id, api_key = get_bunny_credentials()

    url = (
        f"{BUNNY_API_URL}/library/"
        f"{library_id}/videos/{video_id}"
    )

    headers = {
        "AccessKey": api_key,
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        raise BunnyStreamError(
            f"Failed to retrieve Bunny video details: {error}"
        ) from error



def delete_bunny_video(video_id):
    library_id, api_key = get_bunny_credentials()

    url = (
        f"{BUNNY_API_URL}/library/"
        f"{library_id}/videos/{video_id}"
    )

    headers = {
        "AccessKey": api_key,
        "Accept": "application/json",
    }

    try:
        response = requests.delete(
            url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

    except requests.RequestException as error:
        raise BunnyStreamError(
            f"Failed to delete Bunny video: {error}"
        ) from error