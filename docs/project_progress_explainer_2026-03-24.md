# LCDFFC 当前研究进度与主线判断（2026-03-24）

## 1. 一句话结论

当前项目**没有明显偏离主线研究**，但已经从最初的单一路径原型扩展成一个多路径研究平台。当前最大的矛盾不是“方向跑偏”，而是**低层结论、高层 thesis、实验扩展和文档叙述还没有完全收敛到同一条主线上**。

更准确的阶段标签仍然是：

> **post-prototype, pre-consolidation research platform**

---

## 2. 当前研究进度到了哪一步

### 2.1 低层主闭环已经不再是早期脚手架

当前仓库已经具备一条清晰、可运行、可诊断的主路径：

```text
CityLearn observation
  -> forecasting backbone or diagnostic forecast mode
  -> controller
  -> CityLearn env
```

对应实现主要在：

- `models/factory.py:12`
- `eval/run_controller.py:155`
- `controllers/qp_controller.py:25`

其中 `run_controller` 已经明确支持三种诊断模式：

- `learned`
- `oracle`
- `myopic`

见：

- `eval/run_controller.py:165`
- `eval/run_controller.py:345`

这说明项目已经不再是“只能跑 learned forecast + QP 的单一路径试验”。

### 2.2 forecasting 已经从 GRU-only 扩展成多 backbone 平台

当前工厂已支持至少以下 forecasting backbone：

- `gru`
- `tsmixer`
- `patchtst`
- `transformer`
- `granite_patchtst`

见：

- `models/factory.py:12`
- `tests/test_forecaster_factory.py:13`

这说明当前研究问题已经从“能不能把 GRU 跑起来”，转向“不同 forecast backbone 对 control 和高层 routing 结论的影响是什么”。

### 2.3 controller 侧已经形成较成熟主干

当前最成熟的低层组件之一仍然是 QP controller。它已经具备：

- reserve / max charge 等约束
- shared action across buildings
- solver fallback
- 较完整的测试边界

见：

- `controllers/qp_controller.py:87`
- `controllers/qp_controller.py:230`
- `tests/test_qp.py:1`

这意味着 low-level control 已经足够支持系统性诊断，而不是待实现模块。

### 2.4 高层 routing 已进入实验可运行阶段

`LLMRouter.route()` 现在不能再写成“未实现”。它已经是一个**最小 prompt-only router**，具备：

- prompt context 构造
- transformers lazy load
- JSON parse
- bad JSON fallback 到默认策略

见：

- `llm_router/router.py:44`
- `llm_router/router.py:68`
- `llm_router/router.py:79`
- `llm_router/router.py:104`
- `tests/test_llm_router.py:23`

但它仍然只能被写成：

- 实验性高层策略接口
- 最小 prompt-only router

而不能被写成：

- production-ready router
- deterministic-fallback-complete system

### 2.5 当前已经是研究平台而非单实验仓库

当前代码已经扩展到以下实验方向：

- preference shift / event-driven routing：`eval/run_preference_shift.py`
- foundation forecast + control：`eval/run_foundation_control.py`
- controller family compare：`eval/run_foundation_controller_compare.py`
- heuristic / action-grid baselines：`controllers/baseline_controllers.py`

因此，当前项目状态不是“还在起步”，而是：

> **低层闭环已成型，实验面已扩宽，但还没有把所有扩展收敛成一条最强、最可投稿、最可复验的主证据链。**

---

## 3. 是否偏离了主线研究

## 3.1 结论

更准确的判断不是简单的“偏离 / 没偏离”二选一，而是：

- **没有偏离 broad idea**
- **发生了 thesis 收缩**
- **发生了必要的工程与实验再扩展**

### 3.2 没有偏离的部分

如果 broad main idea 是：

1. 在 CityLearn 上做 forecast-then-control
2. 往 decision-focused / preference-aware control 方向推进
3. 把 LLM 放到高层做偏好 / 约束 / 模式路由

那么这条主线并没有被放弃。当前代码结构仍然沿着这条路线展开。

### 3.3 发生收缩的部分

后续 research review 已经把论文叙事从“大而全”收缩成更聚焦的 thesis：

- 不把 low-level forecast + control 本身当成唯一 novelty
- 更聚焦于 **language-conditioned high-level preference routing over a frozen low-level loop**

这不是跑偏，而是让论文主张变得更窄、更可辩护。

### 3.4 发生再扩展的部分

后续又做了 multi-backbone、foundation forecast、controller diagnosis 等工作。这些扩展并不应被简单归类为“跑偏”，因为它们回答的是：

- bottleneck 在 forecast、controller 还是 router？
- 高层 routing 结论是否依赖某个 backbone？
- QP 是否是真正的主短板？

因此，这些扩展更像是**证据补强和误差定位**，而不是无意义偏航。

### 3.5 当前真正的问题

当前项目的主要问题不是研究方向偏离，而是：

> **broad idea、focused thesis、当前代码现实和历史实验结论，还没有被统一成一套稳定叙述。**

这也是为什么当前最需要解决的是“主线证据收敛”，而不是继续横向扩张。

---

## 4. 当前最准确的阶段定位

当前最适合承认的阶段描述是：

### 可以站稳的说法

- 项目已经不是 GRU-only prototype
- 已经有多 backbone forecast-control research platform
- 已有主闭环、诊断模式、实验性 router、foundation-control、controller diagnosis
- 但尚未完成统一验收与统一 thesis 收敛

### 不该继续写成稳定事实的说法

以下表述当前都不应再写成稳定工程事实：

- “当前主路径只有 GRU”
- “LLMRouter.route() 未实现”
- “router 已经 production-ready”
- “所有 backbone 都已同等成熟”
- “仓库已经稳定、永久地通过 RBC 验收”

---

## 5. 下一步应该优先做哪些实验

建议按 **P0 / P1 / P2** 排序推进。

## 5.1 P0：先做收敛实验，不要继续横向扩张

### 实验 1：固定一个低层 reference protocol，形成单一主 artifact

目标不是继续找新模型，而是冻结一个可复验的参考底座。

建议：

- 固定 1 个主 controller（优先当前最强 QP 变体）
- 固定 1–2 个代表性 backbone
  - 一个经典 learned backbone
  - 一个当前最强 foundation backbone
- 固定同一 schema、同一指标、同一输出 artifact

当前最缺的不是更多结果，而是：

> **一个能稳定复现、以后所有 router 实验都挂在它上面的低层参考底座。**

### 实验 2：做 preference-to-KPI controllability 验证

这是当前最应该优先做的实验之一。

你需要系统验证：

- 提高 carbon weight，carbon KPI 是否稳定下降？
- 提高 peak weight，peak KPI 是否稳定改善？
- `balanced / cost-saving / carbon-aware` 几类 profile 是否形成清晰 trade-off frontier？

这一实验的目的，是验证高层偏好是否真的能通过 low-level loop 稳定映射到 KPI trade-off 上。

如果低层 loop 对权重变化没有稳定响应，高层 routing 就没有足够坚实的语义基础。

## 5.2 P1：验证高层结论是否跨 backbone 稳定

### 实验 3：跨 backbone 的 routing 稳定性实验

需要回答的问题是：

> router 的增益，到底是 router 自己带来的，还是某个低层 backbone 偶然配合得好？

建议协议：

- 固定 event-driven schedule
- 固定 1 个最强 rule/text router
- 在 2–3 个 frozen low-level stack 上重复跑
- 检查结论是否方向一致

如果 routing gain 只在某一 backbone 上成立，论文就应该写成 conditional finding；如果在多个 backbone 上都成立，主张才更硬。

### 实验 4：router robustness / corruption / fallback 闭环

当前已经有 corruption 与 fallback 相关实验入口，下一步应把它们从“功能存在”推进到“研究证据”。

重点看：

- bad JSON / malformed output 对 KPI 的影响
- fallback 后性能退化是否可控
- event-driven 触发稀疏时，router 调用频率与收益是否匹配

这一步的价值在于：

- 把最小 prompt-only router 推进为 research-valid interface
- 但不把它夸大为 production system

## 5.3 P2：再考虑 thesis 加深，而不是现在全面铺开

### 实验 5：小范围 decision-focused / SPO+ feasibility check

`QPController.solve_with_cost_vector(...)` 表明仓库里确实有 decision-focused 方向的接口线索，但还没有完整闭环。

见：

- `controllers/qp_controller.py:261`

因此建议：

- 现在不要把 `SPO+` 升级成主线 deliverable
- 只做一个小规模 feasibility check
- 目标是判断“值不值得进入下一轮”，而不是把它直接写成已完成路径

---

## 6. 当前不建议继续做的事

### 6.1 不要继续盲目扩 router 命名版本

如果继续增加 `text_vN`，但没有统一协议、统一底座和统一主指标，边际收益会越来越低。

### 6.2 不要继续堆更多弱 baseline

controller diagnosis 已经做过。若 heuristic / grid 明显不是主胜负手，再继续堆弱 baseline 的论文边际价值较小。

### 6.3 不要继续把重点放在“再多几个模型名”

foundation / backbone 扩展已经足够多。下一步更需要的是**收敛证据**，而不是继续铺模型表。

### 6.4 不要过早把 deterministic production fallback 当成工程主目标

当前 router 仍然是 research interface，而不是产品模块。应先补“研究上足够可信的 fallback / robustness 证据”，再讨论工程级完备性。

---

## 7. 如果只选 3 个最该立刻做的实验

优先级最高的三个实验建议是：

1. **冻结低层 reference stack + acceptance artifact**
2. **preference-to-KPI controllability 实验**
3. **跨 backbone 的 routing 稳定性实验**

---

## 8. 最终判断

- **研究进度**：已经明显越过最小原型阶段，现在是一个具备多条实验路径的研究平台。
- **是否偏离主线**：**没有偏离 broad idea**，但经历了 thesis 收缩和必要的工程扩展。
- **当前最大问题**：不是方向错，而是**主线证据还没收敛**。
- **下一步重点**：不是继续横向扩张，而是**冻结低层底座、验证偏好到 KPI 的可控映射、检查高层结论的跨 backbone 稳定性**。
