# Auto Review Note: Real LLM Router（2026-03-20）

## 当前问题

当前仓库里真正可跑的所谓“文本路由”其实仍是规则/模板系统，`llm_router/router.py` 的 `LLMRouter.route()` 还没有实现。

因此，如果论文或说明文档继续把当前系统描述成真实 `LLM` 路由，会明显站不住。

## 候选做法

### 方案 A：直接上复杂 agent

优点：
- 更符合“LLM + agent”叙事

缺点：
- 工程量过大
- 容易把 tool use / memory / planning 全部缠进来
- 当前阶段无法和已有 heuristic / text_v4 做干净对比

### 方案 B：实现最小 prompt-only LLM router

优点：
- 能真正让 `LLMRouter.route()` 从 `NotImplemented` 变成可运行代码
- 能和现有 `text_v4 / heuristic / fixed` 做一对一对比
- 仍然符合当前高层路由定位：输出结构化 `weights / constraints`

缺点：
- 还不是完整 agent 系统
- 小模型性能可能不如手写规则

## Review 决策

选择 **方案 B**。

## 具体设计

- 后端优先使用本地缓存的小型 instruct 模型，避免依赖外部 API。
- 第一版使用 `transformers` 推理，先支持：
  - prompt 构建
  - 文本生成
  - JSON 解析
  - schema 校验
  - fallback 到默认输出
- 调用频率不采用 `per_step` 暴力调用，而采用 `regime/event change` 触发，再在 segment 内持有上一次输出。

## 为什么这样设计合理

- 它真正回答的是“仓库里有没有一个真实的 LLM router”。
- 即使性能未必超过 `text_v4`，只要能稳定跑通并给出可复现结果，就足以把文档口径从“未实现”推进到“已实现最小 prompt-only 版本”。
- 先做 prompt-only，有利于后续判断：
  - 是 LLM 本身值得继续投入
  - 还是结构化 rule router 已经足够

## 对比实验

在 event-driven protocol 下比较：

- `fixed` 系列
- `heuristic`
- `text_best`
- `llm_prompt_v1`

如果 runtime 可承受，则记录：
- 平均每次路由耗时
- 总 LLM 调用次数
- JSON 解析失败次数
- fallback 次数

## 成功标准

最低成功标准不是“LLM 一定赢”，而是：

1. `LLMRouter.route()` 真正可运行
2. 能稳定输出合法 JSON
3. 能在完整 episode 上形成可复现结果
4. 能回答“真实 LLM router 相比 rule router 到底值不值得继续做”
