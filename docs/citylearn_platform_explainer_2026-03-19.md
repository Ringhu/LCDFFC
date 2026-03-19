# 从 0 开始理解 LCDFFC 与 CityLearn（2026-03-19）

## 1. 这到底是在做什么项目

如果完全不看代码，只用一句话概括，这个项目是在做：

**利用时间序列预测来帮助建筑群储能控制，在 CityLearn 这个仿真平台上验证这种“先预测、再控制”的方法是否真的比简单基线更好。**

更具体一点：

- 场景是 `CityLearn Challenge 2023`
- 对象是一个小型建筑群，而不是单栋楼
- 当前只控制电池，不直接控制所有设备
- 方法不是 RL 直接学动作，而是 `forecast-then-control`
- 当前闭环是：`历史观测 -> GRU 预测器 -> QP 控制器 -> CityLearn 环境`

这个项目的研究主线不是“一上来就让 LLM 或 RL 直接控制系统”，而是先搭一个稳定、可解释、可复现的底层闭环，然后再考虑更复杂的扩展模块，例如：

- uncertainty-aware fallback
- decision-focused learning
- LLM 高层偏好路由

## 2. 为什么要做这件事

建筑能源系统的控制，表面上是在“决定电池什么时候充、什么时候放”，本质上是在处理一个更难的问题：

**未来会发生什么并不确定，但控制决策又必须提前做。**

在这个问题里，至少有三类典型的不确定量：

- 电价会变
- 碳强度会变
- 建筑负荷和光伏出力会变

所以一个自然的问题是：

如果能提前预测未来 24 步的关键时间序列，控制器能不能做出更好的动作？

这也是这个项目的核心研究动机。它并不是只想做一个“预测得更准”的模型，而是想回答：

**时间序列预测到底有没有真正改善下游控制效果？**

例子：

- 如果预测器把未来晚高峰负荷看出来了，控制器就可以在低价时段先充电，在高峰时段放电。
- 如果预测器看不准，控制器就可能在错误时段充放电，反而让成本和峰值更高。

## 3. 为什么用 CityLearn

`CityLearn` 是一个建筑能源控制仿真平台。对当前项目来说，它的价值不在于“它是一个库”，而在于它提供了一个可重复的实验环境：

- 你可以在相同场景下重复比较不同控制策略
- 你可以读取每一步的 observation
- 你可以把 action 送回环境
- 你可以拿到完整的 KPI 结果，例如成本、碳排、峰值

所以在这个项目里，`CityLearn` 既扮演了“数据来源”，也扮演了“被控制对象所在的仿真环境”。

一个非常重要的理解是：

**这里的数据不是先天存在的一张固定表，而是通过环境回放得到的。**

例如：

- `data/prepare_citylearn.py` 并不是去下载一份 CSV 后直接读入
- 它实际做的是：初始化环境、跑一轮零动作 episode、把每一步 observation 导出成数据文件

## 4. 当前到底在控制什么

当前项目不是控制整栋楼的所有设备，而是一个更聚焦的问题：

**在 `central_agent=True`、battery-only 的设定下，控制建筑群里的电池储能动作。**

本地缓存的 `CityLearn 2023 Phase 1` 场景中，当前有 3 栋建筑：

- `Building_1`
- `Building_2`
- `Building_3`

三块电池的参数分别是：

```json
[
  {"capacity": 4.0, "efficiency": 0.95, "nominal_power": 3.32},
  {"capacity": 4.0, "efficiency": 0.95, "nominal_power": 3.32},
  {"capacity": 3.3, "efficiency": 0.96, "nominal_power": 1.61}
]
```

虽然 `central_agent=True`，但环境里的 action 不是单个数，而是一个多槽位向量。当前 action 槽位是：

```text
[
  'dhw_storage', 'electrical_storage', 'cooling_device',
  'dhw_storage', 'electrical_storage', 'cooling_device',
  'dhw_storage', 'electrical_storage', 'cooling_device'
]
```

当前仓库的控制器只主动修改名字为 `electrical_storage` 的那些槽位，也就是只控制电池。

例子：

```python
action = [[0.0] * len(env.action_names[0])]

for i, name in enumerate(env.action_names[0]):
    if name == "electrical_storage":
        action[0][i] = battery_action
```

## 5. 希望实现什么样的控制效果

当前项目里，“好的控制”不是一个抽象说法，而是比较明确的目标：

1. 降低购电成本 `cost`
2. 降低碳排 `carbon`
3. 降低最大用电峰值 `peak`
4. 同时保证动作和 SOC 不违反物理约束

所以一个“好控制器”的含义不是：

- 动作看起来聪明
- 预测误差很小
- 曲线很平滑

而是：

**在 CityLearn 的完整闭环仿真里，最终 KPI 比基线更好。**

当前仓库使用 `RBC` 作为第一阶段基线。当前本地验证结果里：

- `RBC`: cost `33.0114`, carbon `499.6858`, peak `16.4417`
- `learned forecast + QP`: cost `32.4935`, carbon `496.2018`, peak `14.9950`

这说明，在当前这条主线上，预测 + 控制已经不仅仅是“能跑”，而是确实让关键指标变好了。

## 6. 怎么判断控制是好的

当前项目主要看 4 个 KPI：

### 6.1 cost

表示总购电成本。越低越好。

例子：

- 如果控制器能在低电价时充电、在高电价时放电，`cost` 会下降。

### 6.2 carbon

表示总碳排放。越低越好。

例子：

- 如果控制器尽量避开高碳强度时段从电网取电，`carbon` 会下降。

### 6.3 peak

表示区级净负荷的最大峰值。越低越好。

例子：

- 如果晚高峰时统一放电削峰，`peak` 会下降。

### 6.4 ramping

表示净负荷变化的剧烈程度。通常越低越平稳。

例子：

- 如果控制器让动作频繁大幅跳变，`ramping` 可能会变差。

当前第一阶段验收并不是要求所有指标都最优，而是要求：

**在 `cost / carbon / peak` 中，至少有 2 项打平或优于 `RBC`。**

## 7. 时间序列数据在这里起什么作用

这是这份说明里最关键的一点。

时间序列数据在这个项目里不是边角料，而是整个方法链的核心。

它主要有 4 个作用：

### 7.1 作用一：作为环境观测

环境每一步都会给出一个 observation，其中包含很多时序相关量，例如：

- 当前小时 `hour`
- 当前室外温度 `outdoor_dry_bulb_temperature`
- 当前碳强度 `carbon_intensity`
- 当前电价 `electricity_pricing`
- 当前建筑负荷 `non_shiftable_load`
- 当前光伏发电 `solar_generation`

这些量本身就是时间序列。

### 7.2 作用二：作为离线训练数据

项目会先把环境回放成数据文件，再拿这些历史序列训练预测器。

导出入口：

```bash
python data/prepare_citylearn.py \
  --schema /cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json \
  --output_dir artifacts/
```

输出的核心文件是：

- `artifacts/citylearn_data.csv`
- `artifacts/forecast_data.csv`
- `artifacts/forecast_data.npz`
- `artifacts/data_summary.json`

### 7.3 作用三：作为控制器对未来的输入

当前控制器不是只看“此刻”的状态，而是看未来一段 horizon 的预测结果。

当前预测目标是 3 个时间序列：

- `electricity_pricing`
- `non_shiftable_load_avg`
- `solar_generation_avg`

也就是说，预测器不是为了预测所有变量，而是为了给控制器提供未来 24 步最关键的控制相关量。

### 7.4 作用四：作为诊断工具

项目里还会用不同 forecast 模式做诊断：

- `learned`：模型预测
- `oracle`：直接用真实未来值
- `myopic`：只重复当前值

这有助于回答：

- 如果给控制器“完美未来”，它会不会做得更好？
- 如果只是看当前值，不做真正预测，会不会差很多？

这类对照实验本身也是围绕时间序列展开的。

## 8. 从环境到控制的完整工作流

下图给出当前仓库的主工作流：

![CityLearn 工作流](assets/notion/citylearn_workflow_compact.png)

可以把这条链路拆成 6 步：

### 第 1 步：加载场景

```python
from citylearn.citylearn import CityLearnEnv

env = CityLearnEnv(schema=schema_path, central_agent=True)
```

这里的 `schema.json` 定义了：

- 场景时长
- 建筑数量
- 设备参数
- observation 配置
- action 配置

### 第 2 步：读取 observation

```python
obs = env.reset()
```

当前版本下真实结构是：

```text
type(obs) = tuple
len(obs) = 2
type(obs[0]) = list
len(obs[0]) = 1
type(obs[0][0]) = list
len(obs[0][0]) = 49
```

也就是说，当前中央 agent 的 observation 在 `obs[0][0]`，长度是 `49`。

### 第 3 步：把原始 observation 压缩成当前工程使用的特征

当前项目没有把全部 49 维 observation 都丢给预测器，而是提取成 9 维特征：

1. `day_type`
2. `hour`
3. `outdoor_dry_bulb_temperature`
4. `carbon_intensity`
5. `electricity_pricing`
6. `non_shiftable_load_avg`
7. `solar_generation_avg`
8. `electrical_storage_soc_avg`
9. `net_electricity_consumption_avg`

对应函数：

```python
from eval.run_controller import obs_to_features

flat_obs = obs[0][0]
features = obs_to_features(flat_obs, env.observation_names[0])
print(features.shape)  # (9,)
```

### 第 4 步：形成历史窗口

预测器不会只看 1 个时刻，而是看一段过去的序列。

当前默认：

- `history_len = 24`
- `horizon = 24`

意思是：

- 用过去 24 步预测未来 24 步

### 第 5 步：生成未来预测

当前有三种方式：

- `learned`：GRU 模型预测未来 24 步
- `oracle`：直接切出真实未来 24 步
- `myopic`：把当前值重复 24 次

### 第 6 步：控制器输出动作并送回环境

控制器入口：

```python
action = ctrl.act(
    state={"soc": soc_vals},
    forecast=qp_forecast,
    weights=weights,
    constraints=constraints,
)
```

然后把共享电池动作广播到 3 栋楼的 `electrical_storage` 槽位，再调用：

```python
obs, reward, terminated, truncated, info = env.step(action)
```

这就形成了完整的滚动闭环。

## 9. 数据流向是什么

如果把项目当成“数据是怎么流动的”来看，可以理解成下面这条链：

```text
schema.json
  -> CityLearnEnv
  -> raw observation
  -> citylearn_data.csv
  -> forecast_data.csv / npz
  -> CityLearnDataset
  -> GRU forecast
  -> QPController
  -> action
  -> CityLearnEnv
```

这里每个节点的作用是：

- `schema.json`：定义环境规则
- `CityLearnEnv`：产生 observation，接收 action
- `citylearn_data.csv`：完整回放数据
- `forecast_data.csv / npz`：当前预测模型真正使用的压缩数据
- `CityLearnDataset`：把连续序列切成 `(history, future)` 样本
- `GRU forecast`：预测未来
- `QPController`：根据未来预测生成动作

### 一个真实数据样例

当前 `forecast_data.csv` 前 5 行是：

```text
 day_type  hour  outdoor_dry_bulb_temperature  carbon_intensity  electricity_pricing  non_shiftable_load_avg  solar_generation_avg  electrical_storage_soc_avg  net_electricity_consumption_avg
      5.0   1.0                         24.66          0.402488              0.02893                0.322084                   0.0                         0.2                         0.476122
      5.0   2.0                         24.07          0.382625              0.02893                0.316666                   0.0                         0.0                         0.000000
      5.0   3.0                         23.90          0.369458              0.02893                0.313329                   0.0                         0.0                         0.000000
      5.0   4.0                         23.87          0.367017              0.02893                0.313679                   0.0                         0.0                         0.000000
      5.0   5.0                         23.83          0.374040              0.02893                0.328668                   0.0                         0.0                         0.000000
```

一个真实时间片段示意图：

![forecast_data 时间序列样例](assets/notion/citylearn_series.png)

## 10. 当前仓库是怎么进行控制的

当前控制方式不是 RL policy 直接出动作，而是一个更可解释的优化控制器：

- 先预测未来 24 步
- 再用 QP 求一个“此刻应该怎么充放电”

当前控制器在做的事情，本质上是平衡几类目标：

- 成本
- 碳排
- 峰值
- 动作平滑性

同时满足几类约束：

- 电池 SOC 上下界
- 充放电功率上限
- 可选的 `reserve_soc`

例子：

- 如果未来几步电价高、负荷也高，控制器可能倾向于提前充电、然后在高价时段放电。
- 如果未来几步已经是净负荷很低甚至接近净输出，控制器就不应该为了“进一步变负”而做过激放电。

## 11. 怎样评价这种控制是“好”的

对这个项目来说，“好控制”至少要满足三层含义：

### 第一层：物理上可行

例如：

- SOC 不能超上下界
- 动作不能超过功率限制

### 第二层：闭环上有效

例如：

- 不能只是预测误差低
- 必须在完整仿真后让 KPI 变好

### 第三层：相比基线有优势

例如当前基线 `RBC`：

- `cost`: `33.0114`
- `carbon`: `499.6858`
- `peak`: `16.4417`

当前 learned 控制结果：

- `cost`: `32.4935`
- `carbon`: `496.2018`
- `peak`: `14.9950`

这就说明当前 learned 路径已经在真实闭环里优于基线。

## 12. 一轮仿真到底要多久

以下数字是在当前机器、CPU、当前本地缓存 schema 上实际测得的：

- `run_rbc.py` 零动作基线：`719` 步，`12.059 s`，约 `16.77 ms/step`
- `run_controller.py --forecast_mode learned`：`719` 步，`34.628 s`，约 `48.16 ms/step`

怎么理解这个时间：

- 环境本身不慢
- 真正拉长时间的是“每一步都要做一次预测 + 一次优化求解”

例子：

- 如果只是想回放环境和看基线，十几秒就能跑完一轮
- 如果要跑带预测和 QP 的控制，完整一轮大约半分钟量级

对当前研究阶段来说，这个开销是可接受的。

## 13. 给第一次接触项目的人，一个最推荐的理解顺序

如果你完全从 0 开始，我建议按这个顺序理解：

1. 先看项目背景：这个项目是“时间序列预测帮助控制”，不是单纯预测，也不是直接 RL
2. 再看控制对象：当前只控制电池，目标是降低 cost / carbon / peak
3. 再看 CityLearn 是什么：它是环境，不是单纯数据表
4. 再看 `data/prepare_citylearn.py`：理解数据是如何从环境回放出来的
5. 再看 `forecast_data.csv`：理解预测器到底在吃什么
6. 再看 `eval/run_controller.py`：理解预测和控制是如何串成闭环的
7. 最后再看评估结果：理解什么叫“控制有效”

## 14. 最小可运行样例

### 样例 A：最小 observation 读取

```python
from citylearn.citylearn import CityLearnEnv

schema = "/cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json"
env = CityLearnEnv(schema=schema, central_agent=True)
obs = env.reset()
flat_obs = obs[0][0]
print(len(flat_obs))  # 49
```

### 样例 B：最小零动作 rollout

```python
zero_action = [[0.0] * len(env.action_names[0])]
terminated = False
truncated = False

while not (terminated or truncated):
    obs, reward, terminated, truncated, info = env.step(zero_action)
```

### 样例 C：把 observation 转成当前工程使用的 9 维特征

```python
from eval.run_controller import obs_to_features

features = obs_to_features(flat_obs, env.observation_names[0])
print(features.shape)  # (9,)
print(features)
```

### 样例 D：导出当前训练数据

```bash
python data/prepare_citylearn.py \
  --schema /cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json \
  --output_dir artifacts/
```

### 样例 E：运行当前闭环控制

```bash
python eval/run_controller.py \
  --schema /cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json \
  --checkpoint artifacts/checkpoints/gru_mse_best.pt \
  --norm_stats artifacts/norm_stats.npz \
  --forecast_config configs/forecast.yaml \
  --controller_config configs/controller.yaml \
  --output_dir reports/ \
  --tag learned_qp \
  --forecast_mode learned \
  --device cpu
```

## 15. 当前阶段最应该记住的 5 个知识点

1. `CityLearn` 在这个项目里首先是一个交互式环境。
2. 当前控制对象是建筑群电池，而不是环境里的所有设备。
3. 时间序列预测的意义不在于“预测更准”本身，而在于它是否改善了控制 KPI。
4. 当前项目的主方法是 `forecast-then-control`，不是端到端 RL。
5. 对这个项目来说，最终判断标准是完整闭环 KPI，而不是单个模块的局部指标。
