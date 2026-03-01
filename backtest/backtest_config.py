#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽回测配置文件 - 价值+动量混合策略

参考经典理论：
1. 《量化交易：如何建立自己的算法交易事业》- Grinold & Kahn
2. 《打开量化投资的黑箱》- systematicallystructured
3. Fama-French因子模型
4. 邱国鹭《投资中最简单的事》- 四要素框架
5. 李杰《股市进阶之道》- 能力圈理论

策略目标：
- 年化收益率: 25%+
- 最大回撤: <20%
- 夏普比率: >1.0
- 波动率: 15-20%
"""

# ========================================
# 回测基础配置
# ========================================

BACKTEST_CONFIG = {
    # 时间范围（建议至少3年，覆盖完整市场周期）
    "start_date": "2021-01-01",      # 开始日期
    "end_date": "2026-12-31",        # 结束日期
    "benchmark": "000985.XSHG",      # 中证全指 - 更全面的市场基准

    # 资金配置
    "capital_base": 1000000,         # 初始资金100万
    "frequency": "daily",            # 日频交易

    # 交易成本（A股实际水平）
    "commission": 0.0008,            # 买卖佣金万分之八
    "slippage": 0.001,               # 滑点千分之一
    "use_real_price": True,          # 使用真实价格
}

# ========================================
# 风险控制参数
# ========================================

RISK_CONTROL = {
    # 仓位控制
    "max_position_per_stock": 0.15,   # 单只股票最大仓位15%
    "min_position_per_stock": 0.02,   # 最小仓位2%
    "max_total_position": 0.95,       # 最大总仓位95%
    "max_holdings": 20,               # 最大持仓股票数

    # 波动率目标
    "volatility_target": 0.18,        # 年化波动率目标18%

    # 止损止盈
    "stop_loss_threshold": 0.12,      # 止损12%
    "take_profit_threshold": 0.30,    # 止盈30%
    "trailing_stop_threshold": 0.08,  # 移动止损8%

    # 回撤控制
    "max_drawdown_limit": 0.18,       # 最大回撤限制18%

    # 流动性要求
    "min_daily_volume": 100,          # 最小日均成交额（万元）
}

# ========================================
# 投资策略参数
# ========================================

# 1. 因子权重配置（价值+动量混合）
FACTOR_WEIGHTS = {
    # 核心：价值60% + 动量40%
    "value": 0.60,
    "momentum": 0.40,

    # 价值因子内部权重（邱国鹭四要素）
    "value_subweights": {
        "pe": 0.25,              # 估值 - PE
        "pb": 0.20,              # 估值 - PB
        "ps": 0.10,              # 估值 - PS
        "roe": 0.25,             # 品质 - ROE
        "debt_to_equity": 0.10,  # 品质 - 负债率
        "operating_growth": 0.10, # 品质 - 营收增长
    },

    # 动量因子内部权重
    "momentum_subweights": {
        "short_term_momentum": 0.30,   # 1个月动量（继续效应）
        "medium_term_momentum": 0.35,  # 3个月动量（继续效应）
        "long_term_momentum": 0.15,    # 12个月动量（反转效应）
        "volume_ratio": 0.20,          # 成交量Ratio
    },
}

# 2. 价值投资筛选参数（邱国鹭四要素优化）
VALUE_INVESTING_PARAMS = {
    "valuation": {
        # 估值水平（更宽松的阈值以扩大选股范围）
        "pe_max": 35,           # PE不超过35倍（原30）
        "pb_max": 3.5,          # PB不超过3.5倍（原3）
        "ps_max": 5,            # PS不超过5倍
        "peg_max": 1.8,         # PEG不超过1.8
        "dividend_yield_min": 0.01, # 股息率不低于1%
    },

    "quality": {
        # 品质要求（基于李杰能力圈）
        "roe_min": 0.08,        # ROE不低于8%（原15%，更宽松）
        "roe_stable_years": 3,  # ROE稳定3年以上
        "gross_margin_min": 0.20, # 毛利率不低于20%（原30%）
        "net_profit_margin_min": 0.05, # 净利率不低于5%
        "operating_growth_min": 0.05,  # 营收增长率不低于5%
        "net_profit_growth_min": 0.05, # 净利润增长率不低于5%
    },

    "financial_health": {
        # 财务健康度
        "debt_to_assets_max": 0.75,   # 资产负债率不超过75%
        "current_ratio_min": 1.0,     # 流动比率不低于1
        "quick_ratio_min": 0.8,       # 速动比率不低于0.8
        "interest_coverage_min": 2,   # 利息保障倍数不低于2
    },

    "timing": {
        # 时机判断
        "market_pe_threshold": 28,    # 市场PE阈值
        "pbv_threshold": 1.2,         # 市净率阈值
        "sentiment_score_min": 0.55,  # 市场情绪分数
    },

    "position": {
        # 仓位管理
        "industry_concentration_max": 0.4,  # 行业集中度不超过40%
        "cash_reserve_min": 0.05,           # 现金储备不低于5%
        "cash_reserve_max": 0.20,           # 现金储备不超过20%
    }
}

# 3. 李杰能力圈理论参数优化
LI_JIE_PARAMS = {
    # 商业模式评分（1-10分）
    "business_model_score_min": 6,        # 降低要求以扩大范围
    "business_model_thresholds": {
        "high": 8,   # 优秀：强护城河
        "medium": 6, # 良好：一定护城河
        "low": 4,    # 一般：护城河较弱
    },

    # 管理层质量评分
    "management_quality_score_min": 6,
    "management_quality_thresholds": {
        "high": 8,
        "medium": 6,
        "low": 4,
    },

    # 竞争优势评分
    "competitive_advantage_score_min": 6,
    "competitive_advantage_thresholds": {
        "high": 8,
        "medium": 6,
        "low": 4,
    },

    # 能力圈行业（扩展版）
    "circle_of_competence": [
        "消费", "医药", "科技", "金融", "制造",
        "新能源", "环保", "国防", "TMT", "新材料"
    ],

    # 行业护城河强度
    "industry_moat_strength": {
        "消费": 0.25,      # 强护城河
        "医药": 0.20,      # 强护城河
        "科技": 0.15,      # 技术护城河
        "新能源": 0.15,    # 政策护城河
        "军工": 0.18,      # 政策护城河
        "金融": 0.12,      # 牌照护城河
        "制造": 0.08,      # 成本护城河
        "环保": 0.10,      # 政策护城河
    }
}

# 4. 技术分析参数
TECHNICAL_PARAMS = {
    # 均线系统
    "ma_periods": [5, 10, 20, 60, 120, 250],  # 多周期均线

    # MACD
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,

    # RSI
    "rsi_period": 14,
    "rsi_overbought": 75,  # 放宽超买线（原70）
    "rsi_oversold": 25,    # 放宽超卖线（原30）

    # KD
    "kdj_period": 9,
    "kdj_overbought": 85,  # 放宽超买线
    "kdj_oversold": 15,    # 放宽超卖线

    # 成交量
    "volume_ma_period": 5,
    "volume_multiplier": 1.3,  # 成交量放大倍数

    # 布林带
    "boll_period": 20,
    "boll_multiplier": 2,

    # ATR（波动率）
    "atr_period": 14,
}

# ========================================
# 行业轮动参数
# ========================================

INDUSTRY_ROTATION_PARAMS = {
    # 行业评分权重
    "brightness_weight": 0.35,     # 景气度
    "valuation_weight": 0.25,      # 估值
    "momentum_weight": 0.25,       # 动量
    "policy_weight": 0.15,         # 政策

    # 行业数量
    "max_industries": 5,           # 最多投资行业数
    "max_stocks_per_industry": 4,  # 每行业最多股票数

    # 行业暴露限制
    "industry_exposure_max": 0.30,  # 单行业最大暴露30%
    "industry_exposure_min": 0.05,  # 单行业最小暴露5%

    # 行业调整频率
    "rebalance_freq_days": 20,     # 20天调整一次
}

# ========================================
# 风格轮动参数（Fama-French扩展）
# ========================================

STYLE_ROTATION_PARAMS = {
    # 风格评分阈值
    "size_threshold": 0.55,     # 大小盘切换阈值
    "value_threshold": 0.55,    # 价值成长切换阈值
    "momentum_threshold": 0.55, # 动量反转切换阈值
    "quality_threshold": 0.55,  # 质量风格切换阈值

    # 风格暴露限制
    "size_exposure_max": 0.70,   # 大盘风格最大70%
    "value_exposure_max": 0.70,  # 价值风格最大70%

    # 风格scores计算
    "size_scores": {
        "large_cap_weight": 0.60,  # 大市值股票权重
        "mid_cap_weight": 0.30,    # 中市值股票权重
        "small_cap_weight": 0.10,  # 小市值股票权重
    },
}

# ========================================
# 头寸规模控制（Kelly Criterion变体）
# ========================================

POSITION_SIZING_PARAMS = {
    # 基础仓位
    "base_position": 0.10,           # 基础仓位10%

    # 波动率调整
    "volatility_adjustment": True,   # 启用波动率调整
    "target_volatility": 0.18,       # 目标波动率18%
    "volatility_floor": 0.10,        # 波动率下限
    "volatility_ceiling": 0.40,      # 波动率上限

    # 市场状态调整
    "market_regime_adjustment": True,
    "bull_multiplier": 1.15,         # 牛市加仓
    "bear_multiplier": 0.85,         # 熊市减仓
    "volatile_multiplier": 0.80,     # 高波动减仓

    # 分散化调整
    "diversification_adjustment": True,
    "min_holdings": 8,               # 最小持仓数
    "max_holdings": 20,              # 最大持仓数

    # 黑天鹅防护
    "tail_risk_hedge": True,         # 启用尾部风险防护
    "cvar_threshold": 0.05,          # CVaR 95%分位
    "max_loss_allowable": 0.15,      # 最大可接受损失
}

# ========================================
# 交易成本优化参数
# ========================================

TRANSACTION_COST_PARAMS = {
    # 调仓频率控制
    "min_rebalance_days": 15,        # 最小调仓间隔
    "rebalance_on_event": True,      # 事件驱动调仓

    # 成交成本监控
    "max_slippage": 0.0015,          # 最大可接受滑点
    "max_commission_rate": 0.0015,   # 最大可接受佣金率

    # 流动性管理
    "position_turnover_limit": 0.5,  # 单日最大换手率50%
    "daily_volume_limit": 0.10,      # 单日最大成交额占比10%

    # 批量交易
    "batch_trade_enabled": True,     # 启用批量交易
    "max_batch_size": 10,            # 批量交易最大数量
}

# ========================================
# 市场周期判断参数
# ========================================

MARKET_REGIME_PARAMS = {
    # 周期阶段阈值
    "recovery_volatility_max": 0.18,     # 复苏期：波动率<18%
    "recovery_trend_min": 0.05,          # 复苏期：趋势>5%
    "recovery_momentum_min": 0,          # 复苏期：12个月动量>0

    " overheating_volatility_max": 0.22, # 过热期：波动率<22%
    " overheating_trend_min": 0.08,      # 过热期：趋势>8%
    " overheating_inflation_signal": 1,  # 过热期：通胀信号

    "stagnation_volatility_min": 0.22,   # 滞胀期：波动率>22%
    "stagnation_trend_max": 0.02,        # 滞胀期：趋势<2%
    "stagnation_inflation_signal": 1,    # 滞胀期：通胀信号

    "recession_volatility_min": 0.25,    # 衰退期：波动率>25%
    "recession_trend_max": -0.10,        # 衰退期：趋势<-10%
    "recession_policy_signal": 1,        # 衰退期：政策宽松信号

    # 周期信号来源
    "benchmark":"",
    "inflation_proxy": "CPI",
    "policy_proxy": "monetary_policy",
}

# ========================================
# 性能目标
# ========================================

PERFORMANCE_GOALS = {
    # 收益目标
    "target_annual_return": 0.25,      # 年化收益率25%
    "targetMonthly_return": 0.02,      # 月均收益率2%

    # 风险目标
    "target_volatility": 0.18,         # 年化波动率18%
    "max_drawdown_target": 0.18,       # 最大回撤18%
    "var_95_target": 0.12,             # 95% VaR 12%

    # 风险调整收益
    "target_sharpe_ratio": 1.0,        # 夏普比率1.0+
    "target_sortino_ratio": 1.5,       # 索提诺比率1.5+
    "target_calibration_ratio": 1.2,   # 卡尔玛比率1.2+

    # 交易效率
    "win_rate_target": 0.55,           # 胜率55%
    "profit_loss_ratio": 1.8,          # 盈亏比1.8:1
}

# ========================================
# 回测建议
# ========================================

BACKTEST_RECOMMENDATIONS = """
## 回测设置建议

### 1. 时间范围
- 最短：2021-2023（覆盖完整牛熊周期）
- 推荐：2020-2026（5年+，包含2022熊市）
- 长期：2018-2026（8年，验证长期有效性）

### 2. 基准选择
- 中证全指（000985.XSHG）：最全面的市场基准
- 沪深300（000300.XSHG）：大盘风格基准
- 创业板指（399006.XSHE）：成长风格对比

### 3. 费用设置
- 佣金：万分之八（含印花税）
- 滑点：千分之一
- 资金成本：年化4%（可选）

### 4. 回测频率
- 日频：适合价值+动量策略
- 避免高频：防止过度拟合和交易成本过高

### 5. 输出指标
- 绝对收益：累计收益率
- 相对收益：超额收益（vs benchmark）
- 风险指标：波动率、最大回撤、夏普比率
- 交易指标：胜率、盈亏比、换手率

## 参数调优建议

### 1. 保守版本
- value_weight: 0.70, momentum_weight: 0.30
- stock_num: 10
- stop_loss: 0.10
- volatility_target: 0.15

### 2. 平衡版本（默认）
- value_weight: 0.60, momentum_weight: 0.40
- stock_num: 15-20
- stop_loss: 0.12
- volatility_target: 0.18

### 3. 激进版本
- value_weight: 0.50, momentum_weight: 0.50
- stock_num: 25-30
- stop_loss: 0.15
- volatility_target: 0.22
"""

# ========================================
# 作者说明
# ========================================

AUTHOR_NOTES = """
## 策略设计思想

本策略融合了经典量化理论和价值投资理念：

### 1. 理论基础
- **Grinold & Kahn** (《量化交易》)：主动比率、信息比率
- **Fama-French** (多因子模型)：价值、规模、动量、质量
- **Jegadeesh & Titman** (动量策略)：截面动量效应
- **邱国鹭** (《投资中最简单的事》)：四要素框架
- **李杰** (《股市进阶之道》)：能力圈理论

### 2. 策略特色
- 价值60% + 动量40%的混合打分系统
- 动态仓位管理（波动率targeting）
- 行业轮动 + 风格轮动双轮动机制
- A股特色适配（T+1、涨跌停、政策驱动）

### 3. 风险控制
- 波动率目标控制
- 最大回撤限制
- 止损止盈机制
- 流动性过滤
- 黑天鹅防护

## 免责声明
回测结果不代表未来收益。市场有风险，投资需谨慎。
"""
