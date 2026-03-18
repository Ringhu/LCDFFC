# 数据规格说明

## 数据来源

当前数据来源于 CityLearn 环境回放，而不是外部静态表。  
`data/prepare_citylearn.py` 接受内置数据集名或本地 schema 路径，运行零动作 episode 并导出时序数据。

推荐入口：

```bash
python data/prepare_citylearn.py \
  --schema citylearn_challenge_2023_phase_1 \
  --output_dir artifacts/
```

## 主要产物

脚本默认在 `artifacts/` 下生成：

- `citylearn_data.csv`
- `citylearn_data.npz`
- `forecast_data.csv`
- `forecast_data.npz`
- `data_summary.json`

这些文件默认属于本地产物，不应提交到公开仓库。

## 预测数据格式

`forecast_data.npz` 是当前训练入口使用的核心文件。其列顺序与 `eval/run_controller.py` 中的特征提取逻辑保持一致，当前包含：

1. `day_type`
2. `hour`
3. `outdoor_dry_bulb_temperature`
4. `carbon_intensity`
5. `electricity_pricing`
6. `non_shiftable_load_avg`
7. `solar_generation_avg`
8. `electrical_storage_soc_avg`
9. `net_electricity_consumption_avg`

## 当前预测目标

`scripts/train_gru.py` 当前使用以下 3 个目标列：

- `electricity_pricing`
- `non_shiftable_load_avg`
- `solar_generation_avg`

对应列索引为 `[4, 5, 6]`。

## 标准化与切分

- 数据集通过 `CityLearnDataset.from_file()` 构建
- 默认按 `train / val / test` 切分
- 标准化统计保存为 `artifacts/norm_stats.npz`
- `history_len` 与 `horizon` 当前都默认为 `24`

## 当前数据风险

- 如果 `forecast_data.npz` 的列顺序和 `run_controller.py` 假设不一致，会直接影响控制性能
- 如果标准化统计和训练/评估使用的数据源不一致，会导致预测反标准化错误
- 当前第一阶段重点不是扩展更多目标变量，而是先验证现有目标设计是否足够支撑 QP 闭环
