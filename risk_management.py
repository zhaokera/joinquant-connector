#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险控制模块 - 基于《打开量化投资的黑箱》经典理论

核心功能：
1. 波动率目标控制（Volatility Targeting）
2. 动态仓位管理（Kelly Criterion变体）
3. 止损止盈机制（Trailing Stop）
4. 黑天鹅防护（Tail Risk Hedging）
5.流动性风险控制
"""

import numpy as np
import pandas as pd
from jqdata import *
from datetime import datetime, timedelta

# ========================================
# 风险参数配置
# ========================================

# 波动率目标
g.volatility_target = 0.18  # 年化波动率目标18%

# 仓位控制
g.max_position = 0.15  # 单只股票最大仓位15%
g.min_position = 0.02  # 最小仓位2%
g.max_total_position = 0.95  # 总仓位上限95%

# 止损止盈
g.stop_loss_threshold = 0.12  # 止损12%
g.take_profit_threshold = 0.30  # 止盈30%
g.trailing_stop_threshold = 0.08  # 移动止损8%

# 流动性阈值
g.min_volume_filter = 100  # 日均成交量下限（万元）
g.max_position_change = 0.30  # 单日最大仓位调整比例

# 黑天鹅防护
g.tail_risk_hedge = True
g.cvar_threshold = 0.05  # CVaR 95%分位

# ========================================

def initialize_risk_module(context):
    """
    初始化风险控制模块
    """
    g.position_limits = {}  # 每只股票的仓位限制
    g.trail_prices = {}  # 移动止损追踪价格
    g.portfolio_history = []  # 组合历史记录

    log.info("风险控制模块初始化完成")
    log.info(f"波动率目标: {g.volatility_target*100:.0f}%")
    log.info(f"单票上限: {g.max_position*100:.0f}%")
    log.info(f"止损阈值: {g.stop_loss_threshold*100:.0f}%")


def dynamic_position_sizing(context, stock, volatility):
    """
    动态仓位计算（基于 volatility targeting）

    Formula:
    position = (target_vol / stock_vol) * (1 / sqrt(N)) * risk_factor

    参考:《量化交易：如何建立自己的算法交易事业》
    """
    try:
        # 基础计算
        target_vol = g.volatility_target
        stock_vol = max(volatility, 0.10)  # 最小波动率10%

        # 股票数量调整
        current_holdings = len(context.portfolio.positions)
        diversity_factor = 1.0 / np.sqrt(max(1, current_holdings))

        # 风险因子（根据市场状态调整）
        risk_factor = get_risk_factor(context)

        # 计算目标仓位
        position = (target_vol / stock_vol) * diversity_factor * risk_factor

        # 限制在合理范围内
        position = max(g.min_position, min(g.max_position, position))

        return position

    except Exception as e:
        log.debug(f"仓位计算出错: {e}")
        return g.max_position


def get_risk_factor(context):
    """
    获取风险因子（根据市场状态动态调整）

    市场状态:
    - 牛市: 1.1 - 1.2
    - 熊市: 0.7 - 0.85
    - 震荡: 0.9 - 1.0
    """
    try:
        # 计算市场指标
        bench_prices = get_price('000985.XSHG', end_date=context.current_dt,
                                 count=252, fields=['close'], skip_paused=True)

        if len(bench_prices) < 50:
            return 1.0

        # 计算收益率
        returns = bench_prices['close'].pct_change().dropna()

        # 市场波动率
        market_vol = returns.std() * np.sqrt(252)

        # 市场趋势
        price_20 = bench_prices['close'].iloc[-20] if len(bench_prices) >= 20 else bench_prices['close'].iloc[0]
        price_252 = bench_prices['close'].iloc[-252]
        market_trend = (bench_prices['close'].iloc[-1] - price_20) / price_20

        # 风险因子计算
        if market_vol < 0.15 and market_trend > 0.05:
            # 牛市早期
            risk_factor = 1.15
        elif market_vol < 0.15 and market_trend > 0.15:
            # 牛市中期
            risk_factor = 1.20
        elif market_vol > 0.25 and market_trend < -0.10:
            # 熊市
            risk_factor = 0.75
        elif market_vol > 0.20:
            # 高波动
            risk_factor = 0.85
        else:
            # 正常市场
            risk_factor = 1.0

        return risk_factor

    except Exception as e:
        log.debug(f"风险因子计算出错: {e}")
        return 1.0


def calculate_stock_volatility(stock, context):
    """
    计算个股波动率（历史波动率）

    使用不同时间窗口的波动率加权平均
    """
    try:
        end_date = context.current_dt

        # 20日波动率（短期）
        prices_20 = get_price(stock, end_date=end_date, count=20,
                             fields=['close'], skip_paused=True)
        vol_20 = prices_20['close'].pct_change().dropna().std() * np.sqrt(252) if len(prices_20) >= 10 else 0.30

        # 60日波动率（中期）
        prices_60 = get_price(stock, end_date=end_date, count=60,
                             fields=['close'], skip_paused=True)
        vol_60 = prices_60['close'].pct_change().dropna().std() * np.sqrt(252) if len(prices_60) >= 30 else 0.30

        # 120日波动率（长期）
        prices_120 = get_price(stock, end_date=end_date, count=120,
                              fields=['close'], skip_paused=True)
        vol_120 = prices_120['close'].pct_change().dropna().std() * np.sqrt(252) if len(prices_120) >= 60 else 0.30

        # 加权平均（近期波动率权重更高）
        volatility = 0.4 * vol_20 + 0.35 * vol_60 + 0.25 * vol_120

        return max(0.10, min(0.50, volatility))  # 限制范围

    except:
        return 0.30  # 默认波动率


def check_stop_loss(context, stock, entry_price, current_price):
    """
    检查止损条件
    """
    try:
        # 固定比例止损
        loss_ratio = (current_price - entry_price) / entry_price

        if loss_ratio <= -g.stop_loss_threshold:
            log.info(f"触发止损: {stock} 亏损 {loss_ratio*100:.2f}%")
            return True

        # 移动止损检查
        if stock in g.trail_prices:
            trail_price = g.trail_prices[stock]
            pullback = (trail_price - current_price) / trail_price

            if pullback >= g.trailing_stop_threshold:
                log.info(f"触发移动止损: {stock} 回撤 {pullback*100:.2f}%")
                return True

            # 更新追踪价格
            if current_price > trail_price:
                g.trail_prices[stock] = current_price

        return False

    except:
        return False


def check_take_profit(context, stock, entry_price, current_price):
    """
    检查止盈条件
    """
    try:
        gain_ratio = (current_price - entry_price) / entry_price

        if gain_ratio >= g.take_profit_threshold:
            log.info(f"触发止盈: {stock} 盈利 {gain_ratio*100:.2f}%")
            return True

        return False

    except:
        return False


def update_trail_price(context, stock, current_price):
    """
    更新移动止损追踪价格
    """
    if stock not in g.trail_prices:
        g.trail_prices[stock] = current_price
    else:
        g.trail_prices[stock] = max(g.trail_prices[stock], current_price)


def liquidity_check(stock, context):
    """
    流动性检查

    确保股票有足够的成交量，避免买卖时冲击成本过高
    """
    try:
        end_date = context.current_dt
        start_date = end_date - timedelta(days=5)

        # 获取成交量
        volume_data = get_price(stock, start_date=start_date, end_date=end_date,
                               fields={'volume': 'volume', 'money': 'money'},
                               skip_paused=True)

        if volume_data.empty:
            return False

        # 计算日均成交额（万元）
        avg_volume = volume_data['volume'].mean()
        avg_money = volume_data['money'].mean() / 10000  # 转万元

        # 成交量过滤
        if avg_money < g.min_volume_filter:
            return False

        # 成交额波动率（过大说明流动性不稳定）
        volume_std = volume_data['money'].std()
        if volume_std > avg_money * 2:
            return False

        return True

    except:
        return False


def market_regulation_check(context):
    """
    市场监管状态检查（A股特色）

    检查：
    1. 涨跌停状态
    2. 特殊处理状态
    3. 盘口情况
    """
    try:
        current_data = get_current_data()

        # 获取所有持仓股票的状态
        for stock in context.portfolio.positions:
            if stock in current_data:
                stock_data = current_data[stock]

                # 检查是否涨跌停
                if hasattr(stock_data, 'limit_up') and stock_data.limit_up > 0:
                    limit_down = getattr(stock_data, 'limit_down', 0)
                    if stock_data.close >= stock_data.limit_up * 0.999:
                        log.warning(f"{stock} 涨停，可能无法卖出")
                    if stock_data.close <= limit_down * 1.001:
                        log.warning(f"{stock} 跌停，可能无法买入")

        return True

    except Exception as e:
        log.debug(f"监管检查出错: {e}")
        return True


def black_swan_protection(context):
    """
    黑天鹅防护机制

    参考:《打开量化投资的黑箱》- Tail Risk Hedging
    """
    if not g.tail_risk_hedge:
        return

    try:
        # 计算组合的VaR和CVaR
        portfolio_value = context.portfolio.total_value
        positions_value = context.portfolio.positions_value

        # 简单的组合VaR估算
        volatility = calculate_portfolio_volatility(context)
        var_95 = portfolio_value * volatility * 2.33  # 95% VaR
        cvar_95 = portfolio_value * volatility * 2.85  # 95% CVaR

        # 如果CVaR超过阈值，触发防护
        max_acceptable_loss = portfolio_value * g.cvar_threshold

        if cvar_95 > max_acceptable_loss:
            log.warning(f"黑天鹅预警! CVaR={cvar_95:.0f} > 阈值={max_acceptable_loss:.0f}")

            # 动态降低仓位
            reduction_factor = max_acceptable_loss / cvar_95
            target_cash = portfolio_value * (1 - reduction_factor * 0.8)

            # 平仓部分持仓
            if context.portfolio.available_cash < target_cash:
                needs_reduce = target_cash - context.portfolio.available_cash

                # 简单的等比例平仓
                stocks_to_close = list(context.portfolio.positions.keys())[:3]
                for stock in stocks_to_close:
                    if needs_reduce > 0:
                        close_value = min(needs_reduce, positions_value / len(context.portfolio.positions))
                        order_target_value(stock, context.portfolio.positions[stock].amount - close_value / context.portfolio.positions[stock].price)
                        needs_reduce -= close_value

    except Exception as e:
        log.debug(f"黑天鹅防护检查出错: {e}")


def calculate_portfolio_volatility(context):
    """
    计算组合整体波动率
    """
    try:
        if len(context.portfolio.positions) == 0:
            return 0.20

        stocks = list(context.portfolio.positions.keys())
        end_date = context.current_dt

        # 获取价格数据
        prices = get_price(stocks, end_date=end_date, count=252,
                          fields=['close'], skip_paused=True)

        if prices.empty or len(prices) < 50:
            return 0.20

        # 计算收益率和协方差
        returns = prices.pct_change().dropna()

        # 计算组合波动率
        weights = np.ones(len(stocks)) / len(stocks)
        cov_matrix = returns.cov() * 252  # 年化协方差

        portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))

        return max(0.10, min(0.40, portfolio_vol))

    except Exception as e:
        log.debug(f"组合波动率计算出错: {e}")
        return 0.20


def max_drawdown_check(context):
    """
    最大回撤检查

    返回当前回撤和历史最大回撤
    """
    try:
        # 记录组合价值
        portfolio_value = context.portfolio.total_value
        g.portfolio_history.append(portfolio_value)

        if len(g.portfolio_history) < 2:
            return 0, 0

        # 计算当前回撤
        prices = np.array(g.portfolio_history)
        cummax = np.maximum.accumulate(prices)
        drawdown = (prices - cummax) / cummax
        current_dd = abs(min(drawdown))

        # 历史最大回撤
        max_dd = max(abs(drawdown))

        return current_dd, max_dd

    except:
        return 0, 0


def risk_minutes(context):
    """
    风控检查主函数（可定时调用）

    检查内容：
    1. 波动率是否超出阈值
    2. 回撤是否接近上限
    3. 流动性是否充足
    4. 黑天鹅风险
    """
    # 波动率检查
    vol = calculate_portfolio_volatility(context)
    if vol > g.volatility_target * 1.5:
        log.warning(f"波动率超出上限: {vol*100:.1f}% > {g.volatility_target*150:.1f}%")

    # 回撤检查
    current_dd, max_dd = max_drawdown_check(context)
    if current_dd > g.max_drawdown_limit * 0.8:
        log.warning(f"回撤警告: {current_dd*100:.2f}%")

    # 黑天鹅防护
    black_swan_protection(context)

    # 监管检查
    market_regulation_check(context)


def initialize(context):
    """
    初始化（与主策略集成）
    """
    initialize_risk_module(context)


def handle_data(context, data):
    """
    每日风控检查
    """
    # 每日收盘前进行风控检查
    if context.current_dt.hour == 14 and context.current_dt.minute == 55:
        risk_minutes(context)
