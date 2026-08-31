#!/usr/bin/env pwsh
set -e

$IMAGE_NAME = "recsys-service"
$TAR_PATH = "D:\Skillbox_for_VS\python\DIplom\image.tar"
$MODELS_PATH = "D:\Skillbox_for_VS\python\DIplom\models"

Write-Host "=== Building Docker image ===" -ForegroundColor Cyan
docker build -t $IMAGE_NAME .

Write-Host "`n=== Exporting image to $TAR_PATH ===" -ForegroundColor Cyan
docker save -o $TAR_PATH $IMAGE_NAME
Write-Host "Image saved: $TAR_PATH"

Write-Host "`n=== Running container ===" -ForegroundColor Cyan
Write-Host "docker run -p 8000:8000 -v ${MODELS_PATH}:/app/models $IMAGE_NAME"
Write-Host ""
Write-Host "Service will be available at http://localhost:8000" -ForegroundColor Green
Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Green
