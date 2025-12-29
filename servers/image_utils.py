"""
Miro Server Function
"""

import io
import base64
import requests
from PIL import Image


def encode_image_to_base64(image_path: str) -> str:
    """Encode local image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def load_image_from_base64(base64_str: str) -> Image.Image:
    """
    Load image from base64 string

    Args:
        base64_str: Base64 encoded image string

    Returns:
        PIL Image object
    """
    try:
        # Remove data URL prefix if present
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]

        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data)).convert(mode="RGB")
        return image
    except Exception as e:
        raise Exception(f"Failed to decode base64 image: {str(e)}")


def load_image_from_url(url: str) -> Image.Image:
    """
    Load image from URL

    Args:
        url: URL of the image

    Returns:
        PIL Image object
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))
        return image
    except requests.RequestException as e:
        raise Exception(f"Failed to download image from URL: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to load image from URL: {str(e)}")
