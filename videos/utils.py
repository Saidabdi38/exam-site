import os
import subprocess
import tempfile


def optimize_video_for_streaming(video):
    """
    Convert uploaded MP4 files to a web-friendly format.

    Output:
    - H.264 video
    - AAC audio
    - yuv420p pixel format
    - Fast-start MP4 metadata
    - Maximum 1080p resolution
    - Compatible with desktop and mobile browsers
    """

    if not video.video_file:
        return

    input_path = video.video_file.path

    # For now, process MP4 uploads.
    if not input_path.lower().endswith(".mp4"):
        return

    directory = os.path.dirname(input_path)

    fd, temp_path = tempfile.mkstemp(
        suffix=".mp4",
        dir=directory,
    )
    os.close(fd)

    try:
        command = [
            "/usr/bin/ffmpeg",
            "-y",

            # Input
            "-i",
            input_path,

            # Video codec
            "-c:v",
            "libx264",

            # Good balance between processing speed and compression
            "-preset",
            "fast",

            # Video quality
            "-crf",
            "23",

            # Maximum 1080p while keeping original aspect ratio
            "-vf",
            (
                "scale="
                "'min(1920,iw)':"
                "'min(1080,ih)':"
                "force_original_aspect_ratio=decrease,"
                "scale=trunc(iw/2)*2:trunc(ih/2)*2"
            ),

            # Very important for browser/mobile compatibility
            "-pix_fmt",
            "yuv420p",

            # Audio
            "-c:a",
            "aac",

            "-b:a",
            "128k",

            # Put MP4 metadata at beginning of file
            "-movflags",
            "+faststart",

            # Final optimized file
            temp_path,
        ]

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        # Replace original uploaded file only after FFmpeg succeeds
        os.replace(temp_path, input_path)

    except subprocess.CalledProcessError as exc:
        # Do not destroy original video if FFmpeg fails.
        error_message = exc.stderr.decode(
            "utf-8",
            errors="ignore",
        )

        raise RuntimeError(
            f"Video optimization failed: {error_message[-2000:]}"
        ) from exc

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)