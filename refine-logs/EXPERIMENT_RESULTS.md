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

## 经 review 选中的下一版：text_router_v4

在 `v1-v3` 结果基础上，做了一次显式的本地 review，结论是：

> 不再继续让语言层自由合成连续权重，而是让语言层优先在“已经被实验验证过较强”的 fixed experts 之间做选择 / 轻量混合。

基于这条 reviewed idea，实现了：

- `text_router_v4`

它的核心思想是：

- 文本先决定主偏好
- 主偏好再映射到一组经过实验验证的 expert profiles
- 路由层只在这些 expert 之间做受限选择与轻量混合，而不是完全自由生成

完整 GPU2 结果：

| Run | avg_preference_score | avg_regret_to_best_fixed | avg_regret_to_best_single_fixed |
|---|---:|---:|---:|
| fixed_reserve | 0.876931 | 0.001224 | 0.000000 |
| heuristic_router | 0.878355 | 0.002647 | 0.001424 |
| text_router_v2 | 0.876864 | 0.001157 | -0.000067 |
| text_router_v3 | 0.878693 | 0.002986 | 0.001762 |
| text_router_v4 | 0.876622 | 0.000914 | -0.000309 |

结论：

- `text_router_v4` 比 `text_router_v2` 更好
- `text_router_v4` 继续优于最佳单一固定控制器
- `text_router_v4` 也进一步缩小了与 regime-wise best fixed 上界的差距

这意味着：

> 当前最优的文本路由版本已经从 `v2` 更新为 `v4`，并且这次改进不是盲调，而是一次有 review 支撑的改进方向。

## 是否可以进入 auto-review-loop

- 当前状态：`YES`
- 原因：
  - 已有完整实现
  - 已有第一批 parseable 结果
  - 已经出现明确的正负信号，适合进入下一轮 review / refine

## 建议的下一步

优先顺序：

1. 保留 `text_router_v4` 作为当前最佳版本
2. 继续分析 `text_router_v4` 与 regime-wise best fixed 上界之间的剩余差距
3. 对 `preference-shift` 协议做更真实的 regime 设计，减少过于人工的切换
4. 重做 `M4` 的 corruption protocol，使其更贴近真实高层路由失效

## `text_router_v4` 是否已经是最好

这次专门把“最好”拆成两个层次来判断：

1. **它是否是当前已经验证过的文本路由里最强的版本**
2. **它是否已经可以被宣称为全局最优或没有进一步改进空间**

结论是：

> `text_router_v4` 已经可以固定为 **当前已验证的最佳文本路由版本**，但还**不能**宣称它已经是“做到头了”的全局最优。

### 为什么可以固定为当前 best

在同一套 `GPU2`、同一条 `preference-shift` 协议、同一评分脚本下，`v4` 同时满足：

| Run | avg_preference_score | avg_regret_to_best_fixed | avg_regret_to_best_single_fixed |
|---|---:|---:|---:|
| text_router_v2 | 0.876864 | 0.001157 | -0.000067 |
| text_router_v3 | 0.878693 | 0.002986 | 0.001762 |
| text_router_v4 | 0.876622 | 0.000914 | -0.000309 |

这意味着：

- 在当前已测试的文本路由候选中，`v4` 的 `avg_preference_score` 最低
- `v4` 对 regime-wise best fixed 上界的平均 regret 也最低
- `v4` 继续优于最佳单一固定控制器 `fixed_reserve`

更细一层看，`v4` 相对 `v2` 的优势不是只体现在单一平均数上：

- `cost` 段：`v4` 更好
- `carbon` 段：`v4` 更好
- `peak` 段：`v4` 略好
- `reserve` 段：`v2` 仍略好

因此，`v4` 不是“四段全胜”，但它在当前汇总目标下给出了最好的整体折中。

### 为什么不能把它说成全局最优

如果要说“已经做到最好”，至少需要满足下面两件事之一：

1. 它已经打平或逼近到几乎没有差距的可达上界
2. 在更强的后续搜索里，没有再找到更好的合理变体

当前两条都不成立。

第一，`v4` 仍然没有追平当前协议下的 regime-wise best fixed 上界：

- `text_router_v4`: `avg_regret_to_best_fixed = 0.000914`

这个值虽然很小，但它是**正数**，说明仍然存在可见剩余差距。

第二，分段结果也明确说明它还存在局部短板：

- 相比 `v2`，`v4` 在 `reserve` 段仍然更差
- 相比 `fixed_reserve`，`v4` 在 `carbon` 段并不占优

所以更准确的说法应该是：

> `text_router_v4` 是**当前搜索和验证范围内的最优文本路由**，不是已经被证明无法再改进的最终最优。

### 当前固定方式

为了把这个状态固定下来，同时避免后续实验继续手工写版本号，代码里新增了：

- `CURRENT_BEST_TEXT_ROUTER = "text_v4"`
- `make_router("text_best")`
- `eval/run_preference_shift.py --router_type text_best`

因此，从这次之后：

- `text_v4` 是当前已验证最佳版本
- 新实验默认推荐直接用 `text_best`
- 只有当后续实验在同一协议下明确超过 `v4` 时，才更新这个别名

## 继续往下的实验建议

在当前证据下，最合理的后续顺序不是再盲做 `v5`，而是按下面顺序推进：

1. **重做 `M4` 的 corruption protocol**
   目标不是再注入一个泛化的 `extreme_peak`，而是构造更贴近真实高层路由失效的错误：
   - 在 `reserve` 段强行丢掉 `reserve_soc`
   - 在 `carbon` 段故意路由到 cost-heavy expert
   - 在跨 regime 切换点注入 stale instruction / stale expert

2. **做 `text_best` 的 segment-level error attribution**
   重点回答：
   - 为什么 `v4` 在 `reserve` 段仍输给 `v2`
   - 为什么它与 regime-wise best fixed 上界之间还剩 `0.000914`
   - 剩余误差到底来自 instruction parse、expert mapping，还是 blending / persistence

3. **做更真实的 preference-shift protocol**
   当前四段硬切换还是太人工。下一轮应该增加：
   - 更长的稳定段
   - 渐变型偏好变化
   - 更接近 operator language 的 instruction 重写

4. **只有在上面三步完成后，再考虑 `v5`**
   到那时如果还要做下一版，也不该再回到“自由生成连续权重”，而是围绕：
   - expert persistence
   - switch hysteresis
   - regime transition guard
   - segment summary context
   这类更有证据支撑的方向推进。

## 新一轮 M4：transition-aware corruption

这轮没有继续沿用旧版 `extreme_peak` 周期注入，而是先做了一次显式 review，再把 `M4` 改成更贴近真实高层路由失效的协议。

### reviewed 决策

新增 review note：

- `refine-logs/auto-review/2026-03-20-m4-next-step.md`

核心结论是：

> 不再用泛化的极端权重去破坏系统，而是模拟更像真实高层路由失败的情形，例如 regime 切换后的短时错误 expert 选择、`reserve` 段丢掉 reserve 约束等。

### 这轮新增了什么

1. 在 `eval/run_preference_shift.py` 里新增了两类 corruption：
   - `wrong_expert`
   - `transition_wrong_expert`
2. 新增了 `--corruption_window`
   - 用来指定 regime 切换后错误策略持续多少步
3. 新增了一个分段误差归因脚本：
   - `eval/analyze_preference_shift_gap.py`
   - 输入：
     - `--results_dir`
     - `--summary_path`
     - `--target_tag`
     - `--compare_tags`
   - 输出：
     - 默认写到 `{results_dir}/{target_tag}_gap_analysis.json`
4. 对应单测已补进 `tests/test_preference_shift.py`

### GPU 使用

- 小测试：`GPU 3`
- 完整实验：`GPU 2`

### GPU 3 sanity

命令使用：

```bash
CUDA_VISIBLE_DEVICES=3 python eval/run_preference_shift.py \
  --schema /cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json \
  --checkpoint artifacts/checkpoints/gru_mse_best.pt \
  --norm_stats artifacts/norm_stats.npz \
  --forecast_config configs/forecast.yaml \
  --controller_config configs/controller.yaml \
  --output_dir /tmp/pref_shift_transition_gpu3_sanity \
  --tag sanity_text_best_transition_none_gpu3 \
  --router_type text_best \
  --forecast_mode learned \
  --device cuda:0 \
  --max_steps 120 \
  --corruption_mode transition_wrong_expert \
  --corruption_window 12 \
  --route_fallback none
```

以及对应的 `heuristic fallback` 版本。

sanity 结果确认了：

- `transition_wrong_expert` 协议工作正常
- `120` 步短程里共注入 `36` 次 corruption
- fallback 版本 `36` 次 corruption 全部触发 heuristic fallback
- 输出结构仍保持完整：
  - `*_kpis.json`
  - `*_segments.json`
  - `*_routes.json`
  - `*_actions.npy`

### GPU 2 完整实验

这轮完整对照跑的是：

- `text_best_transition24_none`
- `text_best_transition24_fallback`

设置：

- router：`text_best`
- corruption mode：`transition_wrong_expert`
- corruption window：`24`

结果：

| Run | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| clean text_best | 30.5693 | 468.3415 | 14.9948 | 858.7306 |
| text_best_transition24_none | 30.5744 | 468.3799 | 15.0067 | 859.5113 |
| text_best_transition24_fallback | 30.5785 | 468.4277 | 14.9948 | 858.9729 |

补充统计：

- 两组完整实验都注入了 `72` 次 corruption
- fallback 版本中 `72` 次 corruption 全部触发 heuristic fallback

### 这轮 M4 的解释

和旧版 `extreme_peak` 协议相比，这轮终于出现了更可解释的保护模式：

- **无 fallback**：
  - `peak` 相比 clean baseline 恶化了 `+0.0119`
  - `ramping` 恶化了 `+0.7807`
- **有 heuristic fallback**：
  - `peak` 回到了 clean baseline 水平
  - `ramping` 只恶化 `+0.2423`

代价是：

- `cost` 与 `carbon` 相对 clean baseline 略有增加

因此，这轮 `M4` 更准确的结论是：

> 新的 transition-aware corruption 协议已经把 fallback 的作用从“几乎看不见”变成了“可解释的目标保护 tradeoff”：它确实在高层切换失效下保护了 `peak / ramping`，但会付出一些 `cost / carbon` 代价。

这比旧版 `M4` 更强，因为它不再是“几乎没有差异”，而是出现了符合控制直觉的结构化差异。

但它仍然不是最终结论，因为：

- 差距还不算特别大
- fallback 当前更像“保护 peak / smoothness”的策略，而不是全指标都更优

因此当前最准确的状态是：

> `M4` 已从“证据偏弱”推进到“已有可解释正信号，但还需要更强协议继续验证”。

## `text_best` 的 segment-level 误差归因

这轮还新增了：

- `eval/analyze_preference_shift_gap.py`

并对当前 clean best run 做了归因，输出文件为：

- `/tmp/pref_shift_gpu2/text_router_v4_gap_analysis.json`

### 归因结论 1：`text_best` 相比 `v2` 的优势主要来自前三段

相对 `text_router_v2`，`text_best` 的平均优势是：

- `avg_score_delta_vs_target = 0.000242`

拆开看：

- `cost` 段：`text_best` 更好
- `carbon` 段：`text_best` 更好
- `peak` 段：`text_best` 略好
- `reserve` 段：`v2` 仍更好

也就是说：

> `text_best` 之所以整体优于 `v2`，并不是因为它把每一段都做对了，而是它在 `cost / carbon / peak` 三段累计赢得更多，而 `reserve` 仍然是当前最明显的局部短板。

### 归因结论 2：`text_best` 相比 `fixed_reserve` 的剩余差距并不均匀

相对 `fixed_reserve`，`text_best`：

- 在 `cost` 段更好
- 在 `peak` 段更好
- 在 `reserve` 段更好
- 但在 `carbon` 段更差

这说明当前 `text_best` 离 regime-wise best fixed 上界的剩余差距，不是“四段都差一点”，而更像：

> `reserve` 还没有完全稳定，`carbon` 段的 expert mapping / blending 也还存在结构性可改空间。

### 这对下一步 `v5` 的含义

这轮归因进一步说明：

- 不应该回到自由生成连续权重
- 下一版如果要做，应该围绕：
  - `reserve` 段保护
  - `carbon` 段 expert 选择
  - regime transition guard / persistence

也就是说，下一步不该是“更会读文本”，而应是：

> 更好地在 regime 切换和局部短板上做 expert persistence 与 switching control。
