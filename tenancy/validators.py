from django.core.exceptions import ValidationError

MAX_LOGO_BYTES = 2 * 1024 * 1024
MIN_LOGO_EDGE = 64


def _image_error():
    return ValidationError("Upload a PNG, JPEG or WEBP image.")


def validate_logo(upload):
    """Validate an uploaded school logo.

    Accepts PNG, JPEG and WEBP of at most 2 MB and at least 64 x 64 pixels.
    SVG is not accepted because it can carry scripts, and images large enough to
    exhaust memory are rejected rather than decoded.
    """
    if upload is None:
        return upload

    if upload.size > MAX_LOGO_BYTES:
        raise ValidationError("The logo must be 2 MB or smaller.")

    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(upload)
        image.verify()
    except Image.DecompressionBombError:
        raise ValidationError("That image is too large to process. Use a smaller logo.")
    except (UnidentifiedImageError, OSError, ValueError):
        raise _image_error()
    finally:
        upload.seek(0)

    try:
        image = Image.open(upload)
        width, height = image.size
    except Image.DecompressionBombError:
        raise ValidationError("That image is too large to process. Use a smaller logo.")
    except (UnidentifiedImageError, OSError, ValueError):
        raise _image_error()
    finally:
        upload.seek(0)

    if width < MIN_LOGO_EDGE or height < MIN_LOGO_EDGE:
        raise ValidationError(
            f"The logo must be at least {MIN_LOGO_EDGE} by {MIN_LOGO_EDGE} pixels."
        )
    return upload
