"""
Miro Image Edit API Client Example
Demonstrates how to call the image editing service using OpenAI API compatible format
"""

import base64
import requests
from pathlib import Path
from image_utils import encode_image_to_base64


def call_image_edit_api_with_base64(
    api_url: str,
    prompt: str,
    image_paths: list,
):
    """Call API with base64 encoded images"""

    # Construct message content
    content = [{"type": "text", "text": prompt}]

    # Add images
    for image_path in image_paths:
        base64_image = encode_image_to_base64(image_path)
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
            }
        )

    # Construct request
    payload = {
        "model": "Qwen-Image-Edit-2511",
        "messages": [{"role": "user", "content": content}],
    }

    # Send request
    response = requests.post(
        f"{api_url}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    response.raise_for_status()
    return response.json()


def call_image_edit_api_with_url(
    api_url: str,
    prompt: str,
    image_urls: list,
):
    """Call API with HTTP URL images"""

    # Construct message content
    content = [{"type": "text", "text": prompt}]

    # Add image URLs
    for image_url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": image_url}})

    # Construct request
    payload = {
        "model": "Qwen-Image-Edit-2511",
        "messages": [{"role": "user", "content": content}],
    }

    # Send request
    response = requests.post(
        f"{api_url}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    response.raise_for_status()
    return response.json()


def save_base64_images_from_response(response_data: dict, output_dir: str = "./output"):
    """Extract and save base64 encoded images from response"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    choices = response_data.get("choices", [])
    if not choices:
        print("No images found in response")
        return

    content = choices[0].get("message", {}).get("content", "")

    # Extract markdown format images
    import re

    pattern = r"!\[image\]\(data:image/(\w+);base64,([^)]+)\)"
    matches = re.findall(pattern, content)

    saved_files = []
    for idx, (img_format, base64_data) in enumerate(matches):
        # Decode base64
        img_data = base64.b64decode(base64_data)

        # Save file
        filename = f"output_{idx}.{img_format.lower()}"
        filepath = output_path / filename

        with open(filepath, "wb") as f:
            f.write(img_data)

        saved_files.append(str(filepath))
        print(f"Image saved to: {filepath}")

    return saved_files


def main():
    # API service URL
    API_URL = "http://localhost:8081"

    # Example 1: Using local images (base64 encoded)
    print("=" * 60)
    print("Example 1: Using local images (base64 encoded)")
    print("=" * 60)

    try:
        response = call_image_edit_api_with_base64(
            api_url=API_URL,
            prompt="Please give me a rabbit",
            image_paths=["examples/background.png"],
        )

        print(f"Request ID: {response['id']}")
        print(f"Model: {response['model']}")
        print(f"Created at: {response['created']}")

        # Save generated images
        saved_files = save_base64_images_from_response(
            response, "./output/output_image_base64"
        )
        print(f"Total {len(saved_files)} images saved")

    except Exception as e:
        print(f"Error: {str(e)}")

    print("\n")

    # Example 2: Using HTTP URLs
    print("=" * 60)
    print("Example 2: Using HTTP URLs")
    print("=" * 60)

    try:
        response = call_image_edit_api_with_url(
            api_url=API_URL,
            prompt="Turn it into a blue tone",
            image_urls=[
                "https://raw.githubusercontent.com/IntimeAI/Miro/refs/heads/main/examples/example.png",
            ],
        )

        print(f"Request ID: {response['id']}")
        print(f"Model: {response['model']}")

        # Save generated images
        saved_files = save_base64_images_from_response(
            response, "./output/output_image_url"
        )
        print(f"Total {len(saved_files)} images saved")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
