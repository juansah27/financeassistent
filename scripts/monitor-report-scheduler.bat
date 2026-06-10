@echo off
echo ============================================
echo Monitor WhatsApp Auto Report Scheduler
echo ============================================
echo.
echo Monitoring scheduler logs for WhatsApp reports...
echo Press Ctrl+C to stop
echo.
echo ============================================
echo.

docker-compose logs -f web | findstr /i "whatsapp report schedule sent"
