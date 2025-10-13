@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Static IP Setup Guide
echo ========================================
echo.
echo [Opening Windows Network Settings]
echo.
pause

REM Open network settings
start ms-settings:network-ethernet

echo.
echo ========================================
echo How to Set Static IP
echo ========================================
echo.
echo 1. Click "Ethernet" or "Wi-Fi"
echo 2. Click "IP assignment" - "Edit"
echo 3. Select "Manual"
echo 4. Turn on IPv4
echo 5. Enter the following information:
echo.
echo    IP Address:   192.168.0.XXX  (e.g., 192.168.0.101)
echo    Subnet:       255.255.255.0
echo    Gateway:      192.168.0.1    (router IP, usually .1 or .254)
echo    DNS:          8.8.8.8        (Google DNS)
echo    Alt DNS:      8.8.4.4
echo.
echo 6. Click "Save"
echo.
echo ========================================
echo Recommended IP Assignment (SAFE RANGE)
echo ========================================
echo.
echo OPTION 1: High Range (Safest) - Recommended
echo ------------------------------------------------
echo Admin PC:     192.168.0.200
echo Kiosk 1:      192.168.0.201
echo Kiosk 2:      192.168.0.202
echo Kiosk 3:      192.168.0.203
echo.
echo OPTION 2: Medium Range
echo ------------------------------------------------
echo Admin PC:     192.168.0.150
echo Kiosk 1:      192.168.0.151
echo Kiosk 2:      192.168.0.152
echo Kiosk 3:      192.168.0.153
echo.
echo * DHCP is usually: 192.168.0.2 ~ 192.168.0.100
echo * Using .200+ avoids conflicts with DHCP
echo * Check your router: http://192.168.0.1
echo.
pause

