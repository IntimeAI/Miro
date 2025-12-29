#!/bin/bash
# Miroshape Server script

CUDA_VISIBLE_DEVICES=0 \
MIROSHAPE_MODEL_PATH=IntimeAI/Miro \
MIROSHAPE_OUTPUT_DIR=./output/output_shape \
MIROSHAPE_HOST=0.0.0.0 \
MIROSHAPE_PORT=8080 \
python3 servers/miroshape_server.py
