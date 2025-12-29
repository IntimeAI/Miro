import os
from rembg import remove
from PIL import Image

from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline

image_path = "examples/example.png"
image = Image.open(image_path)

image = remove(image)

model_path = "IntimeAI/Miro"
pipeline_shapegen = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_path)

mesh = pipeline_shapegen(image=image)[0]

os.makedirs("output", exist_ok=True)
mesh.export("output/example.glb")
