#!/usr/bin/env python3
"""AutoLooping.py — 移植 LoopAuditioneer 自动找 loop 算法

算法:
1. 找候选点: |x[i+1] - x[i]| < max_derivative * threshold
2. 配对: start 从前往后, end 从后往前, 最长优先
3. 质量评估: 5 点窗口绝对差累加 (越小越好)
4. 筛选: quality <= quality_factor 的进入候选

参数 (来自 LoopAuditioneer AutoLooping 构造函数):
  threshold         = 0.05   导数阈值比例 (相对 max_derivative)
  minLoopDuration   = 0.3    最短 loop 秒数
  distanceBetweenLoops = 0.1 loop 间最小间隔 (秒)
  quality           = 1.0    质量阈值 (5 点窗口差累加)
  maxCandidates     = 5000   候选点上限
  loopsToReturn     = 5      返回 loop 数量
"""

import math


def find_loop_candidates(pcm, derivative_threshold_ratio=0.05, max_candidates=5000):
    """找波形导数小于阈值的候选点 (LoopAudioner 第一步)"""
    n = len(pcm)
    if n < 10:
        return []

    # 1. 找最大导数
    max_deriv = 0.0
    for i in range(n - 1):
        d = abs(pcm[i + 1] - pcm[i])
        if d > max_deriv:
            max_deriv = d

    if max_deriv < 1e-6:
        return list(range(n - 1))

    threshold = max_deriv * derivative_threshold_ratio

    # 2. 收集所有低于阈值的候选
    every = []
    for i in range(n - 1):
        if abs(pcm[i + 1] - pcm[i]) < threshold:
            every.append(i)

    # 3. 如果候选太多, 均匀抽样到 max_candidates
    if len(every) > max_candidates:
        step = len(every) / max_candidates
        return [every[int(i * step)] for i in range(max_candidates)]
    return every


def loop_quality(pcm, start, end):
    """5 点窗口绝对差累加 (LoopAudioner CalculateLoopQuality)

    注意 LoopAudioner: start -= 5, end -= 4 (5 个采样窗口)
    """
    if start < 5 or end < start + 5 or end >= len(pcm) - 1:
        return 1e9
    s = start - 5
    e = end - 4
    diff = 0.0
    for j in range(5):
        diff += abs(pcm[s + j] - pcm[e + j])
    return diff


def find_best_loops(pcm, rate,
                    threshold_ratio=0.05,
                    min_loop_sec=0.3,
                    distance_sec=0.1,
                    quality_factor=1.0,
                    max_candidates=5000,
                    loops_to_return=5,
                    search_start_ratio=0.5,
                    search_end_ratio=1.0):
    """返回 [(start, end, quality), ...] 按质量升序

    search_start_ratio / search_end_ratio:
        限制搜索区间, 默认只搜后一半 (避开 attack 段).
        例如 0.7-1.0 只搜最后 30%.
    """
    min_loop_samples = int(rate * min_loop_sec)
    distance_samples = int(rate * distance_sec)

    n_total = len(pcm)
    search_lo = int(n_total * search_start_ratio)
    search_hi = int(n_total * search_end_ratio)
    search_pcm = pcm[search_lo:search_hi]

    candidates_rel = find_loop_candidates(search_pcm, threshold_ratio, max_candidates)
    if len(candidates_rel) < 2:
        return []
    # 转回原 pcm 索引
    candidates = [c + search_lo for c in candidates_rel]

    # 配对: start 从前往后, end 从后往前
    found = []
    n = len(candidates)

    for i in range(n - 1):
        start = candidates[i]
        if start < 5:
            continue

        # 跳过离最近已找到 loop 太近的
        if found and (start - found[-1][0]) < distance_samples:
            continue

        for j in range(n - 1, i, -1):
            end = candidates[j]
            if end - start < min_loop_samples:
                continue
            if end >= n_total - 1:
                continue

            q = loop_quality(pcm, start, end)
            if q <= quality_factor:
                found.append((start, end, q))
                break

        if len(found) >= loops_to_return * 3:
            break

    found.sort(key=lambda x: x[2])
    return found[:loops_to_return]


def find_best_loop(pcm, rate, **kwargs):
    """返回最佳单个 (start, end, quality), 没找到返回 None"""
    loops = find_best_loops(pcm, rate, **kwargs)
    return loops[0] if loops else None
