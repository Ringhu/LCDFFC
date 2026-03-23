# Pipeline 总结

**问题**：固定目标的 `forecast-control` 系统在运营者偏好变化时无法自然适配  
**最终方法主张**：使用语言条件化的高层路由器，在不重训低层 `forecast-control` 主循环的前提下，在线修改 `QP` 目标与约束  
**最终结论**：`REVISE`  
**日期**：2026-03-19

## 最终产物

- Proposal：`refine-logs/FINAL_PROPOSAL.md`
- Review summary：`refine-logs/REVIEW_SUMMARY.md`
- Experiment plan：`refine-logs/EXPERIMENT_PLAN.md`
- Experiment tracker：`refine-logs/EXPERIMENT_TRACKER.md`

## 贡献快照

- **主贡献**：
  面向 `forecast-then-control` 的语言条件化动态目标路由
- **可选支撑贡献**：
  用于安全路由的 deterministic fallback
- **明确拒绝的复杂度**：
  不把 DFL、uncertainty、第二 benchmark 迁移一起做成并列主贡献

## 必须证明的主张

- 同一个低层控制器能在偏好变化时在线适配，而不需要重训
- 语言条件化路由相比更简单替代方案具有足够的价值或表达优势

## 最先启动的 3 个实验

1. 构造 `preference-shift` 评测协议与评分方法
2. 复现各类固定权重 baseline
3. 比较 heuristic router 与 language-conditioned router

## 主要风险

- **语言可能并非必要**：
  非语言结构化路由器可能就能达到同样效果
- **偏好切换场景可能过于人工**：
  reviewer 可能不认可
- **低层控制污染高层结论**：
  如果 base loop 不够稳，会模糊主张

## 下一步

- 进入 `/run-experiment`
