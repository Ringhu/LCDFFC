# 研究评审报告（2026-03-19）

## 评审范围

本文档记录了针对当前 LCDFFC 项目所做的一次完整本地研究评审与方案收缩流程。

## 本次评审看了什么

### 1. 项目当前真实状态

- 当前已经跑通的主闭环：
  `GRU` 预测器 + `QP` 控制器 + `CityLearn` 评估
- 当前仓库中明确规划但尚未闭环的方向：
  uncertainty、decision-focused learning、LLM router
- 当前已验证的关键结果：
  在本地验证设置下，`learned forecast + QP` 已优于 `RBC`

### 2. 项目叙事文档

- `AGENTS.md`
- `README.md`
- `INSTRUCTION.md`
- `CLAUDE.md`
- `chat.md`
- `docs/` 下相关说明文档

### 3. 相关工作参照系

本次评审还对照了以下几类最相关的工作方向：

- CityLearn / 建筑能源控制 benchmark 工作
- 决策导向预测与 decision-focused learning
- LLM 辅助控制 / 优化 / 高层目标路由
- 近期 building-energy 与 LLM 相关论文

用于 novelty 判断的代表性参考包括：

- CityLearn 环境概览：https://pypi.org/project/citylearn/
- CityLearn challenge 获胜优化式策略：https://jinming.tech/papers/2023-aaai-citylearn-winning-solution.html
- 类 CityLearn 场景下的层次化 RL-MPC：https://doi.org/10.1016/j.enbuild.2025.116879
- 基于 LLM 的可解释建筑控制：https://dblp.org/rec/journals/corr/abs-2402-09584
- 面向能量管理的 decision-focused 鲁棒优化：https://doi.org/10.1016/j.apenergy.2025.127343
- 面向光伏-储能调度的 decision-focused 方法：https://doi.org/10.1016/j.est.2026.121152

## 分轮次评审摘要

### Round 0：对当前 broad idea 的初判

当前项目把多条看起来都合理的研究线放在了一起：

- `forecast + QP`
- uncertainty-aware control
- decision-focused training
- LLM preference routing
- 可选的第二 benchmark 迁移

判断：

- 作为研究路线图，这是合理的
- 作为单篇论文的 thesis，这还不够集中

### Round 1：批判性评审

主要批评点如下：

1. 当前还没有一个唯一的主贡献
2. 当前已经实现的部分本身 novelty 不足
3. LLM 的角色方向是对的，但还没有收缩成一个足够锋利的论文主张
4. 当前评估还不能充分隔离“这篇论文真正的贡献是什么”

结论：

`REVISE`

### Round 1：方案收缩

最终把论文主线收缩为：

> 面向偏好变化场景的、语言条件化的 forecast-then-control 高层目标路由

这个版本保留了原来的问题本身，但避免了贡献发散。

## 最终共识

### 1. 当前工程成熟度够不够？

够，至少已经达到了“可以支撑一篇认真方法论文”的程度。

仓库现在已经不再只是脚手架，而是具备：

- 可运行的数据提取路径
- 可运行的预测模型
- 可运行的优化控制器
- 可运行的端到端评估链路
- 一个已经通过本地验证的、优于 `RBC` 的主闭环结果

### 2. 当前论文想法成熟了吗？

还没有，如果你继续把整条路线图塞进同一篇论文里。

当前 broad idea 还是太宽了，更像“多个论文方向并行”，不像“一个顶会论文主张”。

### 3. 当前方案可行吗？

可行。

而且收缩后的版本尤其可行，因为它是直接建立在当前已经跑通并验证过的低层 `forecast + QP` 主循环上，而不是推翻重来。

### 4. 当前方案足够 novel 吗？

这里需要分两层回答：

1. **只看当前已实现系统本身**：
   不够。  
   单独的 `GRU + QP + CityLearn` 更像扎实工程结果，不够支撑强 CCF-A novelty。

2. **看收缩后的 refined proposal**：
   有希望，但前提是你必须把论文明确聚焦到：
   **“语言条件化的在线目标适配”**
   并且证明语言层不是装饰件，而是确实带来了固定权重或简单路由做不到的能力。

## 结果—主张矩阵

| 实验结果 | 允许主张 |
|---|---|
| 语言路由在偏好切换场景中明显优于固定权重和简单路由 | 强论文主张成立 |
| 语言路由与数值偏好向量路由打平 | 主张必须降级为“偏好条件化路由”，不能再强调语言必要性 |
| 语言路由输给简单 heuristic router | LLM novelty 不成立 |
| 固定低层闭环保持稳定，路由层额外带来适应性收益 | 这是最好的论文形态 |
| 路由层破坏了鲁棒性或可行性 | LLM 部分应退回 future work 或缩弱主张 |

## 优先级最高的 TODO

1. 把当前已验证的低层 `forecast + QP` 主循环冻结为基础平台
2. 设计真实且可信的 `preference-shift` 评测协议
3. 先实现一个最小 heuristic router
4. 再实现一个最小 language-conditioned router
5. 与固定权重、非语言结构化路由做正面对照
6. 只有在 novelty 隔离成功后，再决定 uncertainty 或 DFL 是否应该进入同一篇论文

## 粗略的计算与执行判断

- 当前 base loop 已经能稳定本地运行
- 如果低层主循环保持冻结，router 层实验的成本不会太高
- 当前最大的风险不是算力，而是：
  **评测协议设计得不够干净，导致主张无法被 reviewer 接受**

## 建议的论文结构

1. Introduction
   - 外生时序驱动控制
   - 固定目标控制器的局限
   - 语言条件化目标适配
2. Problem Setting
   - CityLearn 多目标电池控制
   - preference-shift 场景
3. Method
   - 固定低层 `forecast + control`
   - 高层语言条件路由器
   - 结构化 fallback
4. Experiments
   - 主结果
   - novelty isolation
   - simplicity / necessity check
   - robustness
5. Discussion
   - 语言什么时候必要
   - 简单路由什么时候已经够用

## 最终底线判断

- **当前 idea 成熟度**：中等
- **当前工程成熟度**：中高
- **当前可行性**：高
- **当前 novelty**：按已实现内容看不够；按收缩后的论文主线看，有潜力
- **最合理的下一步**：执行 refined experiment plan，而不是继续扩架构
