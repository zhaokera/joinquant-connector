# Skill: joinquant-connector

## 描述
聚宽(JoinQuant)量化交易平台对接器，基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》的投资理念构建量化策略。

## 权限
- bash
- python
- web_fetch
- web_search

## 功能

### 1. 价值投资策略
- 基于邱国鹭四要素（估值、品质、时机、仓位）的量化选股
- 结合李杰能力圈理论的行业轮动
- 投资价值智能分级系统

### 2. 策略回测
- 历史数据回测验证
- 风险控制参数优化
- 绩效指标分析

### 3. 模拟交易
- 实时市场模拟交易
- 自动化交易信号生成
- 仓位管理和风险控制

### 4. 数据集成
- 对接股票分析器技能
- 集成财经新闻技能
- 多源数据融合分析

## 使用示例

```
# 策略回测
skill: joinquant-connector
action: backtest
strategy: value_investing
start_date: 2023-01-01
end_date: 2024-12-31
initial_capital: 1000000

# 模拟交易
skill: joinquant-connector  
action: simulate
strategy: value_investing
capital: 1000000
frequency: daily

# 获取交易信号
skill: joinquant-connector
action: get_signals
stocks: sh600000,sz000001
analysis_type: value_investing
```

## 输出格式

### 回测结果
```json
{
  "strategy": "value_investing",
  "period": "2023-01-01 to 2024-12-31",
  "initial_capital": 1000000,
  "final_value": 1250000,
  "total_return": 0.25,
  "sharpe_ratio": 1.2,
  "max_drawdown": 0.15,
  "win_rate": 0.65,
  "trades": 45
}
```

### 交易信号
```json
{
  "timestamp": "2024-01-15 14:30:00",
  "signals": [
    {
      "symbol": "sh600000",
      "action": "buy",
      "price": 10.50,
      "reason": "估值合理，品质优秀，政策支持",
      "confidence": 0.85
    }
  ]
}
```

## 依赖说明

需要安装聚宽本地开发环境：
```bash
pip install -r requirements.txt
```

或者直接在聚宽平台使用在线策略。

## 投资理念集成

### 邱国鹭四要素量化
- **估值**: PE/PB/ROE等财务指标
- **品质**: 护城河、竞争优势、管理层
- **时机**: 市场情绪、政策导向、资金流向  
- **仓位**: 风险分散、动态调整

### 李杰能力圈理论
- **好生意**: 商业模式、护城河
- **好公司**: 管理层、治理结构
- **好价格**: 安全边际、估值水平

## 注意事项

1. **模拟交易不等于实盘**：心理压力和流动性差异
2. **策略需要持续优化**：市场环境变化需要调整参数
3. **风险控制优先**：设置止损和仓位限制
4. **合规要求**：遵守A股交易规则和监管要求