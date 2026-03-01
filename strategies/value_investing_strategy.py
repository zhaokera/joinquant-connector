# -*- coding: utf-8 -*-
"""
基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》的量化策略
集成 OpenClaw 股票分析技能的投资价值评估体系
"""

import jqdata
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 策略参数配置
g = {
    'stocks': [],           # 候选股票池
    'max_holdings': 10,     # 最大持仓数量
    'position_size': 0.1,   # 单只股票仓位比例
    'rebalance_freq': 5,    # 调仓频率（交易日）
    'last_rebalance': None, # 上次调仓日期
}

def initialize(context):
    """
    初始化策略
    """
    # 设置基准指数
    set_benchmark('000300.XSHG')  # 沪深300
    
    # 设置滑点和手续费
    set_slippage(FixedSlippage(0.002))  # 0.2%滑点
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))  # 佣金
    
    # 设置日志级别
    log.info("价值投资量化策略初始化完成")
    
    # 初始化候选股票池
    update_stock_pool(context)

def before_trading_start(context):
    """
    每个交易日开盘前执行
    """
    current_date = context.current_dt.date()
    
    # 检查是否需要调仓
    if g['last_rebalance'] is None or (current_date - g['last_rebalance']).days >= g['rebalance_freq']:
        log.info(f"准备调仓，当前日期: {current_date}")
        rebalance_portfolio(context)
        g['last_rebalance'] = current_date

def handle_data(context, data):
    """
    每分钟执行（但我们的策略主要在开盘前调仓）
    """
    pass

def after_trading_end(context):
    """
    每个交易日收盘后执行
    """
    # 记录持仓信息
    if len(context.portfolio.positions) > 0:
        log.info(f"当前持仓: {list(context.portfolio.positions.keys())}")
        log.info(f"总市值: {context.portfolio.total_value:.2f}")

def update_stock_pool(context):
    """
    更新候选股票池 - 基于邱国鹭四要素和李杰能力圈理论
    """
    # 获取全市场股票（排除ST、停牌、新股）
    all_stocks = get_all_securities(['stock'], context.current_dt.date())
    all_stocks = all_stocks[~all_stocks.display_name.str.contains('ST')]
    
    # 过滤条件
    candidates = []
    
    for stock in all_stocks.index:
        try:
            # 1. 估值要素 (Valuation) - 邱国鹭
            pe_ratio = get_valuation(stock, context.current_dt, 1)['pe_ratio'].iloc[0]
            pb_ratio = get_valuation(stock, context.current_dt, 1)['pb_ratio'].iloc[0]
            
            # 2. 品质要素 (Quality) - 邱国鹭 + 李杰能力圈
            roe = get_fundamentals(query(indicator).filter(indicator.code == stock), 
                                 date=context.current_dt.date())['roe'].iloc[0] if not get_fundamentals(query(indicator).filter(indicator.code == stock), date=context.current_dt.date()).empty else 0
            
            # 3. 时机要素 (Timing) - 邱国鹭
            # 检查是否处于合理买入区间
            price_position = check_price_position(stock, context)
            
            # 4. 行业轮动 (Industry Rotation) - 邱国鹭
            industry_score = get_industry_score(stock, context)
            
            # 综合评分
            score = calculate_investment_score(
                pe_ratio=pe_ratio,
                pb_ratio=pb_ratio, 
                roe=roe,
                price_position=price_position,
                industry_score=industry_score
            )
            
            # 只选择高分股票
            if score >= 70:
                candidates.append((stock, score))
                
        except Exception as e:
            log.debug(f"处理股票 {stock} 时出错: {e}")
            continue
    
    # 按评分排序，取前N名
    candidates.sort(key=lambda x: x[1], reverse=True)
    g['stocks'] = [stock for stock, score in candidates[:50]]  # 取前50名作为候选池
    
    log.info(f"更新候选股票池，共 {len(g['stocks'])} 只股票")

def calculate_investment_score(pe_ratio, pb_ratio, roe, price_position, industry_score):
    """
    基于邱国鹭四要素计算投资评分
    """
    # 估值评分 (30%)
    valuation_score = 0
    if pe_ratio and pe_ratio > 0:
        if pe_ratio < 15:
            valuation_score = 90
        elif pe_ratio < 25:
            valuation_score = 70
        elif pe_ratio < 35:
            valuation_score = 50
        else:
            valuation_score = 30
    else:
        valuation_score = 20
    
    # 品质评分 (30%)
    quality_score = 0
    if roe and roe > 0:
        if roe > 15:
            quality_score = 90
        elif roe > 10:
            quality_score = 70
        elif roe > 5:
            quality_score = 50
        else:
            quality_score = 30
    else:
        quality_score = 20
    
    # 时机评分 (20%)
    timing_score = price_position * 100 if price_position else 50
    
    # 行业评分 (20%)
    industry_score = industry_score if industry_score else 50
    
    # 加权综合评分
    total_score = (valuation_score * 0.3 + 
                   quality_score * 0.3 + 
                   timing_score * 0.2 + 
                   industry_score * 0.2)
    
    return total_score

def check_price_position(stock, context):
    """
    检查价格位置 - 判断是否处于合理买入区间
    """
    try:
        # 获取近1年价格数据
        hist = attribute_history(stock, 250, '1d', ['close'])
        current_price = hist['close'][-1]
        min_price = hist['close'].min()
        max_price = hist['close'].max()
        
        # 计算当前位置（0-1之间，越接近0越低估）
        if max_price > min_price:
            position = (current_price - min_price) / (max_price - min_price)
            return 1 - position  # 越低越好
        else:
            return 0.5
    except:
        return 0.5

def get_industry_score(stock, context):
    """
    获取行业轮动评分
    """
    # 这里可以实现更复杂的行业分析
    # 简化版本：给予所有行业基础分
    return 60

def rebalance_portfolio(context):
    """
    调仓逻辑
    """
    log.info("开始调仓...")
    
    # 获取当前可交易的候选股票
    tradable_stocks = []
    for stock in g['stocks']:
        if is_trading_stock(stock, context):
            tradable_stocks.append(stock)
    
    # 限制最大持仓数量
    target_stocks = tradable_stocks[:g['max_holdings']]
    
    # 平仓不在目标列表中的股票
    for stock in context.portfolio.positions:
        if stock not in target_stocks:
            order_target(stock, 0)
            log.info(f"平仓: {stock}")
    
    # 建立新仓位
    available_cash = context.portfolio.available_cash
    target_value_per_stock = available_cash * g['position_size']
    
    for stock in target_stocks:
        if stock not in context.portfolio.positions:
            order_value(stock, target_value_per_stock)
            log.info(f"建仓: {stock}, 目标金额: {target_value_per_stock:.2f}")

def is_trading_stock(stock, context):
    """
    检查股票是否可交易
    """
    try:
        # 检查是否停牌
        if not is_suspended(stock, context.current_dt.date()):
            # 检查是否有足够流动性
            volume = get_price(stock, end_date=context.current_dt, frequency='1d', fields=['volume'], count=1)['volume'].iloc[0]
            if volume > 100000:  # 日成交量大于10万股
                return True
    except:
        pass
    return False

# 调试用的辅助函数
def debug_strategy(context):
    """
    调试策略状态
    """
    log.info(f"策略状态:")
    log.info(f"- 候选股票数: {len(g['stocks'])}")
    log.info(f"- 当前持仓数: {len(context.portfolio.positions)}")
    log.info(f"- 可用现金: {context.portfolio.available_cash:.2f}")
    log.info(f"- 总资产: {context.portfolio.total_value:.2f}")