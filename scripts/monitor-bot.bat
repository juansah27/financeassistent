@echo off
echo ============================================
echo WhatsApp Bot Real-Time Monitor
echo ============================================
echo.
echo Bot Status:
docker ps | findstr whatsapp
echo.
echo Listening for messages... (Press Ctrl+C to stop)
echo.
docker logs finance_whatsapp_bot -f --tail 5
