# YM2413 工作交接 (2026-06-25)

## 当前下位机状态 (commit 9327509)
- ym2413.c 退回到 9327509 (u16 8.8 定点优化版, 稳定)
- 旋律 ch0-8 (9通道), 只渲染 ch0-5 (6通道省CPU)
- 鼓声: BD/TOM/HH/CYM 单 op 简化路径 (YM_DRUM 结构)
- SD: 单 op noise 25Hz (独立2-op版本听感好但性能/包络问题待解决)
- ISR 22050Hz, 偶尔卡 (6通道同发时)

## 鼓声参数 (当前 9327509 版)
```
BD:  sin 100Hz, vol=16, env_step=14 (~20ms)
TOM: sin 214Hz(ml5), vol=8, env_step=14 (~20ms)  
HH:  noise 755Hz, vol=2, env_step=46 (~65ms)
CYM: noise 755Hz, vol=2, env_step=255 (~360ms)
SD:  noise 25Hz, vol=8, env_step=28 (~40ms) [单op]
```
注意: step 是 8.8 定点 (freq×64×256/22050)

## SD 2-op 历史版本
- **2407ccb**: 独立 2-op (data区 oneshot), 听感短促可接受
  - mod=noise(25Hz,FB=2) 调制 car=sin(240Hz)
  - mod: DEC=7 SUL=0 REL=7 TL=15 (快衰减)
  - car: DEC=7 SUL=19 REL=28 TL=31 (慢衰减)
  - 问题: 听感和真2op有区别 (之前完整2op走ym_render_fm听感最好)
- **b1b022a**: ch6 真 2-op (ym_render_fm), 听感最好但和旋律抢round-robin + ISR卡
- **ec8ab1b**: ch9 真 2-op (u16优化后), ADSR在round-robin下无限长
- **结论**: SD 2-op 需要 data区独立路径(不走round-robin), 参考drum_fw_sim.py

## 关键代码位置 (9327509)
- YM_DRUM 结构: ym2413.c ~line 155
- ym_drum_trigger: ~line 520
- ym_render_drum: ~line 540
- ym_render_fm: ~line 570 (旋律2-op, u16 8.8定点)
- ym2413_render: ~line 620 (ch0-5旋律 + 鼓声)
- 边沿触发: ym_update_keys ~line 310 (ym_prev_drum_bits)
- 鼓声init参数: ~line 395

## PC 工具
- `tools/drum_fw_sim.py`: 鼓声 PC 仿真 (参数固化, 但用的是onshot不是round-robin)
- `tools/fw_real_sim.py`: 旋律 1:1 下位机仿真
- `tools/ym2413_wav_gen.py`: emu2413 忠实移植 + V3 调参

## 待解决问题
1. **ISR 性能**: 6通道同发偶尔卡, 需进一步优化 ym_render_fm
2. **SD 2-op**: 独立路径(2407ccb)听感可接受但不完美, data区 oneshot 方案
3. **鼓声长度**: 需要在 PC 上用 round-robin 真实仿真验证
4. **STC32G12K128 fm.c**: 16通道不卡的参考实现, 关键是 u16 8.8 定点

## 规则
- 先 PC 仿真验证, 再改下位机
- fw_real_sim.py 必须和下位机同步
- 只改数值/表, 不改架构
- 鼓声是上升沿触发 (VGM reg 0x0E bit 0→1), 无显式 key_off
- 鼓声必须定长度 (oneshot 自衰减), 不能依赖 VGM 的 key_off
