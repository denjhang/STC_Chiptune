# Keil C51 编译踩坑记录

## 假编译问题（2026-06-08）

### 现象

修改 `main.c` 后编译，输出显示 0 错误 0 警告，hex 文件时间戳更新，但烧录后**程序行为完全没变**。

### 原因

C51.exe 的 `OBJECT(build\main)` 参数**不会生效**，OBJ 文件始终输出到**源文件所在目录**（`src\main.OBJ`）。

当 `src\main.OBJ` 已存在且比 `main.c` 新时，C51.exe **跳过编译**，直接输出：

```
C51 COMPILATION COMPLETE.  0 WARNING(S),  0 ERROR(S)
```

没有任何提示说跳过了编译。BL51.exe 链接的是旧的 `src\main.OBJ`，所以代码根本没更新。

### 正确做法

**编译时不要带 `OBJECT` 参数**：

```powershell
# ✅ 正确
D:\Keil_v5\C51\BIN\C51.exe src\main.c OPTIMIZE(8,SPEED) INCDIR(include)
# OBJ 自动输出到 src\main.OBJ

# ❌ 错误（OBJECT 参数无效，但可能阻止重编译）
D:\Keil_v5\C51\BIN\C51.exe src\main.c OPTIMIZE(8,SPEED) INCDIR(include) OBJECT(build\main)
```

### 强制重编译

每次修改代码后，先删除旧 OBJ 再编译：

```powershell
Remove-Item 'STC8H8K64\src\main.OBJ' -Force -ErrorAction SilentlyContinue
```

### 完整编译命令（PowerShell 一行）

```powershell
Set-Location 'D:\working\vscode-projects\STC_Chiptune\STC8H8K64'; Remove-Item 'src\main.OBJ' -Force -ErrorAction SilentlyContinue; & 'D:\Keil_v5\C51\BIN\C51.exe' 'src\main.c' 'OPTIMIZE(8,SPEED)' 'INCDIR(include)'; & 'D:\Keil_v5\C51\BIN\BL51.exe' 'src\main.OBJ' 'TO' 'build\main'; & 'D:\Keil_v5\C51\BIN\OH51.exe' 'build\main'; Copy-Item 'build\main.hex' '..\firmware.hex' -Force
```

### go.bat 需同步修改

`STC8H8K64/go.bat` 中的 `%KEIL_C51%\BIN\C51.exe` 行应去掉 `OBJECT(%OUT%)` 参数，并确保 BL51 引用的是 `src\main.OBJ`。

## 其他已知坑

| 问题 | 原因 | 解决 |
|------|------|------|
| `delay()` 被优化掉 | `OPTIMIZE(8,SPEED)` 优化空循环 | 循环变量加 `volatile` |
| 变量声明位置报错 | Keil C51 用 C89 标准 | 变量必须在函数体顶部声明 |
| P_SW2=0x80 导致 Timer 不触发 | XFR 映射影响 | PWM 相关操作临时开关 P_SW2，不要保持 |
| `using 1` 寄存器组兼容问题 | 官方 demo 不用 | 不使用 `using` 关键字 |
| **`data` 是保留关键字** | C51 memory type (`data`/`idata`/`xdata`/`pdata`/`code`) | 变量名不能用 `data`，用 `dat` 替代 |
| **`s8` 类型转换 `(s8)x` 不可用** | C51 不支持 typedef 别名做 cast | 用 `signed char` 显式写，或避免有符号转换 |
| **struct 内不能有 xdata 数组** | `scc_channel_t { xdata s8 waveram[32]; }` 报错 | struct 改用平坦 xdata 全局变量 |
| **函数名 C51 加 `_` 前缀** | `scc_write()` 编译为 `_scc_write`，调用处也加前缀 | 函数名不要和库函数冲突 |
| **case 内不能声明变量** | C89 限制 | 变量声明在函数/块顶部 |
