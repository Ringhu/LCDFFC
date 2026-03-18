# Agent E: LLM 路由模块

## 角色

你负责 `llm_router/` 和 `scripts/` 目录。**不要修改** data, models, controllers, eval 目录下的任何文件。

## 负责文件

- `llm_router/__init__.py`
- `llm_router/router.py`
- `llm_router/prompt_templates.py`
- `llm_router/json_schema.py`
- `scripts/generate_instruction_data.py`
- `configs/llm_router.yaml`

## 目标

### Sprint 4: Prompt-Only Router

1. **完善 `router.py`**：
   - 实现 `_call_llm()`：支持 vLLM 后端（HTTP API）和 transformers 后端
   - 实现 `route()`：构建 prompt → 调用 LLM → 解析 JSON → 校验 → 返回
   - 错误处理：JSON 解析失败时返回默认权重
   - 支持 batch 调用（可选）

2. **完善 `prompt_templates.py`**：
   - 已有基本模板，根据实验效果迭代
   - 添加 few-shot examples 提高输出稳定性
   - 考虑 chain-of-thought 变体（LLM 先推理再输出 JSON）

3. **完善 `json_schema.py`**：
   - 已有校验逻辑
   - 添加更完善的 fallback 策略
   - 为 constrained decoding（vLLM guided generation）预留 schema

4. **合成指令数据**：
   - `scripts/generate_instruction_data.py` 已有基本逻辑
   - 扩展场景多样性（极端天气、节假日、电网事故等）
   - 输出格式兼容 LoRA 微调（Alpaca/ShareGPT 格式）

### 后续: LoRA 微调

5. **预留 LoRA 接口**：
   - 数据格式：`{"instruction": ..., "input": context_json, "output": weights_json}`
   - 微调脚本可用 LLaMA-Factory 或 PEFT

## LLM 调用示例

```python
# vLLM 后端
import requests

response = requests.post("http://localhost:8000/v1/chat/completions", json={
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": messages,
    "temperature": 0.1,
    "max_tokens": 256,
})
text = response.json()["choices"][0]["message"]["content"]

# transformers 后端
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
```

## 接口约定

```python
from llm_router import LLMRouter

router = LLMRouter(model_name="Qwen/Qwen2.5-7B-Instruct")
result = router.route({
    "time_of_day": "afternoon",
    "hour": 14,
    "day_type": "weekday",
    "price": 0.35,
    "price_trend": "peak_coming",
    "carbon_intensity": 450.0,
    "temperature": 32.5,
    "soc": 0.6,
    "grid_stress": "high",
})
# result = {"weights": {"cost": 0.3, ...}, "constraints": {"reserve_soc": 0.2, ...}}
```

## 止损点

- LLM 输出格式不稳定 → 增加 few-shot examples、降低 temperature
- 延迟太高 → 改为每小时调用一次（而非每步）
- vLLM 部署失败 → 改用 transformers 直接推理
