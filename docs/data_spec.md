# 数据规格说明（reference only）

这个文件只保留数据格式和产物约束，不负责判断当前阶段结论。

当前实现和入口命令如果有冲突，以 `code + tests` 为准。

## 数据来源

当前数据来自 CityLearn 环境回放，不是外部静态表。

推荐入口：

```bash
python data/prepare_citylearn.py \
  --schema citylearn_challenge_2023_phase_1 \
  --output_dir artifacts/
```

`data/prepare_citylearn.py` 接受内置数据集名或本地 schema 路径，运行 zero-action episode 并导出时序数据。

## 主要产物

脚本默认在 `artifacts/` 下生成：

- `citylearn_data.csv`
- `citylearn_data.npz`
- `forecast_data.csv`
- `forecast_data.npz`
- `data_summary.json`
- `norm_stats.npz`

这些文件默认都是本地产物，不应提交到公开仓库。

## 预测数据格式

`forecast_data.npz` 是当前 forecasting 训练和评估会共用的核心文件。

当前列顺序是：

1. `day_type`
2. `hour`
3. `outdoor_dry_bulb_temperature`
4. `carbon_intensity`
5. `electricity_pricing`
6. `non_shiftable_load_avg`
7. `solar_generation_avg`
8. `electrical_storage_soc_avg`
9. `net_electricity_consumption_avg`

这个顺序需要和 `eval/run_controller.py` 里的特征提取逻辑保持一致。

## 当前预测目标

当前共享训练入口是 `scripts/train_forecaster.py`。

当前默认目标列仍然是这 3 个：

- `electricity_pricing`
- `non_shiftable_load_avg`
- `solar_generation_avg`

对应列索引是 `[4, 5, 6]`。

## 标准化和切分

- 数据集通过 `CityLearnDataset.from_file()` 构建
- 默认按 `train / val / test` 切分
- 标准化统计保存为 `artifacts/norm_stats.npz`
- `history_len` 和 `horizon` 默认都常见为 `24`，实际值以配置文件为准

## 当前高风险点

- `forecast_data.npz` 列顺序和 `run_controller.py` 假设不一致，会直接影响控制效果
- 训练和评估如果用了不同 `norm_stats`，反标准化会出错
- 新增目标列前，先确认 controller 真的会用到这些信号
