@echo off
echo ============================================
echo Real-Time Scheduler Monitor
echo ============================================
echo.
echo Watching for WhatsApp auto report...
echo Schedule: 21:00
echo Next check: 21:05
echo.
echo Press Ctrl+C to stop
echo ============================================
echo.

docker-compose logs -f web 2>&1 | findstr /i "whatsapp report schedule sent generating current time hour 21"
