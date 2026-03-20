# Auto Review Note: Targeted Ablation Next Step（2026-03-20）

## 当前证据

截至目前：

- `text_best` 已经是当前已验证的最佳文本路由
- `M4` 已从“几乎无差异”推进到“有可解释的 fallback 保护信号”
- 但 `text_best` 相比 regime-wise best fixed 上界的剩余差距仍然存在
- 分段归因已经明确指出：
  - `reserve` 是最明显的局部短板
  - `carbon` 段也存在 expert mapping / blending 的结构性可改空间

因此，下一步最值得做的不是立刻做 `v5`，而是先验证：

> 当前剩余差距到底主要来自 `reserve` 保护不足，还是来自 `carbon` 段错误路由。

## 候选方向

### 方案 A：直接做 `v5`

- 优点：
  可以继续提高主结果
- 缺点：
  在当前证据还没拆清楚之前，容易继续盲调
  即使 `v5` 有改进，也很难解释它到底修正了哪一类问题

### 方案 B：做 targeted ablation

- 优点：
  直接回答当前最重要的两个问题：
  - `reserve` 约束保护到底有多关键
  - `carbon` 段错路由到底会造成多大伤害
  更适合形成论文里的误差分析 / 失败模式分析
- 缺点：
  不是直接提升主结果，而是先提升解释力

### 方案 C：直接去做 OOD / transfer

- 优点：
  可以扩展故事
- 缺点：
  当前主机制还没解释清楚，做这个太早

## Review 决策

选择 **方案 B**。

这轮应优先做两个 targeted corruption：

1. `reserve_drop_guard`
   - 只在 `reserve` 段破坏 `reserve_soc`
2. `carbon_misroute`
   - 只在 `carbon` 段把路由错误导向 cost-heavy expert

## 目标

1. 判断 `reserve` 保护不足是否是当前最主要短板
2. 判断 `carbon` 段错路由对主结果有多大贡献
3. 看 heuristic fallback 在这两类错误下的保护模式是否不同

## 成功标准

- 至少有一个 targeted ablation 能显著拉开 none vs fallback
- 能明确回答：
  - 是 `reserve` 更敏感
  - 还是 `carbon` 更敏感
- 能为后续 `v5` 指定更窄的修改方向

## 如果结果不明显

如果这两个 targeted ablation 仍然拉不开差距，那么更合理的解释就会变成：

> 当前高层路由剩余误差并不主要来自单一 regime 的局部失效，而更可能来自跨 regime 切换行为本身。

那时再进入 `stale instruction / persistence` 类实验会更合适。
