# Round 7 结果：foundation forecast 强但加上 QP 不完全兑现，究竟是不是 QP 的问题？（2026-03-21）

## 1. 本轮要回答的问题

本轮直接回应用户的新质疑：

> `Moirai2 / TimesFM 2.5` 的 zero-shot forecasting 已经很强，但接上当前 `QP` 控制器后，下游收益没有完全按 forecasting 排名兑现。这是不是 `QP` 本身的问题？

对应的 reviewed design 是：

- `refine-logs/auto-review/2026-03-21-round7-controller-diagnosis-review.md`

## 2. 本轮先做了什么排错

在正式跑 controller baseline 之前，本轮先发现并确认了一个关键事实：

- `controllers/qp_controller.py` 支持 `carbon_intensity`
- 但当前主链路在调用 `ctrl.act(...)` 时通常没有真正传入未来 `carbon` 预测

因此，本轮不能只比较不同 controller family，还必须额外比较：

- 当前实际使用的 `qp_current`
- 修正输入后的 `qp_carbon`

另外，本轮第一次实现 `run_foundation_controller_compare.py` 时，还发现了一个实验脚本偏差：

- history 初始被错误地预填了 `512` 个重复首帧
- 这会把 `qp_current` 错误地退化为接近 `zero_action`

该问题已在 full run 前修正，并用单点复现实验证明：

- 修正后，`moirai2 + qp_current` 已精确复现 round6 结果

因此，下面的 full result 都来自修正后的脚本，不是错误版本的结果。

## 3. 本轮比较了哪些 controller

固定：

- foundation backbone：`moirai2`、`timesfm2.5`
- 场景：`citylearn_challenge_2023_phase_1`
- horizon：`24`
- context length：`512`
- 统一权重：
  - `cost 0.15`
  - `carbon 0.10`
  - `peak 0.65`
  - `smooth 0.10`
- 统一约束：`reserve_soc = 0.2`

比较的 controller family：

1. `zero_action`
2. `qp_current`
3. `qp_carbon`
4. `forecast_heuristic`
5. `action_grid`

## 4. Full result

### 4.1 Moirai2

| Controller | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| zero_action | 31.5444 | 477.9883 | 16.4417 | 856.3507 |
| qp_current | 29.2140 | 447.0601 | 15.1225 | 791.7540 |
| qp_carbon | 29.1737 | 446.4288 | 15.1225 | 793.4768 |
| forecast_heuristic | 35.3278 | 543.1013 | 17.7270 | 1123.0482 |
| action_grid | 31.1508 | 478.3257 | 16.3541 | 877.9948 |

相对 `zero_action` 的归一化平均比分（越低越好）：

- `qp_carbon`: `0.926291`
- `qp_current`: `0.926437`
- `action_grid`: `1.002043`
- `zero_action`: `1.000000`
- `forecast_heuristic`: `1.161442`

### 4.2 TimesFM 2.5

| Controller | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| zero_action | 31.5444 | 477.9883 | 16.4417 | 856.3507 |
| qp_current | 29.4396 | 449.6589 | 15.3452 | 809.6941 |
| qp_carbon | 29.3588 | 447.7061 | 15.3442 | 805.6593 |
| forecast_heuristic | 34.9586 | 536.0734 | 16.4417 | 1099.2815 |
| action_grid | 31.1885 | 478.5432 | 16.3541 | 868.1755 |

相对 `zero_action` 的归一化平均比分（越低越好）：

- `qp_carbon`: `0.935353`
- `qp_current`: `0.938208`
- `action_grid`: `0.999589`
- `zero_action`: `1.000000`
- `forecast_heuristic`: `1.128359`

## 5. 关键对比

### 5.1 `qp_carbon` 对 `qp_current` 的真实增益

`moirai2` 下：

- `cost`: `-0.0403`
- `carbon`: `-0.6313`
- `peak`: 基本持平
- `ramping`: `+1.7228`

`timesfm2.5` 下：

- `cost`: `-0.0808`
- `carbon`: `-1.9528`
- `peak`: `-0.0010`
- `ramping`: `-4.0348`

结论：

- 缺少 `carbon` 预测输入确实是一个真实问题
- 但它带来的改进量级是“稳定但不巨大”的修正，不足以支持“QP family 本身有根本问题”

### 5.2 非 QP controller 有没有打败 QP？

没有。

在两条 backbone 上都成立：

- `forecast_heuristic` 明显最差
- `action_grid` 虽然比 heuristic 好很多，但仍然远弱于 `qp_current / qp_carbon`
- `action_grid` 甚至只是在 `peak` 上比 `zero_action` 略好，整体并没有形成可靠收益

这说明：

- 当前 foundation forecast 的收益并不是被 “QP family 压没了”
- 至少在本轮测试的 controller family 里，`QP` 仍是最有效的控制方法

## 6. 本轮最重要的结论

### 6.1 直接回答“是不是 QP 的问题”

**不是主要问题。**

更准确地说：

- 当前 `QP` 的实现里确实有一个输入定义问题：未来 `carbon` 信号缺失
- 修正后，`qp_carbon` 在两条 backbone 上都稳定优于 `qp_current`
- 但即使把这个问题修正掉，`QP` 依然明显优于本轮测试的非 QP controller family

因此，当前最合理的结论不是：

- `QP` 不行

而是：

- `QP` 仍然是当前最好的一类 controller
- 真正的问题更像是：forecast quality、controller objective、以及多 KPI trade-off 之间本来就不是单调映射

### 6.2 为什么 zero-shot forecast 很强，但 downstream 不一定按同样顺序兑现

本轮结果支持下面这个解释：

1. zero-shot forecasting 强，只说明点预测或 rolling metric 强
2. 但 control 要兑现这些收益，还取决于：
   - 控制器目标是什么
   - 控制器看见哪些未来信号
   - 控制器为了 `peak / reserve / smoothness` 愿意牺牲多少 `cost / carbon`
3. 所以 forecasting 排名不会一比一映射成 control 排名

在当前项目里，`Granite + QP` 与 `Moirai2 + QP` 的 trade-off 差异，其实更像是：

- 不同 backbone 把 controller 推向了不同的 KPI 平衡点

而不是：

- 某个 backbone 强，但被 QP 毁掉了

## 7. 对后续研究的影响

本轮可以把 controller baseline round 的主结论先固定下来：

1. `QP` 不是当前 low-level 的主要短板
2. `carbon` 输入缺失是一个应该修正的真实问题
3. 单纯换成 heuristic / action-grid，并不能更好地兑现 foundation forecast
4. 后续更值得推进的方向不是继续堆更多弱 controller，而是：
   - 把 `qp_carbon` 这条 corrected path 固定下来
   - 继续研究 objective trade-off
   - 分析为什么 `Granite` 更强 `peak`，而 `Moirai2 / TimesFM` 更强 `cost / carbon`

## 8. 本轮最终判断

如果只回答用户这句话：

> “foundation model zero-shot 很强，但加上 QP 不行，是不是 QP 的问题？”

那么本轮最准确的回答是：

> 不是主要问题。当前 `QP` 有一个可修正的 `carbon` 信号缺失问题，但修正后它仍然明显优于本轮测试的非 QP controller。foundation forecast 的收益没有完全兑现，主要不是因为 `QP family` 错了，而是因为 forecasting 优势到控制 KPI 的映射本来就受 objective 和 trade-off 约束。
