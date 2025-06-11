# Script para ejecutar flujo PAD desde Microsoft Store
Write-Host "🚀 Ejecutando flujo Gaming desde PAD Store..." -ForegroundColor Green

try {
    # Buscar PAD instalado desde Store
    $padApps = Get-AppxPackage -Name "*PowerAutomate*"
    
    if ($padApps) {
        Write-Host "✅ Power Automate Desktop encontrado (Microsoft Store)" -ForegroundColor Green
        
        # Ejecutar flujo por nombre
        $flowName = "envio_masivo"
        
        # Comando para ejecutar desde Store
        Start-Process -FilePath "ms-powerautomate:" -ArgumentList "flow=$flowName" -Wait
        
        Write-Host "✅ Comando enviado exitosamente!" -ForegroundColor Green
        
    } else {
        Write-Host "❌ Power Automate Desktop no encontrado" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    
    # Método alternativo: Usar URI scheme
    Write-Host "🔄 Intentando método alternativo..." -ForegroundColor Yellow
    Start-Process "ms-powerautomate://run?flowname=envio_masivo"
}

Write-Host "🎯 Proceso completado." -ForegroundColor Cyan