@echo off
cd /d "D:\working\vscode-projects\STC_Chiptune\STC32G12K128"

del /q *.OBJ 2>nul
if not exist build mkdir build

echo === Compile ay8910.c ===
D:\Keil_v5\C251\BIN\C251.EXE ay8910.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Compile scc.c ===
D:\Keil_v5\C251\BIN\C251.EXE scc.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Compile sn76489.c ===
D:\Keil_v5\C251\BIN\C251.EXE sn76489.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Compile gb.c ===
D:\Keil_v5\C251\BIN\C251.EXE gb.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Compile nes.c ===
D:\Keil_v5\C251\BIN\C251.EXE nes.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Compile saa1099.c ===
D:\Keil_v5\C251\BIN\C251.EXE saa1099.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Compile fm.c ===
D:\Keil_v5\C251\BIN\C251.EXE fm.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Compile main.c ===
D:\Keil_v5\C251\BIN\C251.EXE main.c LARGE OPTIMIZE(8,SPEED) NOALIAS
if %ERRORLEVEL% NEQ 0 goto :fail

echo === Link ===
D:\Keil_v5\C251\BIN\l251.exe ay8910.OBJ,scc.OBJ,sn76489.OBJ,gb.OBJ,nes.OBJ,saa1099.OBJ,fm.OBJ,main.OBJ TO build\MAIN
if %ERRORLEVEL% NEQ 0 goto :fail

echo === HEX ===
D:\Keil_v5\C251\BIN\OH251.EXE build\MAIN HEXFILE(build\MAIN.hex)
if %ERRORLEVEL% NEQ 0 goto :fail

echo BUILD OK: build\MAIN.hex
exit /b 0
:fail
echo BUILD FAILED
exit /b 1
