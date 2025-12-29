"""
Miro 3D AI - Gradio Web Interface

This module provides a web-based interface for the Miro 3D generation system,
combining image editing and 3D model generation capabilities through an
interactive chat interface.

Features:
    - Text-to-3D generation
    - Image editing with natural language prompts
    - Version history management
    - Real-time 3D model visualization
"""

import os
import re
import uuid
import base64
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import gradio as gr
import requests

from utils.render import render_image


# ==========================================
# Configuration Constants
# ==========================================

MIROSHAPE_URL = "http://localhost:8080"
MIROIMAGE_URL = "http://localhost:8081"
OUTPUT_PATH = "output/gradio"
IMAGE_MODEL = "Qwen-Image-Edit-2511"

SYSTEM_PROMPT = f"""You are a 3D modeler. 
Please generate a 3D modeling render based on user requirements. 
Always provide a 3D rendering image with a grayish-white background to convey a professional texture. 
Use only ambient lighting to showcase the model's structure and material, 
avoid high-contrast lighting or dramatic shadows. 
Do not use stylized effect images with post-processing."""

# ==========================================
# Image Processing Utilities
# ==========================================


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode a local image file to base64 string.

    Args:
        image_path: Path to the image file

    Returns:
        Base64 encoded string of the image

    Raises:
        FileNotFoundError: If the image file does not exist
        IOError: If there's an error reading the file
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_images_from_response(
    response_data: Dict[str, Any], output_dir: str
) -> List[str]:
    """
    Extract and save images from API response.

    The API returns images embedded in markdown format within the response content.
    This function extracts those images and saves them to disk.

    Args:
        response_data: JSON response from the image editing API
        output_dir: Directory to save extracted images

    Returns:
        List of paths to saved image files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    choices = response_data.get("choices", [])
    if not choices:
        print("Warning: No images found in API response")
        return []

    content = choices[0].get("message", {}).get("content", "")

    # Extract images in markdown format: ![image](data:image/format;base64,...)
    pattern = r"!\[image\]\(data:image/(\w+);base64,([^)]+)\)"
    matches = re.findall(pattern, content)

    saved_files = []
    for idx, (img_format, base64_data) in enumerate(matches):
        try:
            # Decode base64 data to binary
            img_data = base64.b64decode(base64_data)

            # Save image file with appropriate extension
            filename = f"output_{idx}.{img_format.lower()}"
            filepath = output_path / filename

            with open(filepath, "wb") as f:
                f.write(img_data)

            saved_files.append(str(filepath))
            print(f"Image saved to: {filepath}")
        except Exception as e:
            print(f"Error saving image {idx}: {e}")

    return saved_files


# ==========================================
# API Client Functions
# ==========================================


def call_image_edit_api(prompt: str, image_paths: List[str]) -> Dict[str, Any]:
    """
    Call the image editing API with base64 encoded images.

    Args:
        prompt: Text prompt describing the desired image edit
        image_paths: List of paths to input images

    Returns:
        JSON response from the API containing edited images

    Raises:
        requests.HTTPError: If the API request fails
    """
    # Construct message content with text prompt
    content = [{"type": "text", "text": SYSTEM_PROMPT + prompt}]

    # Add all images as base64 encoded data URLs
    for image_path in image_paths:
        base64_image = encode_image_to_base64(image_path)
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
            }
        )

    # Construct API request payload
    payload = {
        "model": IMAGE_MODEL,
        "messages": [{"role": "user", "content": content}],
    }

    # Send POST request to image editing API
    response = requests.post(
        f"{MIROIMAGE_URL}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    response.raise_for_status()
    return response.json()


def call_3d_generation_api(image_path: str, output_path: Optional[str] = None) -> str:
    """
    Call the 3D generation API with a base64 encoded image.

    Args:
        image_path: Path to the input image
        output_path: Optional path to save the generated 3D model

    Returns:
        Path to the saved GLB model file

    Raises:
        requests.HTTPError: If the API request fails
        IOError: If there's an error saving the model file
    """
    # Encode input image to base64
    base64_image = encode_image_to_base64(image_path)

    # Construct API request payload
    payload = {"image_base64": base64_image}

    # Send POST request to 3D generation API
    response = requests.post(
        f"{MIROSHAPE_URL}/generate3d",
        data=payload,
    )

    response.raise_for_status()

    # Generate output path if not provided
    if output_path is None:
        output_path = f"output_{Path(image_path).stem}.glb"

    # Save the GLB model file
    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"3D model saved to: {output_path}")
    return output_path


# ==========================================
# Core Generation Pipeline
# ==========================================


def generate_3d_model(
    text: str, images: List[str], history_state: List[str]
) -> Tuple[Optional[str], List[str], Optional[str], List[str]]:
    """
    Generate a 3D model based on text prompt and input images.

    This function orchestrates the complete generation pipeline:
    1. Edit/generate images based on text prompt
    2. Generate 3D model from the edited image
    3. Render a preview image of the 3D model

    Args:
        text: Text prompt describing the desired 3D model
        images: List of input image paths
        history_state: List storing paths to previously generated models

    Returns:
        Tuple containing:
            - model_path: Path to the generated 3D model (or None if failed)
            - updated_history_state: Updated list of model paths
            - render_image_path: Path to rendered preview image (or None if failed)
            - generated_images: List of paths to generated/edited images
    """
    # Create unique output directory for this generation
    prefix = uuid.uuid4().hex
    output_path = os.path.join(OUTPUT_PATH, prefix)

    # Step 1: Generate/edit image based on text prompt
    try:
        response_image = call_image_edit_api(text, images)
        image_files = extract_images_from_response(response_image, output_path)
    except Exception as e:
        print(f"Error in image generation: {e}")
        return None, history_state, None, []

    new_model_path = None
    current_image = None

    # Step 2: Generate 3D model from the edited image
    if image_files:
        reference_image = image_files[0]
        if os.path.exists(reference_image):
            try:
                model_path = call_3d_generation_api(
                    reference_image, os.path.join(output_path, "output.glb")
                )
                if os.path.exists(model_path):
                    new_model_path = model_path
                    history_state.append(new_model_path)

                    # Step 3: Render preview image of the 3D model
                    render_path = os.path.join(output_path, "render_image.png")
                    render_image(new_model_path, render_path)
                    if os.path.exists(render_path):
                        current_image = render_path
            except Exception as e:
                print(f"Error in 3D generation: {e}")

    return new_model_path, history_state, current_image, image_files


# ==========================================
# Gradio Event Handlers
# ==========================================


def on_submit_immediate(
    message: Dict[str, Any], history: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], None, Dict[str, Any], gr.update, gr.update]:
    """
    Immediately update chat UI with user input before processing.

    This provides instant feedback to the user by updating the chat interface
    immediately, before the long-running 3D generation task begins.

    Args:
        message: User input containing 'text' and 'files' keys
        history: Chat history list

    Returns:
        Tuple containing:
            - updated_history: Chat history with user message added
            - cleared_input: None to clear the input box
            - message_copy: Copy of message for next processing step
            - input_update: Gradio update to disable input during processing
            - button_update: Gradio update to disable revert button during processing
    """
    user_text = message.get("text", "")
    user_files = message.get("files", [])

    # Add user uploaded images to chat history
    for user_file in user_files:
        history.append({"role": "user", "content": gr.Image(user_file, height=200)})

    # Add user text message to chat history
    history.append({"role": "user", "content": user_text})

    return (
        history,  # Updated chatbot with user message
        None,  # Clear input box
        message,  # Pass message to next step
        gr.update(interactive=False),  # Disable input during processing
        gr.update(interactive=False),  # Disable revert button during processing
    )


def on_submit_process(
    message: Dict[str, Any],
    history: List[Dict[str, Any]],
    state: List[str],
    current_image_state: Optional[str],
) -> Tuple[
    List[Dict[str, Any]],
    List[str],
    Optional[str],
    gr.update,
    Optional[str],
    gr.update,
    gr.update,
]:
    """
    Process the long-running 3D generation task.

    This runs after the UI has been updated with user input. It performs the
    actual image editing and 3D model generation.

    Args:
        message: User input containing 'text' and 'files' keys
        history: Chat history (already contains user message)
        state: Model version history
        current_image_state: Current rendered image path

    Returns:
        Tuple containing updated UI components:
            - updated_history: Chat history with assistant responses
            - updated_state: Updated model version history
            - new_model: Path to newly generated 3D model
            - version_list_update: Updated version dropdown choices
            - updated_current_image_state: Updated current image path
            - input_update: Re-enable input after processing
            - button_update: Re-enable revert button after processing
    """
    # Collect images for editing (current image + new uploads)
    edit_images = []
    if current_image_state:
        edit_images.append(current_image_state)

    user_text = message.get("text", "")
    user_files = message.get("files", [])

    # Combine current image with newly uploaded images
    edit_images += user_files

    # Use default background if no images provided
    if not edit_images:
        edit_images = ["examples/background.png"]

    # Generate 3D model from text and images
    new_model, updated_state, updated_current_image_state, generated_images = (
        generate_3d_model(user_text, edit_images, state)
    )

    # Add generated images to chat history
    for generated_image in generated_images:
        history.append(
            {"role": "assistant", "content": gr.Image(generated_image, height=200)}
        )

    # Add rendered 3D model preview to chat history
    if updated_current_image_state:
        history.append(
            {
                "role": "assistant",
                "content": gr.Image(updated_current_image_state, height=200),
            }
        )

    # Update version list with new model
    new_choices = [f"Version {i+1}" for i in range(len(updated_state))]

    return (
        history,
        updated_state,
        new_model,
        gr.update(choices=new_choices, value=new_choices[-1] if new_choices else None),
        updated_current_image_state,
        gr.update(interactive=True),  # Re-enable input
        gr.update(interactive=True),  # Re-enable revert button
    )


def revert_to_version(version_index: int, history_state: List[str]) -> Optional[str]:
    """
    Revert to a specific model version from history.

    Args:
        version_index: Index of the version to revert to
        history_state: List of model paths in history

    Returns:
        Path to the selected model, or None if index is invalid
    """
    if version_index is not None and 0 <= version_index < len(history_state):
        selected_model = history_state[version_index]
        return selected_model
    return None


# ==========================================
# Custom CSS Styling
# ==========================================

CUSTOM_CSS = """
/* Fix chatbot extra scrollbar issue */
#chat-window {
    overflow: unset !important;
}
"""


# ==========================================
# Gradio UI Definition
# ==========================================


def create_interface() -> gr.Blocks:
    """
    Create and configure the Gradio interface.

    Returns:
        Configured Gradio Blocks interface
    """
    with gr.Blocks(css=CUSTOM_CSS, title="Miro") as demo:
        # Session state storage (independent for each user session)
        history_state = gr.State([])  # Stores paths to all generated 3D models
        current_image_state = gr.State(None)  # Stores path to current rendered image
        message_state = gr.State()  # Intermediate state to pass message between steps

        # Header
        gr.Markdown(
            """
            # Miro: Conversational and editable 3D asset generation from text and images
            
            Create stunning 3D models from text descriptions and images. 
            Simply describe what you want or upload an image to get started!
            """
        )

        with gr.Row(equal_height=True):
            # Left column: 3D visualization area
            with gr.Column(scale=2):
                gr.Markdown("### 🧊 3D Visualization")
                model_viewer = gr.Model3D(
                    label="Current 3D Model",
                    elem_id="model-viewer",
                    interactive=True,
                    height=610,
                )

                version_list = gr.Radio(
                    choices=[],
                    label="📜 Version History",
                    type="index",
                    interactive=True,
                )
                revert_btn = gr.Button(
                    "Revert to Selected Version", variant="secondary"
                )

            # Right column: chat interface area
            with gr.Column(scale=1):
                gr.Markdown("### 💬 Chat Interface")
                chatbot = gr.Chatbot(
                    label="Conversation",
                    elem_id="chat-window",
                    type="messages",
                    height=610,
                )

                msg_input = gr.MultimodalTextbox(
                    show_label=False,
                    placeholder="Describe your 3D model or upload an image...",
                    file_types=["image"],
                    file_count="multiple",
                    lines=4,
                    max_lines=4,
                )

        # Examples section
        gr.Examples(
            examples=[
                [
                    {
                        "text": "Replace the rabbit with a tiger.",
                        "files": ["examples/example.png"],
                    }
                ],
                [
                    {
                        "text": "Add a cute pokemon to this background.",
                        "files": ["examples/background.png"],
                    }
                ],
                [
                    {
                        "text": "Add a hat to the rabbit.",
                        "files": ["examples/example.png"],
                    }
                ],
            ],
            inputs=[msg_input],
            label="💡 Example Prompts",
            examples_per_page=5,
        )

        # Event bindings
        # Two-step submit process for better UX
        msg_input.submit(
            # Step 1: Immediately update UI with user input
            on_submit_immediate,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input, message_state, msg_input, revert_btn],
        ).then(
            # Step 2: Process the long-running 3D generation task
            on_submit_process,
            inputs=[message_state, chatbot, history_state, current_image_state],
            outputs=[
                chatbot,
                history_state,
                model_viewer,
                version_list,
                current_image_state,
                msg_input,
                revert_btn,
            ],
        )

        # Version revert functionality
        revert_btn.click(
            revert_to_version,
            inputs=[version_list, history_state],
            outputs=[model_viewer],
        )

    return demo


# ==========================================
# Application Entry Point
# ==========================================


def main():
    """
    Main entry point for the application.
    """
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        favicon_path="assets/logo.svg",
        share=False,
    )


if __name__ == "__main__":
    main()
