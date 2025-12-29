"""
MiroShape FastAPI Server
Provides API service for image to 3D model generation
"""

import io
import os
import sys
import uuid

# Add parent directory to Python path to enable imports
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "miroshape"
    ),
)

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from rembg import remove
from typing import Optional

from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
from image_utils import load_image_from_base64, load_image_from_url


# ==================== Configuration ====================
MODEL_PATH = os.getenv(
    "MIROSHAPE_MODEL_PATH",
    "IntimeAI/Miro",
)
OUTPUT_DIR = os.getenv("MIROSHAPE_OUTPUT_DIR", "./output/output_shape")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==================== FastAPI Application ====================
app = FastAPI(
    title="MiroShape API",
    description="Image to 3D Model Generation Service API",
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
PIPELINE_SHAPEGEN = None


# ==================== Startup Event ====================
@app.on_event("startup")
async def startup_event():
    """Initialize model pipeline on startup"""
    global PIPELINE_SHAPEGEN
    print("Loading MiroShape model pipeline...")
    PIPELINE_SHAPEGEN = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(MODEL_PATH)
    print("Model pipeline loaded successfully")


# ==================== API Endpoints ====================


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MiroShape API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.post("/generate3d")
async def generate_3d_model(
    file: Optional[UploadFile] = File(
        None, description="Input image file (supports PNG, JPG, JPEG, etc.)"
    ),
    image_base64: Optional[str] = Form(None, description="Base64 encoded image string"),
    image_url: Optional[str] = Form(None, description="URL of the image to download"),
):
    """
    Generate 3D model from image

    Supports three input methods:
    1. File upload: Use multipart/form-data with 'file' field
    2. Base64: Use JSON body with 'image_base64' field
    3. URL: Use JSON body with 'image_url' field

    Args:
        file: Uploaded image file (optional)
        image_base64: Image input via base64 (optional)
        image_url: Image input via URL (optional)

    Returns:
        Binary GLB file as response
    """
    task_id = str(uuid.uuid4())

    try:
        image = None

        # Priority: file upload > base64 > URL
        if file is not None:
            # Validate file type
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file type, please upload an image file",
                )

            # Read uploaded image
            image_data = await file.read()
            image = Image.open(io.BytesIO(image_data))

        elif image_base64:
            # Load from base64
            image = load_image_from_base64(image_base64)
        elif image_url:
            # Load from URL
            image = load_image_from_url(image_url)
        else:
            raise HTTPException(
                status_code=400,
                detail="No image input provided. Please provide file, image_base64, or image_url",
            )

        # Convert to RGB mode if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Remove background
        image = remove(image)

        # Generate 3D model
        mesh = PIPELINE_SHAPEGEN(image=image)[0]

        # Save model file
        output_filename = f"{task_id}.glb"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        mesh.export(output_path)

        # Return success response
        with open(output_path, "rb") as f:
            output_content = f.read()

        if os.path.exists(output_path):
            os.remove(output_path)

        return Response(
            content=output_content,
            media_type="application/octet-stream",
            headers={
                f"Content-Disposition": f"attachment; filename={output_filename}",
                "Content-Type": "model/gltf-binary",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating 3D model (task_id: {task_id}): {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate 3D model: {str(e)}"
        )


# ==================== Main Entry Point ====================
if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment variables
    host = os.getenv("MIROSHAPE_HOST", "0.0.0.0")
    port = int(os.getenv("MIROSHAPE_PORT", "8080"))

    uvicorn.run(app, host=host, port=port, log_level="info")
