import os
import subprocess
import tempfile

from django.conf import settings


def optimize_video_for_streaming(video):
    """
    Rewrites an uploaded MP4 with -movflags +faststart
    so playback can begin sooner over HTTP.

    No re-encoding is done.
    """
    if not video.video_file:
        return

    input_path = video.video_file.path

    if not input_path.lower().endswith(".mp4"):
        return

    directory = os.path.dirname(input_path)

    fd, temp_path = tempfile.mkstemp(
        suffix=".mp4",
        dir=directory,
    )
    os.close(fd)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                temp_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        os.replace(temp_path, input_path)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)