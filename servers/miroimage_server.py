"""
MiroImage FastAPI Server
Provides API service for image generation
"""

import base64
import io
import os
import time
from typing import List, Optional, Union

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field

from vllm_omni.diffusion.data import DiffusionParallelConfig, logger
from vllm_omni.entrypoints.omni import Omni
from vllm_omni.utils.platform_utils import detect_device_type, is_npu

from image_utils import load_image_from_base64, load_image_from_url

# ==================== Configuration ====================
MODEL_PATH = os.getenv("MIROIMAGE_MODEL_PATH", "Qwen/Qwen-Image-Edit-2511")
MODEL_NAME = os.getenv("MIROIMAGE_MODEL_NAME", "Qwen-Image-Edit-2511")
DEFAULT_NUM_INFERENCE_STEPS = int(os.getenv("MIROIMAGE_NUM_INFERENCE_STEPS", "50"))
DEFAULT_CFG_SCALE = float(os.getenv("MIROIMAGE_CFG_SCALE", "4.0"))
DEFAULT_GUIDANCE_SCALE = float(os.getenv("MIROIMAGE_GUIDANCE_SCALE", "1.0"))
DEFAULT_LAYERS = int(os.getenv("MIROIMAGE_LAYERS", "4"))
DEFAULT_RESOLUTION = int(os.getenv("MIROIMAGE_RESOLUTION", "640"))


# ==================== Request Models ====================
class Message(BaseModel):
    role: str
    content: Union[str, List[dict]]


class ImageEditRequest(BaseModel):
    model: str = Field(default=MODEL_NAME)
    messages: List[Message]
    num_inference_steps: Optional[int] = Field(default=DEFAULT_NUM_INFERENCE_STEPS)
    cfg_scale: Optional[float] = Field(default=DEFAULT_CFG_SCALE)
    guidance_scale: Optional[float] = Field(default=DEFAULT_GUIDANCE_SCALE)
    layers: Optional[int] = Field(default=DEFAULT_LAYERS)
    resolution: Optional[int] = Field(default=DEFAULT_RESOLUTION)
    seed: Optional[int] = Field(default=0)


class ImageEditResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]


# ==================== FastAPI Application ====================
app = FastAPI(
    title="MiroImage API",
    description="Image Generation Service API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Global Variables ====================
omni_instance = None
device = None
generator = None


# ==================== Helper Functions ====================
def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL image to base64 string"""
    buffered = io.BytesIO()
    img.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/{format.lower()};base64,{img_str}"


def parse_messages(messages: List[Message]) -> tuple:
    """Parse messages to extract prompt and images"""
    prompt = ""
    images = []

    for message in messages:
        if message.role == "user":
            if isinstance(message.content, str):
                prompt = message.content
            elif isinstance(message.content, list):
                for item in message.content:
                    if item.get("type") == "text":
                        prompt = item.get("text", "")
                    elif item.get("type") == "image_url":
                        image_url = item.get("image_url", {})
                        url = image_url.get("url", "")

                        if url.startswith("http://") or url.startswith("https://"):
                            images.append(load_image_from_url(url))
                        elif url.startswith("data:image"):
                            images.append(load_image_from_base64(url))
                        else:
                            # Assume it's base64 encoded
                            images.append(load_image_from_base64(url))

    if not prompt:
        raise HTTPException(status_code=400, detail="No valid prompt found")

    if not images:
        raise HTTPException(status_code=400, detail="No valid input images found")

    return prompt, images


# ==================== Startup Event ====================
@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    global omni_instance, device, generator

    logger.info(f"Loading model: {MODEL_PATH}")

    device = detect_device_type()
    generator = torch.Generator(device=device).manual_seed(0)

    # Enable VAE memory optimizations on NPU
    vae_use_slicing = is_npu()
    vae_use_tiling = is_npu()

    parallel_config = DiffusionParallelConfig(ulysses_degree=1)

    # Initialize Omni with appropriate pipeline
    omni_instance = Omni(
        model=MODEL_PATH,
        vae_use_slicing=vae_use_slicing,
        vae_use_tiling=vae_use_tiling,
        cache_backend=None,
        cache_config=None,
        parallel_config=parallel_config,
    )

    logger.info("Model loaded successfully")


# ==================== Shutdown Event ====================
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global omni_instance
    if omni_instance:
        omni_instance.close()
        logger.info("Model resources released")


# ==================== API Endpoints ====================
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MiroImage API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI API compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": int(time.time()),
            }
        ],
    }


@app.post("/v1/chat/completions")
async def create_chat_completion(request: ImageEditRequest):
    """Image editing endpoint (OpenAI API compatible)"""
    if request.model != MODEL_NAME:
        raise HTTPException(status_code=500, detail=f"Only support {MODEL_NAME}")

    global omni_instance, generator

    if omni_instance is None:
        raise HTTPException(status_code=503, detail="Model not yet loaded")

    try:
        # Parse messages
        prompt, input_images = parse_messages(request.messages)

        # Use single image or list of images
        if len(input_images) == 1:
            input_image = input_images[0]
        else:
            input_image = input_images

        # Set random seed
        generator.manual_seed(request.seed)

        logger.info(f"Starting image generation, prompt: {prompt}")
        generation_start = time.perf_counter()

        # Generate image
        generate_kwargs = {
            "prompt": prompt,
            "pil_image": input_image,
            "negative_prompt": " ",
            "generator": generator,
            "true_cfg_scale": request.cfg_scale,
            "guidance_scale": request.guidance_scale,
            "num_inference_steps": request.num_inference_steps,
            "num_outputs_per_prompt": 1,
            "layers": request.layers,
            "resolution": request.resolution,
        }

        outputs = omni_instance.generate(**generate_kwargs)
        generation_end = time.perf_counter()
        generation_time = generation_end - generation_start

        logger.info(f"Image generation completed, time: {generation_time:.4f}s")

        if not outputs:
            raise HTTPException(
                status_code=500, detail="Generation failed, no output returned"
            )

        # Extract images
        first_output = outputs[0]
        if (
            not hasattr(first_output, "request_output")
            or not first_output.request_output
        ):
            raise HTTPException(status_code=500, detail="Invalid output format")

        req_out = first_output.request_output[0]
        if not isinstance(req_out, dict) or "images" not in req_out:
            raise HTTPException(status_code=500, detail="No images found in output")

        images = req_out["images"]
        if not images:
            raise HTTPException(status_code=500, detail="Generated image list is empty")

        # Convert to base64
        result_images = []
        img = images[0]

        if isinstance(img, list):
            # Multi-layer output
            for sub_img in img:
                base64_img = image_to_base64(sub_img)
                result_images.append(f"![image]({base64_img})")
        else:
            # Single image
            base64_img = image_to_base64(img)
            result_images.append(f"![image]({base64_img})")

        # Construct OpenAI API compatible response
        response = ImageEditResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "\n".join(result_images),
                    },
                    "finish_reason": "stop",
                }
            ],
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error occurred during image generation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ==================== Main Entry Point ====================
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MIROIMAGE_HOST", "0.0.0.0")
    port = int(os.getenv("MIROIMAGE_PORT", "8081"))

    uvicorn.run(app, host=host, port=port, log_level="info")
