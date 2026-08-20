@echo off
echo ========================================================
echo   Building PS5 LiveContainer via Docker Toolchain
echo ========================================================

REM Build the SDK Docker image if not already built
docker build -t ps5-sdk .

REM Run the build inside Docker container with CRLF line ending cleanup
docker run --rm -v "%cd%:/app" ps5-sdk bash -c "sed -i 's/\r$//' Makefile src/*.c include/*.h test_payloads/*/*.c test_payloads/*/*Makefile 2>/dev/null; make"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Built ps5_livecontainer.elf and test payloads!
) else (
    echo.
    echo [ERROR] Build failed! Check compiler logs above.
)
pause
