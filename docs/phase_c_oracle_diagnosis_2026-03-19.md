# Phase C Oracle Diagnosis (2026-03-19)

## Purpose

固化 `Phase C` 当前已经验证过的诊断结论，避免后续工作再次依赖过时聊天记录。

## What Was Checked

1. 修正 `QPController` 的共享动作建模，使其与 CityLearn `electrical_storage` 的归一化动作语义一致。
2. 修正 `eval/run_controller.py` 中的当前 SOC 读取索引。
3. 修正 rollout 启动方式，使控制从 episode 首步即可介入，而不是等待 24 步 warmup。
4. 核对 `artifacts/forecast_data.npz` 中 `oracle_data` 的 `price/load/solar` 与零动作 CityLearn rollout 的真实时序是否一致。
5. 将求解器顺序改为 `CLARABEL -> OSQP`，避免 `charge/discharge` 分解下的退化充放电解污染诊断。
6. 将 cost/carbon 目标改为基于 `max(net_load, 0)` 的 import proxy，而不是直接最小化原始 `net_load`。

## Verified Facts

- `oracle_data` 与零动作 rollout 的 `price/load/solar` 对齐是正确的，不存在简单的 `t` 与 `t+1` 索引错位。
- 旧结论“`learned / myopic / oracle` 都是零动作”已经失效，那是由 rollout warmup 和当前 SOC 读取问题共同造成的假诊断。
- 修正后，`learned forecast + QP` 已通过当前阶段 `RBC` 验收。
- `oracle` 结果仍显著劣于 `learned` 和 `RBC`，因此 `oracle` 现在不能被解释为理论上界。

## Fixed Reference Results

本地缓存 schema:

`/cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json`

参考结果：

- `RBC`: cost `33.0114`, carbon `499.6858`, peak `16.4417`
- `learned_qp_fix4`: cost `32.4935`, carbon `496.2018`, peak `14.9950`
- `myopic_qp_fix4`: cost `33.0120`, carbon `499.6928`, peak `16.4417`
- `oracle_qp_fix4`: cost `33.6512`, carbon `510.9105`, peak `17.1023`

动作统计：

- `learned_qp_fix4`: min `-0.2129`, max `0.2504`, mean_abs `0.0728`
- `myopic_qp_fix4`: min `0.0000`, max `0.0005`, mean_abs `0.000003`
- `oracle_qp_fix4`: min `-0.9155`, max `0.3153`, mean_abs `0.0808`

## Current Interpretation

当前更合理的解释不是“oracle forecast 取错了行”，而是：

1. `oracle` 路径在时序上已经对齐。
2. 求解器退化问题已做一轮抑制。
3. 即便如此，精确未来 `price/load/solar` 仍会驱动当前 QP 产生比 `learned` 更激进的动作。

因此，当前真正待解释的问题是：

- 为什么当前控制目标在 oracle target 下会系统性过激；
- 这是否来自目标函数仍缺少某种重要代理项；
- 或者 forecast target 只包含 `price/load/solar` 仍不足以支撑 oracle 作为合理上界。

## Next Step

下一步优先做下面两件事，而不是直接进入 uncertainty：

1. 比较 `oracle_qp_fix4` 与 `learned_qp_fix4` 在高动作时段的 forecast 序列，定位 oracle 过激动作具体由哪些 horizon pattern 触发。
2. 检查是否需要把控制目标中的 peak/import proxy 继续改成更贴近真实 KPI 的分段代理，或收紧 terminal / reserve 约束。
