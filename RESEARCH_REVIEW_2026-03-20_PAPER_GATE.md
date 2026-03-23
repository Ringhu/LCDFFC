# 研究阶段 Gate Review（2026-03-20）

## 评审问题

本次评审只回答一个核心问题：

> 按当前工程和实验进度，是否已经足够开始写 paper？

这里需要明确区分两种“paper”：

1. **按项目最初 broad idea 写的论文**
   - 时间序列分析
   - 决策
   - LLM agent
   - 可迁移到更多环境的方法
2. **按当前已经收缩后的 focused thesis 写的论文**
   - CityLearn 上的语言条件化高层目标路由
   - 固定低层 `forecast + QP`
   - preference-shift 适配
   - 误差分析与安全性分析

如果不把这两层区分开，结论会一直摇摆。

## 本次评审看了什么

- `chat.md`
- `docs/project_progress_explainer_2026-03-20.md`
- `refine-logs/PAPER_FACING_SUMMARY_2026-03-20.md`
- `RESEARCH_REVIEW_2026-03-19.md`
- `refine-logs/EXPERIMENT_RESULTS.md`
- `refine-logs/EXPERIMENT_TRACKER.md`

## 结论

### 结论 1：按最初 broad idea 来看，当前还不够直接写成最终投稿版

如果论文还想保留最初对外的“大故事”：

- 时序分析 + 决策 + LLM agent
- 方法具有更强泛化性
- 未来可迁移到 Grid2Op 等第二 benchmark

那么当前进度还不够。

原因很直接：

1. 当前主实证几乎全部建立在 `CityLearn preference-shift` 协议上
2. 还没有 `OOD / transfer` 证据
3. 还没有第二环境验证
4. 当前真正落地的 LLM 角色是高层偏好路由，而不是更宽泛的“LLM agent”

所以，如果论文标题和摘要还保留 broad idea 级别的野心，当前证据是不够的。

### 结论 2：按当前已经收缩后的 focused thesis 来看，已经足够开始写 paper

如果论文主张严格收缩为：

> 在当前 CityLearn preference-shift 协议下，语言条件化高层路由优于单一固定控制器，并具备可解释的误差分析与安全性分析。

那么当前已经足够开始写 paper。

原因是：

1. 当前 best method 已经稳定为 `text_v4`
2. `text_v4` 优于最佳单一固定控制器 `fixed_reserve`
3. 误差来源已经拆到具体 regime：`reserve` 第一、`carbon` 第二
4. fallback 的安全性作用已经被明确证明
5. `v5 / v6 / v7` 的 reviewed 负结果已经说明当前 best 基本稳定，不是在随机飘

这意味着：

- 你已经有主结果
- 有误差分析
- 有安全性分析
- 有负结果支持“为什么当前 best 是 best”

从一篇 focused method paper 的角度，这是可以开始写的。

### 结论 3：当前状态最准确的判断不是“能不能写”，而是“写到什么边界”

当前项目的问题不是完全没到写作阶段，而是：

> 你已经有一篇可以开始写的 focused paper，但还没有一篇可以直接放心投稿的 broad paper。

换句话说：

- **写作起点已经够了**
- **最终投稿证据还差半步**

## 当前已经成立的内容

下面这些内容，我认为已经可以稳定写进论文主线：

1. `text_v4` 是当前 best
2. `text_v4` 优于最佳单一固定控制器
3. `reserve` 是第一主敏感点，`carbon` 是第二主敏感点
4. fallback 在失效协议下能形成可解释保护
5. 局部 reserve release guard 调优进入饱和区，后续 `v5 / v6 / v7` 没能超过 `v4`

## 当前仍不应写满的内容

下面这些内容，当前还不应该写成强主张：

1. 不能写成“优于 regime-wise best fixed upper bound”
2. 不能写成“语言层已经证明优于所有结构化替代”
3. 不能写成“方法已经具备充分跨分布泛化性”
4. 不能写成“这是一个已经跨环境成立的通用方法”

## 当前最大的真实短板

我认为当前最关键的短板不是再去调一个更复杂的 router，而是：

1. **证据覆盖范围偏窄**
   - 主要集中在当前 protocol
2. **主结果优势存在，但幅度不大**
   - 因此需要更谨慎的 narrative
3. **缺少最后一个投稿 gate**
   - 要么补最小 OOD / transfer
   - 要么经过一轮更高层 review 后接受“当前只写 focused version”

## Gate 决策

### Gate A：能不能开始写？

**YES**

可以开始写。

### Gate B：能不能直接按现在的证据作为最终投稿版？

**NO**

还不建议直接把当前结果当成最终投稿版收尾。

### Gate C：最合理的下一步是什么？

**先写 focused paper，再决定是否补最小 OOD / transfer。**

更具体地说，推荐顺序是：

1. 用当前结果进入 `paper-plan`
2. 再进入 `paper-write`
3. 在写作过程中保留一个 decision point：
   - 如果 review 认为当前证据已经够支撑 focused paper，就继续成稿
   - 如果 review 认为泛化证据不足，就补一轮最小 OOD / transfer

## 最终一句话判断

> 你现在的进度已经足够开始写一篇 focused paper，但还不够直接写成你最初 broad idea 那种终局版本。当前最合理的动作不是继续局部调 router，而是先把 paper 写起来，再由下一轮高层 review 决定是否补最小泛化实验。
