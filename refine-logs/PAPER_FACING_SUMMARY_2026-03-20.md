# Paper-Facing Summary（2026-03-20）

## 1. 当前论文主张与证据状态

当前这条研究主线的论文主张可以收敛为：

> 在不重训低层 `forecast + QP` 系统的前提下，语言条件化的高层路由器可以在线适配变化中的运营偏好，并且优于单一固定权重控制器。

到目前为止，这个主张已经具备**正向实验支撑**，但仍有明确边界：

- 已经成立的部分：
  - 当前最佳文本路由 `text_v4` 稳定优于最佳单一固定控制器 `fixed_reserve`
  - fallback 的作用已经被证明，不再只是直觉性设计
  - 误差来源已经被拆分到具体 regime，而不是停留在“router 还不够好”的模糊判断
- 尚不能过度主张的部分：
  - 当前结果还没有追平 regime-wise best fixed 上界
  - 当前不能写成“语言路由已经全面优于所有结构化替代和更强上界”
  - 当前也不能写成“局部 router 机制仍有大量可挖空间”，因为 `v5 / v6 / v7` 已经显示局部 release guard 调优进入饱和区

因此，当前最稳妥的论文表述应当是：

> 语言条件化高层路由在偏好切换任务中已经表现出相对于单一固定控制器的优势，同时具备可解释的误差分析与安全性证据；但它仍未追平更强的 regime-wise fixed upper bound，因此论文应将重点放在“动态适配能力 + 误差与安全性分析”，而不是宣称已经达到最优控制性能。

## 2. 主结果

### 2.1 当前 best router

当前经过完整实验、review 和多轮局部改进后，**最佳文本路由版本仍为 `text_v4`**。

`text_v4` 的核心思想不是自由生成连续权重，而是：

- 先从文本中识别主偏好
- 再把文本路由到已经被实验验证过较强的 fixed expert profiles
- 只在这些 experts 上做受限选择与轻量混合

这比 `v1 / v2 / v3` 更稳定，也更贴近当前实验事实。

### 2.2 主结果表

在统一的 `preference-shift` 协议下，关键方法的汇总结果如下：

| Run | avg_preference_score | avg_regret_to_best_fixed | avg_regret_to_best_single_fixed |
|---|---:|---:|---:|
| fixed_reserve | 0.876931 | 0.001224 | 0.000000 |
| heuristic_router | 0.878355 | 0.002647 | 0.001424 |
| text_router_v2 | 0.876864 | 0.001157 | -0.000067 |
| text_router_v4 | 0.876622 | 0.000914 | -0.000309 |
| text_router_v5 | 0.876862 | 0.001154 | -0.000070 |
| text_router_v6 | 0.876622 | 0.000914 | -0.000309 |
| text_router_v7 | 0.876622 | 0.000914 | -0.000309 |

这里最关键的事实有三条：

1. `text_v4` 优于最佳单一固定控制器 `fixed_reserve`
2. `text_v4` 也优于 `heuristic_router`
3. `v5 / v6 / v7` 都没有超过 `v4`

因此当前可以明确写成：

> 在偏好切换评测中，当前最佳的语言条件化路由器 `text_v4` 已经优于单一固定权重控制器；但后续几轮 reviewed 局部改进未能继续超过 `v4`，说明当前最优点已经比较稳定。

## 3. 误差分析

### 3.1 当前剩余误差主要落在哪些 regime

segment-level gap analysis 已经明确：

- `text_v4` 相对 `text_v2` 的整体优势主要来自：
  - `cost`
  - `carbon`
  - `peak`
- `reserve` 段反而仍然是 `v2` 更强

这说明 `text_v4` 的优势并不是“每一段都更好”，而是：

> 它在前三段累计赢得更多，因此总体平均分更低，但 `reserve` 仍是当前最明显的局部短板。

进一步与 `fixed_reserve` 对比可以看到：

- `text_v4` 在 `cost / peak / reserve` 段更好
- 但在 `carbon` 段更差

因此当前最准确的误差分解是：

> 剩余误差不是平均散落在所有 regime 上，而是集中在两个地方：`reserve` 是第一主敏感点，`carbon` 是第二主敏感点。

### 3.2 targeted ablation 的结论

针对这两个点，已经做了 targeted ablation：

- `reserve_drop_guard`
- `carbon_misroute`

完整 GPU2 结果如下：

| Run | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| clean text_best | 30.5693 | 468.3415 | 14.9948 | 858.7306 |
| reserve_drop_none | 30.6324 | 469.5827 | 15.1640 | 859.6667 |
| reserve_drop_fallback | 30.5752 | 468.4454 | 14.9948 | 858.7073 |
| carbon_misroute_none | 30.6446 | 469.7692 | 15.0031 | 861.8297 |
| carbon_misroute_fallback | 30.5818 | 468.5174 | 15.0001 | 859.8567 |

这些结果说明：

- `reserve_drop_guard` 对 `peak` 的直接伤害更强，属于第一主敏感项
- `carbon_misroute` 主要拖累 `carbon` 和 `ramping`，属于第二主敏感项

所以论文中的误差分析部分可以明确写成：

> 当前语言路由器的剩余误差主要由 reserve-aware 保护不足和部分 carbon misrouting 引起，其中 reserve 是更强的主导误差源。

## 4. 安全性分析

### 4.1 transition-aware corruption

在更真实的高层失效协议 `transition_wrong_expert` 下：

| Run | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| clean text_best | 30.5693 | 468.3415 | 14.9948 | 858.7306 |
| transition_none | 30.5744 | 468.3799 | 15.0067 | 859.5113 |
| transition_fallback | 30.5785 | 468.4277 | 14.9948 | 858.9729 |

这里已经能看出清晰 tradeoff：

- 无 fallback 时，`peak` 和 `ramping` 都变差
- 有 fallback 时，`peak` 回到 clean baseline，`ramping` 的恶化也显著减小
- 代价是 `cost / carbon` 略有增加

这说明：

> fallback 不是一个“所有指标都更优”的模块，而是一个在高层失效下优先保护 `peak / smoothness` 的安全机制。

### 4.2 targeted reserve failure

在 `reserve_drop_guard` 下，fallback 的保护更明显：

- 无 fallback：
  - `reserve_gap = 0.0822`
  - `peak = 15.1640`
- 有 fallback：
  - `reserve_gap = 0.0000`
  - `peak = 14.9948`

这是一条非常强的安全性证据，因为它不是平均指标的轻微改善，而是：

> heuristic fallback 直接把 reserve-related violation 从明显存在拉回到 0，并同时恢复了 peak 指标。

因此，当前论文里的安全性分析已经有足够材料，不必再写成“未来工作”，而应作为当前工作的实证组成部分。

## 5. 已经足够的部分

从论文推进角度看，以下部分已经足够，不需要继续投入局部试错：

1. **最佳 router 的选择已经稳定**
   - `text_v4` 是当前 best
   - `v5 / v6 / v7` 都没有超过它

2. **主结果已经具备正向支撑**
   - `text_v4` 优于最佳单一固定控制器

3. **误差分析已经足够具体**
   - 不再是抽象的“router 还有误差”
   - 已经具体到 `reserve` 和 `carbon`

4. **安全性分析已经成立**
   - fallback 的作用已经能形成 paper-facing 叙事

## 6. 仍需改进的部分

当前还不能完全宣称论文已经闭环，原因主要有三条：

1. **还没有追平 regime-wise best fixed 上界**
   - 当前 best `text_v4` 仍有 `avg_regret_to_best_fixed = 0.000914`

2. **局部 router 微调已经进入低收益区**
   - 继续细调 reserve release guard 没有再带来增益

3. **泛化证据仍不足**
   - OOD / transfer 还没有做
   - 目前结果仍主要建立在当前 preference-shift 协议上

因此，论文当前的限制部分应该诚实写成：

> 当前方法已经展示了动态偏好适配能力与安全性优势，但尚未追平更强的 regime-wise upper bound，且其跨分布泛化能力仍有待进一步验证。

## 7. 下一步最合理的推进方向

基于当前证据，**不建议继续做 `v8` 这类局部 router 微调**。

更合理的下一步有且只有两类：

### 方向 A：paper-facing review / paper planning

先把当前结果当作一篇论文雏形来 review，重点看：

- 当前主张是否收得足够稳
- 主结果、误差分析、安全性分析三部分是否已经构成完整故事
- reviewer 还会追问什么缺口

### 方向 B：补一轮 OOD / transfer

只在 review 明确指出“泛化证据不足”时，再补最小 OOD / transfer 实验。

因此，当前最合理的实际推进顺序是：

1. 用本文件作为 paper-facing 总结底稿
2. 对这份总结做一轮 review
3. 根据 review 决定是否补 OOD / transfer
4. 再进入 `paper-plan / paper-write`

## 8. 作用范围提醒

本文件中的所有正向结论，都应默认限定在**当前 CityLearn preference-shift 协议**下理解。

也就是说，当前可以稳定主张的是：

> 在当前 CityLearn preference-shift 评测设置下，`text_v4` 优于最佳单一固定控制器，并且具备可解释的误差分析与安全性分析结果。

当前还不能把这些结果外推成更强的泛化性表述，例如：

- 对任意运营偏好切换都有效
- 对任意分布偏移都稳定
- 对所有更强上界都已逼近或超过

## 9. 论文排布建议

如果把当前结果整理成论文，最合理的排布建议是：

### 主文建议放入

- `text_v4` vs 单一固定控制器 / heuristic 的主结果
- `reserve_drop_guard` 与 `carbon_misroute` 的 targeted ablation，作为误差分析
- `transition_wrong_expert` 与 targeted reserve failure 下的 fallback 结果，作为安全性分析

### Appendix 建议放入

- `v5 / v6 / v7` 的 reviewed 负结果
- 更细的 route stats
- 局部 release guard 调优过程
- 更细的 protocol 工程细节

这样做的好处是：

- 主文聚焦于“主结果 + 误差分析 + 安全性分析”
- 负结果仍然保留，但不会压垮主线叙事

## 10. 当前不能主张的内容

为了避免后续写作时把主张写得过满，当前应明确避免以下说法：

1. 不能写成“当前方法优于 regime-wise best fixed upper bound”
2. 不能写成“语言层已经证明优于所有结构化替代”
3. 不能写成“局部 router 机制仍然存在明确、稳定的可提升空间”

更稳妥的写法应当是：

- 当前方法已经优于单一固定控制器
- 当前方法还未追平更强 upper bound
- 当前局部 router 微调已经进入低收益区
- 后续是否补 OOD / transfer，应由下一轮更高层 review 决定
