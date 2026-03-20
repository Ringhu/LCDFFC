# 初始实验结果

**日期**：2026-03-19  
**计划来源**：`refine-logs/EXPERIMENT_PLAN.md`

## 本轮做了什么

本轮按照 `experiment-bridge` 的要求，完成了 `M0-M2` 的最小桥接实现与首批实验：

1. 新增了偏好切换评测脚本：
   - `eval/run_preference_shift.py`
2. 新增了偏好切换评分与汇总脚本：
   - `eval/preference_shift_metrics.py`
   - `eval/summarize_preference_shift.py`
3. 新增了 4 类高层路由变体：
   - `fixed`
   - `heuristic`
   - `numeric`
   - `text-template`
4. 新增了对应单测：
   - `tests/test_preference_shift.py`

## GPU 使用

- 小测试：
  `GPU 3`
- 完整第一批实验：
  `GPU 2`

已完成的实际运行：

- `CUDA_VISIBLE_DEVICES=3`：96 步 `text router` sanity
- `CUDA_VISIBLE_DEVICES=2`：8 组完整 719 步实验

## Sanity 阶段

### M0: Sanity — PASSED

短程 sanity 命令在 `GPU 3` 上通过：

```bash
CUDA_VISIBLE_DEVICES=3 python eval/run_preference_shift.py \
  --schema /cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json \
  --checkpoint artifacts/checkpoints/gru_mse_best.pt \
  --norm_stats artifacts/norm_stats.npz \
  --forecast_config configs/forecast.yaml \
  --controller_config configs/controller.yaml \
  --output_dir /tmp/pref_shift_gpu3_sanity \
  --tag sanity_text_gpu3 \
  --router_type text \
  --forecast_mode learned \
  --device cuda:0 \
  --max_steps 96
```

结果：

- 训练 / 推理主循环正常
- 输出文件格式正常：
  - `*_kpis.json`
  - `*_segments.json`
  - `*_routes.json`
  - `*_actions.npy`

## M1: 固定权重 baseline

在 `GPU 2` 上完成了 5 组完整固定权重对照：

- `fixed_balanced`
- `fixed_cost`
- `fixed_carbon`
- `fixed_peak`
- `fixed_reserve`

关键 KPI：

| Run | cost | carbon | peak |
|---|---:|---:|---:|
| fixed_balanced | 30.4596 | 466.7547 | 14.9948 |
| fixed_cost | 31.0128 | 476.7996 | 15.1639 |
| fixed_carbon | 30.5682 | 468.2660 | 15.0019 |
| fixed_peak | 30.5412 | 467.8788 | 14.9948 |
| fixed_reserve | 30.6500 | 469.8930 | 15.0034 |

当前信号：

- 在这套 `preference-shift` 评分体系下，`fixed_balanced` 与 `fixed_carbon / fixed_reserve` 已经非常强
- 这说明后续 router 想要立住论文主张，必须在“偏好切换适配”上明显超过这些固定变体

## M2: Router 雏形

在 `GPU 2` 上完成了 3 组高层路由实验：

- `heuristic_router`
- `numeric_router`
- `text_router`

关键 KPI：

| Run | cost | carbon | peak |
|---|---:|---:|---:|
| heuristic_router | 30.6447 | 470.1035 | 15.0005 |
| numeric_router | 31.3612 | 481.7459 | 14.9041 |
| text_router | 31.0553 | 477.6960 | 14.9041 |

## Preference-Shift 汇总

基于 `fixed_balanced` reference 与“相对最佳固定策略 regret”的汇总结果：

| Run | avg_preference_score | avg_regret_to_best_fixed |
|---|---:|---:|
| fixed_reserve | 0.8769 | 0.0012 |
| heuristic_router | 0.8784 | 0.0026 |
| fixed_balanced | 0.8797 | 0.0040 |
| fixed_carbon | 0.8798 | 0.0040 |
| fixed_peak | 0.8799 | 0.0042 |
| text_router | 0.8849 | 0.0092 |
| fixed_cost | 0.8968 | 0.0211 |
| numeric_router | 0.8946 | 0.0188 |

## 当前结论

### 正面信号

1. `preference-shift` 评测桥已经搭起来了
2. 低层 `forecast + QP` 在新评测脚本下保持稳定
3. `heuristic / numeric / text` 三类 router 都已经能跑完整 episode，并产出 parseable 结果
4. 第二版 `text_router_v2` 已经在完整 719 步实验中跑通

### 负面信号

1. 当前 `text-template` router 没有超过最佳固定权重
2. 当前 `numeric` router 也没有超过最佳固定权重
3. 当前 `heuristic` router 虽然优于 `text / numeric`，但仍然没有稳定优于最佳固定权重

### 对论文主张的含义

这轮结果说明：

- 当前“语言条件化高层路由”这个主张还**没有被实验支撑起来**
- 但这并不是坏事，因为它已经在第一轮最小实验里被明确暴露出来
- 这恰好说明 `experiment-bridge` 起到了作用：先用最小代价检验 thesis，而不是继续盲目扩架构

## 第二版 router 改进（text_v2）

在第一轮结果基础上，进一步做了第二版改进：

1. 把 `text_v1` 的极端关键词映射改成更平滑的文本条件候选选择
2. 补充了“相对最佳单一固定策略”的汇总口径，避免只看“regime 级最优固定策略上界”
3. 在 `GPU 3` 上完成短程 sanity，在 `GPU 2` 上完成完整 719 步实验

第二版关键结果：

| Run | avg_preference_score | avg_regret_to_best_fixed | avg_regret_to_best_single_fixed |
|---|---:|---:|---:|
| fixed_reserve | 0.876931 | 0.001224 | 0.000000 |
| heuristic_router | 0.878355 | 0.002647 | 0.001424 |
| text_router (v1) | 0.884912 | 0.009205 | 0.007981 |
| text_router_v2 | 0.876864 | 0.001157 | -0.000067 |

含义：

- `text_router_v2` 已经明显优于 `text_router v1`
- `text_router_v2` 现在**略优于最佳单一固定策略**
- 但 `text_router_v2` 仍然**没有超过“按 regime 选择最佳固定策略”的上界**

因此，当前更准确的结论是：

> 第二版已经让“语言条件化路由优于固定权重”第一次出现了正信号，但这条主张还不够稳，还需要继续扩大差距并验证鲁棒性。

## 第三版 router 与 M4 结果

### text_router_v3

为了继续放大 `v2` 的优势，又实现了 `text_router_v3`：

- 更强调“文本主偏好必须保持主导”
- 用 bounded context adjustment 替代过强的候选 profile 竞争
- 目标是减少上下文把文本主意图反客为主的情况

完整 719 步结果：

| Run | avg_preference_score | avg_regret_to_best_fixed | avg_regret_to_best_single_fixed |
|---|---:|---:|---:|
| text_router_v2 | 0.876864 | 0.001157 | -0.000067 |
| text_router_v3 | 0.878693 | 0.002986 | 0.001762 |

结论：

- `text_router_v3` 没有继续提升，反而比 `v2` 更差
- 当前最优文本路由仍然是 `text_router_v2`
- 这说明第二轮改进后的方向不应该再盲目继续“强化文本先验”，而应回到更细的协议与上下文表示设计

### M4：fallback 鲁棒性检查

对当前最优的 `text_router_v2`，做了更强的 corruption 注入：

- corruption 频率：每 `12` 步
- corruption 模式：`extreme_peak`
- 对比：
  - `route_fallback = none`
  - `route_fallback = heuristic`

结果：

| Run | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| text_v2_corrupt12_none | 30.5747 | 468.4389 | 14.9948 | 856.6183 |
| text_v2_corrupt12_fallback | 30.5831 | 468.5653 | 14.9948 | 856.5503 |

补充统计：

- 两组实验都注入了 `59` 次 corruption
- fallback 版本中 `59` 次 corruption 全部触发了 heuristic fallback
- 但 KPI 差异仍然很小

结论：

- 当前 corruption 设定下，fallback 的保护作用没有形成显著指标差异
- 更合理的解释不是“fallback 没用”，而是：
  1. 当前低层 `forecast + QP` 本身已经比较稳
  2. 当前 chosen corruption mode 还不够贴近真正会破坏控制质量的高层路由失效

因此，`M4` 当前状态应被视为：

> 已经实现并完成首轮实验，但目前结论仍偏弱，后续需要改成更贴近真实路由失效的 corruption protocol。

## 是否可以进入 auto-review-loop

- 当前状态：`YES`
- 原因：
  - 已有完整实现
  - 已有第一批 parseable 结果
  - 已经出现明确的正负信号，适合进入下一轮 review / refine

## 建议的下一步

优先顺序：

1. 保留 `text_router_v2` 作为当前最佳版本，不再把 `v3` 继续往前推
2. 分析 `text_router_v2` 和 `fixed_reserve / heuristic_router` 在各个 regime 中的剩余差距
3. 对 `preference-shift` 协议做更真实的 regime 设计，减少过于人工的切换
4. 把 `M4` 的 corruption protocol 改成更贴近真实高层路由失效的形式，而不是只做极端 peak 偏置
