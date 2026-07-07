@echo off
REM Deploy script for system redesign (Windows)
REM Run this after pulling the redesign code

echo ======================================
echo   Sieve System Redesign Deployment
echo ======================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [X] Docker is not running. Please start Docker first.
    exit /b 1
)

echo [√] Docker is running
echo.

REM Step 1: Database migration
echo [*] Step 1: Database Migration
echo ------------------------------
echo Running migration script...

REM Check if postgres container is running
docker ps | findstr postgres >nul
if errorlevel 1 (
    echo [!] PostgreSQL container not running. Starting services...
    docker-compose up -d postgres
    echo Waiting for PostgreSQL to be ready...
    timeout /t 5 /nobreak >nul
)

REM Run migration
docker exec -i sieve-postgres psql -U postgres -d sieve_db < database\migrations\001_add_redesign_columns.sql

if errorlevel 1 (
    echo [X] Database migration failed
    exit /b 1
)

echo [√] Database migration completed
echo.

REM Step 2: Rebuild containers
echo [*] Step 2: Rebuild Containers
echo ------------------------------
echo Rebuilding text_extractor and api_gateway...

docker-compose build api_gateway text_extractor

if errorlevel 1 (
    echo [X] Container build failed
    exit /b 1
)

echo [√] Containers rebuilt
echo.

REM Step 3: Restart services
echo [*] Step 3: Restart Services
echo ------------------------------
echo Restarting all services...

docker-compose down
docker-compose up -d

if errorlevel 1 (
    echo [X] Service restart failed
    exit /b 1
)

echo [√] Services restarted
echo.

REM Step 4: Wait for services to be healthy
echo [*] Step 4: Health Check
echo ------------------------------
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check if text_extractor is running
docker ps | findstr text_extractor >nul
if errorlevel 1 (
    echo [X] Text Extractor is not running
    exit /b 1
)

echo [√] Text Extractor is running
echo.

REM Step 5: Verification
echo [*] Step 5: Verification
echo ------------------------------

echo Checking database schema...
docker exec -i sieve-postgres psql -U postgres -d sieve_db -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='tasks' AND column_name='message_type';" | findstr message_type >nul

if errorlevel 1 (
    echo [X] New columns not found in database
    exit /b 1
)

echo [√] New columns verified in database

echo Checking Redis connection...
docker exec -i redis redis-cli PING | findstr PONG >nul
if errorlevel 1 (
    echo [X] Redis connection failed
    exit /b 1
)

echo [√] Redis is responding
echo.

echo ======================================
echo   [√] Deployment Complete!
echo ======================================
echo.
echo [*] Next Steps:
echo 1. Check logs: docker-compose logs -f text_extractor
echo 2. Test message buffer: docker exec -i redis redis-cli LRANGE buffer:messages:-GROUP_ID 0 -1
echo 3. Send test messages to verify new features
echo.
echo [*] Documentation: docs\REDESIGN_IMPLEMENTATION.md
echo.

pause
