"""
MiroShape API Client Example
Demonstrates how to call the 3D model generation service
"""

import requests
from pathlib import Path
from image_utils import encode_image_to_base64


def call_generate_api_with_file(
    api_url: str,
    image_path: str,
    output_path: str = None,
):
    """Call API with file upload"""

    # Open and send file
    with open(image_path, "rb") as f:
        files = {"file": (Path(image_path).name, f, "image/png")}
        response = requests.post(
            f"{api_url}/generate3d",
            files=files,
        )

    response.raise_for_status()

    # Save GLB file
    if output_path is None:
        output_path = f"output_{Path(image_path).stem}.glb"

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"3D model saved to: {output_path}")
    return output_path


def call_generate_api_with_base64(
    api_url: str,
    image_path: str,
    output_path: str = None,
):
    """Call API with base64 encoded image"""

    # Encode image to base64
    base64_image = encode_image_to_base64(image_path)

    # Construct request payload
    payload = {"image_base64": base64_image}

    # Send as multipart/form-data with empty file and JSON body
    response = requests.post(
        f"{api_url}/generate3d",
        data=payload,
    )

    response.raise_for_status()

    # Save GLB file
    if output_path is None:
        output_path = f"output_{Path(image_path).stem}.glb"

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"3D model saved to: {output_path}")
    return output_path


def call_generate_api_with_url(
    api_url: str,
    image_url: str,
    output_path: str = None,
):
    """Call API with HTTP URL image"""

    # Construct request
    payload = {"image_url": image_url}

    # Send request
    response = requests.post(
        f"{api_url}/generate3d",
        data=payload,
    )

    response.raise_for_status()

    # Save GLB file
    if output_path is None:
        output_path = "output_from_url.glb"

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"3D model saved to: {output_path}")
    return output_path


def main():
    # API service URL
    API_URL = "http://localhost:8080"

    # Create output directory
    output_dir = Path("./output/output_shape")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Example 1: Using file upload
    print("=" * 60)
    print("Example 1: Using file upload")
    print("=" * 60)

    try:
        output_file = call_generate_api_with_file(
            api_url=API_URL,
            image_path="examples/example.png",
            output_path=str(output_dir / "model_from_file.glb"),
        )
        print(f"Success! Model saved to: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\n")

    # Example 2: Using base64 encoded image
    print("=" * 60)
    print("Example 2: Using base64 encoded image")
    print("=" * 60)

    try:
        output_file = call_generate_api_with_base64(
            api_url=API_URL,
            image_path="examples/example.png",
            output_path=str(output_dir / "model_from_base64.glb"),
        )
        print(f"Success! Model saved to: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\n")

    # Example 3: Using HTTP URL
    print("=" * 60)
    print("Example 3: Using HTTP URL")
    print("=" * 60)

    try:
        output_file = call_generate_api_with_url(
            api_url=API_URL,
            image_url="https://raw.githubusercontent.com/IntimeAI/Miro/refs/heads/main/examples/example.png",
            output_path=str(output_dir / "model_from_url.glb"),
        )
        print(f"Success! Model saved to: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\n")
    print("=" * 60)
    print("All examples completed!")
    print(f"Check the '{output_dir}' directory for generated 3D models")
    print("=" * 60)


if __name__ == "__main__":
    main()
