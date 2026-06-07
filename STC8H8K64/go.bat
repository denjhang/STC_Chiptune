@echo off
cd /d %~dp0
set KEIL_C51=D:\Keil_v5\C51
set SRC=src\main.c
set INC=include
set OBJ=src\main.OBJ
set OUT=build\main

echo Compiling %SRC% ...
%KEIL_C51%\BIN\C51.exe %SRC% OPTIMIZE(8,SPEED) INCDIR(%INC%)

echo Linking ...
%KEIL_C51%\BIN\BL51.exe %OBJ% TO %OUT%

echo Generating HEX ...
%KEIL_C51%\BIN\OH51.exe %OUT%

copy /Y build\main.hex firmware.hex

echo.
echo Done: firmware.hex
