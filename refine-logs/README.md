# refine-logs/

当前研究线是 CAVS（Controller-Aware Validation Score）。skill pipeline 文件在这个目录的根层级。

`archive/` 包含旧的 CSFT/routing 追踪文件（EXPERIMENT_PLAN, EXPERIMENT_TRACKER, FINAL_PROPOSAL 等的旧版本）。

## Skill pipeline 文件

| 文件 | 用途 | 读取方 |
|------|------|--------|
| `FINAL_PROPOSAL.md` | CAVS 研究提案 | `/experiment-plan` |
| `REVIEW_SUMMARY.md` | GPT-5.4 review 总结 | `/experiment-plan` |
| `REFINEMENT_REPORT.md` | 细化报告 | — |
| `REFINE_STATE.json` | 状态检查点 | `/research-refine` |
| `score-history.md` | 分数演变 | — |
| `EXPERIMENT_PLAN.md` | CAVS 实验计划 | `/experiment-bridge` |
| `EXPERIMENT_TRACKER.md` | 实验追踪表 | `/experiment-bridge` |

## 什么时候看这里

- 你想追某一轮实验结果
- 你想看某一轮 review 为什么改了方向
- 你想找 paper-facing summary 或 round notes

## 不要用这里判断什么

不要用这个目录判断当前主训练入口、评估协议、能力边界。这些问题看 `README.md` → `CLAUDE.md` → `INSTRUCTION.md`。
