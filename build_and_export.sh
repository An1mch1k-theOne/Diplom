#!/usr/bin/env bash
set -e

IMAGE_NAME="recsys-service"
TAR_PATH="D:/Skillbox_for_VS/python/DIplom/image.tar"
MODELS_PATH="D:/Skillbox_for_VS/python/DIplom/models"

echo "=== Building Docker image ==="
docker build -t "$IMAGE_NAME" .

echo ""
echo "=== Exporting image to $TAR_PATH ==="
docker save -o "$TAR_PATH" "$IMAGE_NAME"
echo "Image saved: $TAR_PATH"

echo ""
echo "=== Running container ==="
echo "docker run -p 8000:8000 -v $MODELS_PATH:/app/models $IMAGE_NAME"
echo ""
echo "Service will be available at http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
