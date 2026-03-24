# Phase C Oracle Diagnosis（dated diagnosis, 2026-03-19）

这个文件只保留 2026-03-19 当天的一次局部诊断记录，不再承担当前仓库事实源角色。

当前主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

如果文档和代码不一致，以 `code + tests` 为准。

## 这份 dated diagnosis 还能回答什么

它现在只适合回答：

- 2026-03-19 当天排查过哪些 `oracle / learned / myopic` 相关问题
- 当时为什么会记录一组局部 KPI 和动作统计
- 当时对 oracle 诊断路径的解释是什么

## 不要再用它判断什么

不要再用这个文件判断：

- 当前 `oracle` 路径的最终结论
- 当前是否已经稳定通过某个验收线
- 当前 controller 或 runner 的最终正确性
- 当前论文里该如何使用这些诊断结果

这些问题现在请直接看：

- `eval/run_controller.py`
- `controllers/qp_controller.py`
- `tests/test_run_controller_modes.py`
- `tests/test_qp.py`
- `README.md`
- `CLAUDE.md`

## 保留它的原因

保留它，是为了记录一轮具体诊断做过什么检查、当时观察到了什么现象。它现在只算 dated diagnosis，不算当前工程契约。
