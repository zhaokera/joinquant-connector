# JoinQuant Connector for OpenClaw

基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》投资理念的聚宽量化策略。

## 功能特性

### 📊 投资理念集成
- **邱国鹭四要素**: 估值、品质、时机、仓位管理
- **李杰能力圈理论**: 好生意、好公司、好价格
- **价值投资框架**: 安全边际、护城河、长期持有

### 🤖 量化策略
- **智能选股**: 结合技术面+基本面+新闻情绪
- **动态调仓**: 基于市场环境自动调整仓位
- **风险控制**: 止损止盈、分散投资、最大回撤控制

### 🔗 OpenClaw 集成
- 调用 `openclaw-stock-analyzer` 获取股票分析
- 调用 `openclaw-finance-news` 获取新闻情绪
- 调用 `openclaw-duckgo` 获取实时资讯

## 使用方法

### 1. 聚宽平台部署
```python
# 在聚宽研究环境中直接运行
from joinquant_connector import ValueInvestingStrategy
```

### 2. 本地回测
```bash
python backtest.py --start-date 2023-01-01 --end-date 2024-12-31
```

### 3. 模拟交易
在聚宽平台创建策略并开启模拟交易

## 策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_positions` | 10 | 最大持仓股票数量 |
| `min_value_score` | 70 | 最低价值评分阈值 |
| `position_size` | 0.1 | 单只股票仓位比例 |
| `stop_loss` | 0.15 | 止损比例 |
| `take_profit` | 0.30 | 止盈比例 |

## 投资框架说明

### 邱国鹭四要素应用
1. **估值**: PE/PB/PEG等指标评估
2. **品质**: ROE/毛利率/现金流质量
3. **时机**: 市场情绪+政策导向+技术信号
4. **仓位**: 根据确定性动态调整

### 李杰能力圈理论应用
1. **好生意**: 行业前景+商业模式
2. **好公司**: 管理层+治理结构+护城河
3. **好价格**: 安全边际+估值水平

## 依赖

- Python 3.8+
- jqdata (聚宽数据API)
- pandas, numpy
- OpenClaw skills (stock-analyzer, finance-news, duckduckgo)

## 作者

zhaokera

## 许可证

MIT License