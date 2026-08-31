$IMAGE_NAME = "recsys-service"
$TAR_PATH = "D:\Skillbox_for_VS\python\DIplom\image.tar"
$MODELS_PATH = "D:\Skillbox_for_VS\python\DIplom\models"

Write-Host "=== Checking Docker ===" -ForegroundColor Cyan
docker version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Building Docker image ===" -ForegroundColor Cyan
docker build -t $IMAGE_NAME .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Exporting image to $TAR_PATH ===" -ForegroundColor Cyan
docker save -o $TAR_PATH $IMAGE_NAME
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker save failed." -ForegroundColor Red
    exit 1
}
Write-Host "Image saved: $TAR_PATH" -ForegroundColor Green

Write-Host "`n=== Ready! ===" -ForegroundColor Green
Write-Host "To run the container:" -ForegroundColor Cyan
Write-Host "  docker run -p 8000:8000 -v ${MODELS_PATH}:/app/models $IMAGE_NAME"
Write-Host ""
Write-Host "Service: http://localhost:8000" -ForegroundColor Green
Write-Host "Docs:    http://localhost:8000/docs" -ForegroundColor Green
