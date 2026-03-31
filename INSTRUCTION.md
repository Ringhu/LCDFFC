# LCDFFC 当前执行面板

## 文件定位

本文件只回答两件事：现在先做什么，接下来按什么顺序做。仓库事实优先级不要在这里判断，直接看 `CLAUDE.md`。

## 当前阶段

当前研究线是 CAVS（Controller-Aware Validation Score）。核心论点：平均预测误差（MSE/MAE）不是下游控制质量的好代理指标，CAVS 能选出比 MSE/MAE 更好的预测模型。

旧的 CSFT/routing 工作已归档到 `refine-logs/archive/` 和 `docs/archive/`。

## 当前优先级

### P0: Lock stack (E01)

验证修正后的 pipeline 能复现基线结果。

```bash
python eval/run_cavs_validation.py --config configs/cavs.yaml --dry_run
```

- 模型：myopic, oracle, GRU, Moirai2, TimesFM2.5
- 场景：phase_1
- 目标：KPI 在修正后的 stack 上可复现
- 输出：`reports/cavs/E01/`

### P1: Misalignment evidence (E02-E05)

训练多 backbone、跑 FM sweep、建排行榜、算 rank correlation。

- E02: GRU, TSMixer; 5 scenarios; 3 seeds → checkpoints + forecast/KPI tables
- E03: Moirai2, TimesFM2.5; 5 scenarios (zero-shot)
- E04: 合并 E02+E03 建 leaderboard
- E05: Spearman/Kendall rank correlation（MSE ranking vs KPI ranking）
- 决策门：如果 rank correlation > 0.85，核心论点弱

### P2: Perturbation sensitivity (E06-E08)

- E06: Oracle variants 对比（3 scenarios）
- E07: Channel-horizon perturbation → sensitivity heatmap (24×3)
- E08: Event-critical error analysis

```bash
python eval/perturbation_sensitivity.py \
  --schema citylearn_challenge_2023_phase_1 \
  --oracle_data artifacts/forecast_data.npz \
  --output_dir reports/cavs/sensitivity
```

### P3: CAVS validation (E09)

核心实验。用 E04 的所有模型 + E07 的 sensitivity map，比较 CAVS vs MSE vs MAE 选模型的效果。

- 决策门：CAVS 选出的模型在 3+ scenarios 上至少 2 个 KPI 优于 MSE 选出的模型

### P4: External transfer (E10, NICE-TO-HAVE)

在 CityLearn 2022 上验证 misalignment 和 CAVS 优势是否保持。

## 当前不该优先做的事

- 继续堆 router 版本
- 把 CSFT 重新拿出来做主贡献
- 在没有 E01-E05 结果前写论文
- 把 LLM routing 写成主要贡献

## 验证顺序

先跑轻量检查：

```bash
python tests/test_smoke.py
python tests/test_forecaster_factory.py
python tests/test_run_controller_modes.py
```

主 CAVS runner：

```bash
python eval/run_cavs_validation.py --config configs/cavs.yaml
```

## 文档更新规则

- 入口命令变了，更新 `README.md`
- 稳定能力边界变了，更新 `CLAUDE.md`
- 当前任务顺序变了，更新 `INSTRUCTION.md`
- 单轮结果、round review、历史判断，留在 `docs/` 或 `refine-logs/`
