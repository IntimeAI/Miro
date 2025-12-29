import trimesh
import pyrender
import numpy as np
import os
from PIL import Image

# 1. Force use of EGL backend
os.environ["PYOPENGL_PLATFORM"] = "egl"


def render_image(glb_path, output_path):
    # Load model
    tm_scene = trimesh.load(glb_path)
    scene = pyrender.Scene.from_trimesh_scene(tm_scene)

    # --- Key improvement: Ambient light and background ---
    # Reduce ambient light intensity to avoid flat appearance and allow shadows to show
    scene.ambient_light = [0.2, 0.2, 0.2]

    # --- Key improvement: Three-point lighting ---
    centroid = tm_scene.centroid
    scale = tm_scene.extents.max()

    # 1. Key Light: Strong light from 45 degrees above, creates main shadows
    key_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=3.0)
    key_pose = np.eye(4)
    key_pose[:3, 3] = centroid + [scale, scale, scale]  # Upper right
    scene.add(key_light, pose=key_pose)

    # 2. Fill Light: Soft light from another side, eliminates overly dark areas
    fill_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.0)
    fill_pose = np.eye(4)
    fill_pose[:3, 3] = centroid + [-scale, 0, scale]  # Left side
    scene.add(fill_light, pose=fill_pose)

    fill_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.0)
    fill_pose = np.eye(4)
    fill_pose[:3, 3] = centroid + [scale, 0, scale]  # Right side
    scene.add(fill_light, pose=fill_pose)

    fill_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.0)
    fill_pose = np.eye(4)
    fill_pose[:3, 3] = centroid + [-scale, 0, -scale]
    scene.add(fill_light, pose=fill_pose)

    fill_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.0)
    fill_pose = np.eye(4)
    fill_pose[:3, 3] = centroid + [scale, 0, -scale]
    scene.add(fill_light, pose=fill_pose)

    # 3. Rim Light/Back Light: From behind, outlines edges, adds depth
    rim_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=3.0)
    rim_pose = np.eye(4)
    rim_pose[:3, 3] = centroid + [0, scale, -scale]  # Upper back
    scene.add(rim_light, pose=rim_pose)

    # --- Key improvement: Camera position adjusted to 45-degree viewing angle ---
    # Avoid direct view, side view provides better texture
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 4.0)

    # Calculate an oblique viewing camera matrix
    eye = centroid + np.array([scale * 0.25, scale * 0.25, scale * 1.25]) * 1.25
    target = centroid
    up = np.array([0, 1, 0])

    # Construct LookAt matrix
    z_axis = (eye - target) / np.linalg.norm(eye - target)
    x_axis = np.cross(up, z_axis)
    x_axis /= np.linalg.norm(x_axis)
    y_axis = np.cross(z_axis, x_axis)

    camera_pose = np.eye(4)
    camera_pose[:3, 0] = x_axis
    camera_pose[:3, 1] = y_axis
    camera_pose[:3, 2] = z_axis
    camera_pose[:3, 3] = eye

    scene.add(camera, pose=camera_pose)

    # --- 4. Render ---
    r = pyrender.OffscreenRenderer(viewport_width=1248, viewport_height=832)
    # Enable anti-aliasing (enabled by default)
    color, depth = r.render(scene, flags=pyrender.RenderFlags.RGBA)

    # 5. Save result
    img_rgba = Image.fromarray(color)

    img_rgba.save(output_path)

    r.delete()
