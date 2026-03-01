# -*- coding: utf-8 -*-
"""
价值投资量化策略 - 基于邱国鹭《投资中最简单的事》和李杰《股市进阶之道》
聚宽(JoinQuant)平台专用版本
"""

import numpy as np
import pandas as pd
from jqdata import *

# 策略参数配置
g.stock_num = 10  # 持仓股票数量
g.check_out_lists = ['check_for_suspend', 'check_for_delist']  # 风控检查

def initialize(context):
    """
    初始化策略
    """
    set_benchmark('000300.XSHG')  # 沪深300作为基准
    set_option('use_real_price', True)  # 使用真实价格

    # 设置交易成本（order_style已废弃，按股下单）
    set_slippage(FixedSlippage(0.0005))  # 滑点
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))  # 手续费
    
    # 日级别调仓
    run_daily(trade, time='14:50')
    
    log.info("价值投资量化策略初始化完成")

def trade(context):
    """
    交易逻辑主函数
    """
    # 获取当前可交易股票池
    stock_pool = get_stock_pool(context)
    
    if len(stock_pool) == 0:
        log.info("股票池为空，跳过本次调仓")
        return
    
    # 基于价值投资理念筛选股票
    selected_stocks = value_investing_selection(stock_pool, context.current_dt)
    
    if len(selected_stocks) == 0:
        log.info("未找到符合价值投资标准的股票，跳过本次调仓")
        return
    
    # 执行调仓
    adjust_position(context, selected_stocks)

def get_stock_pool(context):
    """
    获取基础股票池
    """
    # 获取所有A股（排除ST、停牌等）
    all_stocks = list(get_all_securities(['stock'], context.current_dt).index)
    
    # 过滤条件
    filtered_stocks = []
    for stock in all_stocks:
        # 排除ST股票
        if is_st_stock(stock, context.current_dt):
            continue
        # 排除停牌股票
        if is_suspended(stock, context.current_dt):
            continue
        # 排除上市时间小于60天的股票
        if (context.current_dt.date() - get_security_info(stock).start_date).days < 60:
            continue
            
        filtered_stocks.append(stock)
    
    return filtered_stocks

def is_st_stock(stock, date):
    """
    判断是否为ST股票
    """
    try:
        name = get_security_info(stock).display_name
        if 'ST' in name or '*ST' in name:
            return True
    except:
        pass
    return False

def is_suspended(stock, date):
    """
    判断是否停牌
    """
    try:
        current_data = get_current_data()
        return current_data[stock].paused
    except:
        return True

def value_investing_selection(stock_pool, date):
    """
    基于邱国鹭四要素的价值投资选股
    """
    if len(stock_pool) == 0:
        return []
    
    try:
        # 1. 估值分析 (邱国鹭四要素之一)
        valuation_df = get_valuation_data(stock_pool, date)
        if valuation_df is None or valuation_df.empty:
            log.debug("估值数据获取失败")
            return []
        
        # 2. 基本面分析 (邱国鹭四要素之二)
        financial_df = get_financial_data(stock_pool, date)
        if financial_df is None or financial_df.empty:
            log.debug("财务数据获取失败")
            return []
        
        # 合并数据
        merged_df = pd.merge(valuation_df, financial_df, on='code', how='inner')
        if merged_df.empty:
            return []
        
        # 3. 应用价值投资筛选条件
        selected_stocks = apply_value_investing_filters(merged_df, date)
        
        # 4. 基于李杰能力圈理论排序
        ranked_stocks = rank_by_circle_of_competence(selected_stocks, date)
        
        # 返回前N只股票
        return ranked_stocks[:g.stock_num]
        
    except Exception as e:
        log.debug(f"选股过程出错: {e}")
        return []

def get_valuation_data(stock_list, date):
    """
    获取估值数据 - 聚宽正确API
    """
    try:
        # 查询估值指标
        q = query(
            valuation.code,
            valuation.pe_ratio,
            valuation.pb_ratio,
            valuation.ps_ratio,
            valuation.market_cap
        ).filter(
            valuation.code.in_(stock_list)
        )
        
        df = get_fundamentals(q, date=date)
        return df
        
    except Exception as e:
        log.debug(f"获取估值数据失败: {e}")
        return None

def get_financial_data(stock_list, date):
    """
    获取财务数据 - 聚宽正确API
    """
    try:
        # 查询财务指标
        q = query(
            indicator.code,
            indicator.roe,
            indicator.inc_revenue_year_on_year,
            indicator.inc_net_profit_year_on_year,
            indicator.gross_profit_margin,
            indicator.net_profit_margin,
            indicator.total_assets,
            indicator.total_liability,
            indicator.equity
        ).filter(
            indicator.code.in_(stock_list)
        )
        
        df = get_fundamentals(q, date=date)
        return df
        
    except Exception as e:
        log.debug(f"获取财务数据失败: {e}")
        return None

def apply_value_investing_filters(df, date):
    """
    应用邱国鹭价值投资四要素筛选
    """
    filtered_stocks = []
    
    for idx, row in df.iterrows():
        score = 0
        reasons = []
        
        # 1. 估值要素 (权重30%)
        pe = row.get('pe_ratio', np.inf)
        pb = row.get('pb_ratio', np.inf)
        
        if pe < 20 and not np.isnan(pe):
            score += 30
            reasons.append("低PE")
        if pb < 2.0 and not np.isnan(pb):
            score += 20
            reasons.append("低PB")
            
        # 2. 品质要素 (权重30%)
        roe = row.get('roe', 0)
        revenue_growth = row.get('inc_revenue_year_on_year', 0)
        profit_growth = row.get('inc_net_profit_year_on_year', 0)
        
        if roe > 10 and not np.isnan(roe):
            score += 30
            reasons.append("高ROE")
        if revenue_growth > 10 and not np.isnan(revenue_growth):
            score += 15
            reasons.append("收入增长")
        if profit_growth > 10 and not np.isnan(profit_growth):
            score += 15
            reasons.append("利润增长")
            
        # 3. 时机要素 (权重20%)
        # 这里简化处理，实际可以结合市场情绪、政策等
        market_score = 20  # 简化处理
        score += market_score
        
        # 4. 仓位要素 (权重20%)
        # 根据风险分散原则
        position_score = 20
        score += position_score
        
        # 综合评分阈值
        if score >= 60:
            filtered_stocks.append({
                'code': row['code'],
                'score': score,
                'reasons': reasons
            })
    
    # 按评分排序
    filtered_stocks.sort(key=lambda x: x['score'], reverse=True)
    return [stock['code'] for stock in filtered_stocks]

def rank_by_circle_of_competence(stocks, date):
    """
    基于李杰能力圈理论排序
    """
    # 简化实现：优先选择消费、医药、科技等护城河明显的行业
    industry_preference = {
        '801030': 1.2,  # 医药生物
        '801020': 1.1,  # 食品饮料  
        '801080': 1.1,  # 电子
        '801730': 1.0,  # 电力设备
        '801180': 0.9,  # 房地产
        '801760': 0.8,  # 国防军工
    }
    
    ranked_stocks = []
    for stock in stocks:
        try:
            # 获取行业信息
            industry_code = get_industry(stock, date=date)
            multiplier = industry_preference.get(industry_code, 1.0)
            ranked_stocks.append((stock, multiplier))
        except:
            ranked_stocks.append((stock, 1.0))
    
    # 按行业偏好排序
    ranked_stocks.sort(key=lambda x: x[1], reverse=True)
    return [stock[0] for stock in ranked_stocks]

def adjust_position(context, target_stocks):
    """
    调整持仓
    """
    # 获取当前持仓
    current_holdings = list(context.portfolio.positions.keys())
    
    # 卖出不在目标列表中的股票
    for stock in current_holdings:
        if stock not in target_stocks:
            order_target_value(stock, 0)
            log.info(f"卖出股票: {stock}")
    
    # 买入目标股票
    target_value = context.portfolio.available_cash / len(target_stocks)
    for stock in target_stocks:
        if stock not in current_holdings:
            order_target_value(stock, target_value)
            log.info(f"买入股票: {stock}")

def after_trading_end(context):
    """
    收盘后处理
    """
    log.info(f"当日持仓: {list(context.portfolio.positions.keys())}")
    log.info(f"可用资金: {context.portfolio.available_cash}")
    log.info(f"总资产: {context.portfolio.total_value}")