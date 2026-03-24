# AGENTS.md

## 文件定位

本文件不再承担当前仓库事实源角色。

当前主阅读路径是：

1. `README.md`：项目概览、运行入口、目录导航
2. `CLAUDE.md`：稳定工程约定、能力边界、事实优先级
3. `INSTRUCTION.md`：当前执行顺序和下一步任务
4. `code/`、`tests/`、`configs/`

如果文档和代码不一致，以代码与测试为准。完整优先级见 `CLAUDE.md`。

## 还保留在这里的内容

本文件现在只保留少量长期协作规则：

- 文档变了要及时和代码同步
- 文档默认写中文，直接写事实
- `implemented / experimental / planned` 要分开写
- 不要把最小 prompt-only router 写成 production 系统
- 不要把 `SPO+`、RL、OOD 写成已经完成

## 当前不该再从这里获取的内容

下面这些内容不要再以本文件为准：

- 当前 Sprint 状态
- 当前主训练脚本
- `LLMRouter.route()` 是否实现
- backbone 排名或实验结论
- 是否已经通过某轮验收

这些内容现在分别由下面几类来源负责：

- 当前实现事实：`code/` + `tests/`
- 稳定工程说明：`CLAUDE.md`
- 对外入口：`README.md`
- 当前执行顺序：`INSTRUCTION.md`
- 历史材料：`docs/`、`refine-logs/`、dated review docs

## 长期有效的协作规则

### 文档规则

- 代码行为变了，就同步改文档。
- 不要把单轮实验结果写成长期事实。
- 不要把旧规格文档当成当前实现说明。
- 需要写当前状态时，优先更新 `README.md`、`CLAUDE.md`、`INSTRUCTION.md`，不要回写到历史文档里。

### 仓库卫生规则

公开仓库不应提交这些本地产物：

- `artifacts/`
- `reports/`
- `.claude/`
- `__pycache__/`
- 其他本地缓存、密钥、私有对话材料

### 提交前检查

提交前至少确认：

1. 入口脚本和文档一致
2. 新增能力被标成正确层级
3. 历史材料没有重新冒充当前事实
4. 公开仓库不会带上本地产物
