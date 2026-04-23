# NexusMind Benchmark 验证框架

> 通过真实案例对照，证明 NexusMind 舆情推演系统的有效性。

## 核心指标

| 指标 | 全称 | 权重 | 含义 |
|------|------|------|------|
| **TCS** | Trend Consistency Score | 35% | 模拟情绪走势与现实走势是否同涨同跌 |
| **TPH** | Turning Point Hit Rate | 25% | 模拟是否抓住现实中的关键拐点 |
| **KAC** | Key Actor Coverage | 20% | 关键主体是否被系统覆盖 |
| **EOA** | Event Order Accuracy | 20% | 事件顺序是否与现实一致 |

**综合评分** = `0.35 × TCS + 0.25 × TPH + 0.20 × KAC + 0.20 × EOA`（满分 100）

## 使用流程

1. 为案例整理参考真值（`reference_data.json`）
2. 准备固定种子材料（`seed_materials/`）
3. 运行系统，导出评估结果（`evaluation_result.json`）
4. 用 `scoring.py` 计算评分

```bash
python benchmark/scoring.py benchmark/case_01_wuhan_university_library
```

## 目录结构

```
benchmark/
├── README.md
├── scoring.py
├── case_01_wuhan_university_library/
│   ├── case_overview.md
│   ├── reference_data.json
│   ├── evaluation_result.json    # 系统跑完后填入
│   └── seed_materials/
├── case_02_huazhong_agricultural_university_academic_misconduct/
│   ├── case_overview.md
│   ├── reference_data.json
│   └── seed_materials/
└── case_03_jiangxi_industry_vocational_college_food_safety/
    ├── case_overview.md
    ├── reference_data.json
    └── seed_materials/
```
