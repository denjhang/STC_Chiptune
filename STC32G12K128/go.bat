@echo off
cd /d "D:\working\vscode-projects\STC_Chiptune\STC32G12K128"

echo === Compile ===
D:\Keil_v5\C251\BIN\C251.EXE main.c SMALL BROWSE DEBUG
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Link ===
D:\Keil_v5\C251\BIN\l251.exe main.OBJ TO test
if %ERRORLEVEL% NEQ 0 goto :fail

echo === HEX ===
D:\Keil_v5\C251\BIN\OH251.EXE test HEXFILE(test.hex)
if %ERRORLEVEL% NEQ 0 goto :fail

echo BUILD OK: test.hex
exit /b 0
:fail
echo BUILD FAILED
exit /b 1
