#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽回测配置文件
基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》的投资理念
"""

# 回测基础配置
BACKTEST_CONFIG = {
    "start_date": "2020-01-01",
    "end_date": "2026-12-31",
    "benchmark": "000300.XSHG",  # 沪深300
    "universe": "A股全市场",
    "capital_base": 1000000,  # 初始资金100万
    "commission": 0.0003,     # 佣金万分之三
    "slippage": 0.001,       # 滑点千分之一
    "frequency": "daily"      # 日频交易
}

# 风险控制参数
RISK_CONTROL = {
    "max_position": 0.3,      # 单只股票最大仓位30%
    "max_holdings": 10,       # 最大持仓股票数
    "stop_loss": -0.15,       # 止损线-15%
    "take_profit": 0.30,      # 止盈线30%
    "max_drawdown": -0.25     # 最大回撤控制25%
}

# 价值投资筛选参数（邱国鹭四要素）
VALUE_INVESTING_PARAMS = {
    "valuation": {
        "pe_max": 30,         # PE不超过30倍
        "pb_max": 3,          # PB不超过3倍
        "peg_max": 1.5        # PEG不超过1.5
    },
    "quality": {
        "roe_min": 0.15,      # ROE不低于15%
        "gross_margin_min": 0.3,  # 毛利率不低于30%
        "net_profit_growth_min": 0.1  # 净利润增长率不低于10%
    },
    "timing": {
        "market_pe_threshold": 25,    # 市场PE阈值
        "sentiment_score_min": 0.6    # 市场情绪分数
    },
    "position": {
        "industry_concentration_max": 0.4,  # 行业集中度不超过40%
        "cash_reserve_min": 0.1           # 现金储备不低于10%
    }
}

# 李杰能力圈理论参数
LI_JIE_PARAMS = {
    "business_model_score_min": 7,    # 商业模式评分不低于7分
    "management_quality_score_min": 7, # 管理层质量评分不低于7分
    "competitive_advantage_score_min": 7, # 竞争优势评分不低于7分
    "circle_of_competence": [
        "消费", "医药", "科技", "金融", "制造"
    ]  # 能力圈行业
}

# 技术分析参数
TECHNICAL_PARAMS = {
    "macd_signal": "golden_cross",    # MACD金叉
    "rsi_range": [30, 70],           # RSI超买超卖区间
    "ma_period": [20, 60],           # 均线周期
    "volume_multiplier": 1.5         # 成交量放大倍数
}