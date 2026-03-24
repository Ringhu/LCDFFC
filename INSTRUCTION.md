# LCDFFC 当前执行面板

## 文件定位

本文件只回答两件事：现在先做什么，接下来按什么顺序做。仓库事实优先级不要在这里判断，直接看 `CLAUDE.md`。

## 当前阶段

当前仓库已经不是 GRU-only prototype。现在更需要把主路径和实验路径整理好，再把一个参考低层协议固定下来。

当前重点不是继续加更多模型名，也不是继续扩 router 版本。当前重点是把后续所有实验挂到同一套参考底座上。

## 当前优先级

### P0

1. 保持主阅读路径稳定：`README.md -> CLAUDE.md -> INSTRUCTION.md -> code/tests/configs`
2. 固定一个低层 reference stack 和统一 artifact
3. 验证 preference 到 KPI 的可控映射

### P1

4. 检查 routing 结论是否在多个 backbone 上方向一致
5. 把 router 的 bad JSON / fallback / 调用频率影响写成可验证结果

### P2

6. 再决定是否要做小规模 `SPO+` feasibility check

## 当前推荐动作

### 1. 固定一个 reference low-level protocol

先固定这些东西，不要继续横向扩展：

- 1 个主 controller，优先当前最强 QP 变体
- 1 个经典 learned backbone
- 1 个当前最强 foundation backbone
- 统一 schema、统一指标、统一输出目录结构

目标很简单：以后 router、preference、diagnosis 都挂在这套底座上。

### 2. 做 preference-to-KPI controllability

先回答这几个问题：

- `carbon` 权重增大后，carbon KPI 是否稳定下降
- `peak` 权重增大后，peak KPI 是否稳定改善
- `balanced / cost-saving / carbon-aware` 是否形成清楚的 trade-off

如果这一层不稳定，高层 routing 结论就不稳。

### 3. 做 cross-backbone routing stability

固定 event-driven 协议和同一个 router，在 2 到 3 个 frozen low-level stack 上重复跑。先看结论方向是否一致，再决定论文里能写多强。

## 当前不该优先做的事

- 继续堆更多 router 命名版本
- 继续堆更多弱 baseline controller
- 在没有统一协议前继续写 backbone 排名
- 把 prompt-only router 写成 production 模块
- 把 `SPO+`、RL、OOD 提前写成主交付

## 建议验证顺序

先跑轻量检查，再跑主 runner：

```bash
python tests/test_smoke.py
python tests/test_forecaster_factory.py
python tests/test_run_controller_modes.py
python tests/test_controller_baselines.py
python tests/test_preference_shift.py
```

如果环境里有 `cvxpy`，再补：

```bash
python tests/test_qp.py
```

主 runner：

```bash
python eval/run_rbc.py --schema citylearn_challenge_2023_phase_1 --output_dir reports/
python eval/run_controller.py --schema citylearn_challenge_2023_phase_1 --forecast_config configs/forecast.yaml --controller_config configs/controller.yaml --output_dir reports/ --tag forecast_qp
```

## 文档更新规则

- 入口命令变了，更新 `README.md`
- 稳定能力边界变了，更新 `CLAUDE.md`
- 当前任务顺序变了，更新 `INSTRUCTION.md`
- 单轮结果、round review、历史判断，留在 `docs/` 或 `refine-logs/`
