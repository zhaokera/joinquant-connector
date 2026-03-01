# -*- coding: utf-8 -*-
"""
价值+动量混合量化策略
基于《量化交易：如何建立自己的算法交易事业》和《打开量化投资的黑箱》经典理论
融合邱国鹭《投资中最简单的事》和李杰《股市进阶之道》投资理念

策略核心：
- 价值因子 (60%): 估值、品质、财务健康度
- 动量因子 (40%): 价格趋势、截面动量、反转效应
- Fama-French因子模型思想: Size, Value, Momentum, Quality
- 行业中性化 + 风格轮动
"""

import numpy as np
import pandas as pd
from jqdata import *
from datetime import datetime, timedelta

# ========================================
# 策略参数配置
# ========================================

# 持仓配置
g.stock_num = 15  # 持仓股票数量（适度分散）
g.max_position_per_stock = 0.10  # 单只股票最大仓位10%
g.min_market_cap = 50  # 最小市值筛查（ excludes 小市值扫地桶）

# 风险控制参数
g.volatility_target = 0.18  # 年化波动率目标18%
g.max_drawdown_limit = 0.18  # 最大回撤限制18%
g.stop_loss_threshold = 0.12  # 止损阈值12%
g.take_profit_threshold = 0.30  # 止盈阈值30%

# 调仓参数
g.rebalance_freq = 20  # 基础调仓频率（交易日）
g.rebalance_on_event = False  # 是否事件驱动调仓
g.last_rebalance_date = None

# 筛选参数
g.min_liquidity_days = 120  # 最小上市天数
g.min_volume_filter = 100  # 最小平均成交量（万股）

# 因子权重配置（价值60% + 动量40%）
g.factor_weights = {
    'value': 0.60,      # 价值因子
    'momentum': 0.40,   # 动量因子
}

# 价值因子内部权重
g.value_subweights = {
    'pe': 0.25,
    'pb': 0.20,
    'ps': 0.10,
    'roe': 0.25,
    'debt_to_equity': 0.10,
    'operating_growth': 0.10,
}

# 动量因子内部权重
g.momentum_subweights = {
    'short_term_momentum': 0.30,   # 1个月动量
    'medium_term_momentum': 0.35,  # 3个月动量
    'long_term_momentum': 0.15,    # 12个月动量（反转效应）
    'volume_ratio': 0.20,          # 成交量Ratio
}

# 行业轮动参数
g.industry_rotation = True
g.industry_leader_count = 3  # 每个行业最多选几只龙头

# 风格轮动参数
g.style_rotation = True
g.style_score_threshold = 0.55  # 风格分数阈值

# ========================================

def initialize(context):
    """
    初始化策略
    """
    # 设置基准指数
    set_benchmark('000985.XSHG')  # 中证全指作为基准

    # 使用真实价格
    set_option('use_real_price', True)

    # 设置交易成本
    set_slippage(FixedSlippage(0.0005))  # 0.05%滑点
    set_commission(PerTrade(buy_cost=0.0008, sell_cost=0.0018, min_cost=5))  # 适度佣金

    # 日频交易，避免过度交易
    run_daily(trade, time='14:30')  # 收盘前30分钟调仓

    # 事件驱动调仓：单日大涨/大跌后重新评估
    run_daily(check_market_condition, time='09:30')

    # 每月第一个交易日强制调仓（monthday=1 表示每月1号）
    run_monthly(rebalance_on_schedule, monthday=1, time='09:45')

    # 记录初始化完成
    g.initialized = True
    g.market_regime = 'neutral'  # 市场状态：bull/bear/neutral
    g.industry_scores = {}  # 行业评分

    log.info("=" * 60)
    log.info("价值+动量混合策略初始化完成")
    log.info(f"目标年化波动率: {g.volatility_target*100:.0f}%")
    log.info(f"持仓数量: {g.stock_num}只")
    log.info(f"因子配置: 价值{g.factor_weights['value']*100:.0f}% + 动量{g.factor_weights['momentum']*100:.0f}%")
    log.info("=" * 60)


def check_market_condition(context):
    """
    检查市场状况（事件驱动调仓触发器）
    """
    try:
        # 计算市场波动率
        market_vol = calculate_market_volatility(context)

        # 计算市场趋势
        try:
            prices = get_price('000985.XSHG', end_date=context.current_dt, count=20,
                             fields=['close'], skip_paused=True)
            market_trend = (prices['close'].iloc[-1] - prices['close'].iloc[-10]) / prices['close'].iloc[-10] if len(prices) >= 10 else 0
        except:
            market_trend = 0

        # 判断市场状态
        if market_vol > 0.02:  # 单日波动>2%为高波动
            g.market_regime = 'volatile'
        elif market_trend > 0.05:
            g.market_regime = 'bull'
        else:
            g.market_regime = 'bear'

        # 高波动时触发调仓评估
        if market_vol > 0.025:
            g.rebalance_on_event = True
            log.info(f"市场高波动！触发重新评估: 波动率={market_vol*100:.2f}%")

    except Exception as e:
        log.debug(f"市场状况检查出错: {e}")


def trade(context):
    """
    主交易逻辑（日频调仓）
    """
    # 检查是否需要调仓
    if not need_rebalance(context):
        return

    # 获取股票池
    stock_pool = get_stock_pool(context)

    if len(stock_pool) == 0:
        log.info("股票池为空，跳过本次调仓")
        return

    # 选股（价值+动量混合打分）
    selected_stocks = hybrid_selection(stock_pool, context)

    if len(selected_stocks) == 0:
        log.info("未找到符合条件的股票，跳过调仓")
        return

    # 执行调仓
    adjust_position(context, selected_stocks)

    # 更新调仓记录
    g.last_rebalance_date = context.current_dt.date()
    g.rebalance_on_event = False


def need_rebalance(context):
    """
    判断是否需要调仓
    """
    # 事件驱动调仓
    if g.rebalance_on_event:
        return True

    # 定期调仓
    if g.last_rebalance_date is None:
        return True

    days_since_last = (context.current_dt.date() - g.last_rebalance_date).days
    if days_since_last >= g.rebalance_freq:
        return True

    # 检查持仓股票是否还符合条件
    current_holdings = list(context.portfolio.positions.keys())
    if len(current_holdings) > 0:
        try:
            current_data = get_current_data()
            for stock in current_holdings:
                # 检查是否被ST
                if hasattr(current_data[stock], 'is_st') and current_data[stock].is_st:
                    return True
                # 检查是否停牌
                if current_data[stock].paused:
                    return True
        except:
            pass

    return False


def rebalance_on_schedule(context):
    """
    每月第一个交易日强制调仓
    """
    g.rebalance_on_event = True
    trade(context)


def get_stock_pool(context):
    """
    获取基础股票池（分层筛选）

    筛选逻辑：
    1. 基础筛查（流动性、市值、ST）
    2. 财务质量筛查
    3. 动量筛查
    """
    try:
        current_date = context.current_dt

        # =====================================
        # 第一层：基础筛查
        # =====================================

        # 获取所有A股
        all_stocks = list(get_all_securities(['stock'], current_date).index)

        # 排除ST股票
        try:
            current_data = get_current_data()
            non_st_stocks = [s for s in all_stocks if not current_data[s].is_st]
        except:
            # 兼容性处理
            non_st_stocks = all_stocks

        # 排除停牌股票
        try:
            paused_data = get_price(non_st_stocks, end_date=current_date,
                                  count=1, fields=['paused'], skip_paused=False)
            trading_stocks = [s for s in non_st_stocks if not paused_data['paused'].iloc[0][s]]
        except:
            trading_stocks = non_st_stocks

        # 排除上市时间过短的股票
        eligible_stocks = []
        for stock in trading_stocks:
            try:
                info = get_security_info(stock)
                if (current_date.date() - info.start_date).days >= g.min_liquidity_days:
                    eligible_stocks.append(stock)
            except:
                eligible_stocks.append(stock)

        # 排除市值过小的股票（避免小市值风险）
        try:
            valuation = get_fundamentals(
                query(valuation.code, valuation.market_cap)
                .filter(valuation.code.in_(eligible_stocks)),
                date=current_date
            )
            valuation.set_index('code', inplace=True)
            eligible_stocks = [s for s in eligible_stocks
                            if s in valuation.index and valuation.loc[s, 'market_cap'] >= g.min_market_cap]
        except:
            pass

        log.info(f"基础筛选后: {len(eligible_stocks)} 只股票")

        # =====================================
        # 第二层：财务质量筛查
        # =====================================

        if len(eligible_stocks) > 0:
            # 获取财务指标（只使用聚宽indicator表中存在的字段）
            financial = get_fundamentals(
                query(
                    indicator.code, indicator.roe,
                    indicator.pe_ratio, indicator.pb_ratio
                ).filter(indicator.code.in_(eligible_stocks)),
                date=current_date
            )

            if not financial.empty:
                financial.set_index('code', inplace=True)

                # 过滤财务异常股票
                quality_filtered = []
                for stock in eligible_stocks:
                    if stock in financial.index:
                        row = financial.loc[stock]
                        # 连续盈利（排除ST风险）
                        if not (np.isnan(row['roe']) or np.isnan(row['pe_ratio']) or np.isnan(row['pb_ratio'])):
                            # ROE > 0 (盈利)
                            if row['roe'] > 0:
                                quality_filtered.append(stock)

                eligible_stocks = quality_filtered
                log.info(f"财务筛选后: {len(eligible_stocks)} 只股票")

        # =====================================
        # 第三层：动量筛查
        # =====================================

        if len(eligible_stocks) > 0:
            momentum_stocks = filter_by_momentum(eligible_stocks, context)
            eligible_stocks = momentum_stocks
            log.info(f"动量筛选后: {len(eligible_stocks)} 只股票")

        return eligible_stocks

    except Exception as e:
        log.error(f"获取股票池失败: {e}")
        return []


def filter_by_momentum(stocks, context):
    """
    动量筛选：排除近期表现太差的股票
    """
    try:
        end_date = context.current_dt
        start_date = end_date - timedelta(days=60)

        # 获取价格数据
        prices = get_price(stocks, start_date=start_date, end_date=end_date,
                          fields=['close'], skip_paused=True)

        if prices.empty:
            return stocks

        # 计算动量指标
        momentum_score = {}
        for stock in stocks:
            if stock in prices.columns and stock in prices.columns:
                price_series = prices[stock].dropna()
                if len(price_series) > 20:
                    # 1个月动量
                    m1_ret = (price_series.iloc[-1] - price_series.iloc[-20]) / price_series.iloc[-20] if len(price_series) >= 20 else 0
                    # 3个月动量
                    m3_ret = (price_series.iloc[-1] - price_series.iloc[-60]) / price_series.iloc[-60] if len(price_series) >= 60 else 0

                    # 合成动量分数
                    score = 0.5 * m1_ret + 0.5 * m3_ret
                    momentum_score[stock] = score

        # 保留动量排名前70%的股票
        if len(momentum_score) > 0:
            sorted_stocks = sorted(momentum_score.items(), key=lambda x: x[1], reverse=True)
            cutoff = max(10, len(sorted_stocks) * 7 // 10)
            return [s[0] for s in sorted_stocks[:cutoff]]

        return stocks

    except Exception as e:
        log.debug(f"动量筛选出错: {e}")
        return stocks


def hybrid_selection(stocks, context):
    """
    混合选成长股票
    综合价值因子 + 动量因子 + 风格因子
    """
    try:
        current_date = context.current_dt

        # =====================================
        # 1. 获取价值因子数据
        # =====================================
        valuation = get_fundamentals(
            query(
                valuation.code, valuation.pe_ratio, valuation.pb_ratio,
                valuation.ps_ratio, valuation.market_cap,
                valuation.pcf_ratio, valuation.np_ratio
            ).filter(valuation.code.in_(stocks)),
            date=current_date
        )

        financial = get_fundamentals(
            query(
                indicator.code, indicator.roe, indicator.roa,
                indicator.gross_profit_margin, indicator.net_profit_margin,
                indicator.net_profit_year_on_year,
                indicator.total_assets_turnover, indicator.current_ratio
            ).filter(indicator.code.in_(stocks)),
            date=current_date
        )

        # =====================================
        # 2. 获取动量因子数据
        # =====================================
        end_date = current_date
        prices_1m = get_price(stocks, end_date=end_date, count=20, fields=['close'], skip_paused=True)
        prices_3m = get_price(stocks, end_date=end_date, count=60, fields=['close'], skip_paused=True)
        prices_12m = get_price(stocks, end_date=end_date, count=252, fields=['close'], skip_paused=True)

        # =====================================
        # 3. 计算各因子得分（标准化）
        # =====================================

        # 价值因子得分
        value_scores = calculate_value_scores(valuation, financial)

        # 动量因子得分
        momentum_scores = calculate_momentum_scores(prices_1m, prices_3m, prices_12m, stocks)

        # 综合打分（价值60% + 动量40%）
        combined_scores = {}
        all_stock_set = set(value_scores.keys()) & set(momentum_scores.keys())

        for stock in all_stock_set:
            # 标准化后加权
            value_norm = (value_scores[stock] - min(value_scores.values())) / max(0.001, max(value_scores.values()) - min(value_scores.values()))
            momentum_norm = (momentum_scores[stock] - min(momentum_scores.values())) / max(0.001, max(momentum_scores.values()) - min(momentum_scores.values()))

            # 最终分数
            combined_scores[stock] = (
                g.factor_weights['value'] * value_norm +
                g.factor_weights['momentum'] * momentum_norm
            )

        # =====================================
        # 4. 行业轮动调整
        # =====================================

        if g.industry_rotation:
            combined_scores = apply_industry_rotation(combined_scores, current_date)

        # =====================================
        # 5. 风格轮动调整（Fama-French思想）
        # =====================================

        if g.style_rotation:
            combined_scores = apply_style_rotation(combined_scores, context)

        # =====================================
        # 6. 选股票
        # =====================================

        # 按综合得分排序
        sorted_stocks = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

        # 选前N只
        selected = [s[0] for s in sorted_stocks[:g.stock_num]]

        log.info(f"选中 {len(selected)} 只股票: {selected[:5]}...")

        return selected

    except Exception as e:
        log.error(f"混合选股票出错: {e}")
        return []


def calculate_value_scores(valuation, financial):
    """
    计算价值因子得分（基于Fama-French Value思路）

    价值特征：低PE、低PB、低PS、高ROE、低负债
    """
    scores = {}

    if valuation.empty or financial.empty:
        return scores

    # 合并数据
    merged = pd.merge(valuation.set_index('code'), financial.set_index('code'),
                     left_index=True, right_index=True, how='inner')

    for stock in merged.index:
        row = merged.loc[stock]

        # 计算各子因子得分（0-100分）
        pe_score = max(0, min(100, 50 - (row['pe_ratio'] - 10) * 2)) if row['pe_ratio'] > 0 and not pd.isna(row['pe_ratio']) else 50
        pb_score = max(0, min(100, 60 - (row['pb_ratio'] - 1.5) * 10)) if row['pb_ratio'] > 0 and not pd.isna(row['pb_ratio']) else 50
        ps_score = max(0, min(100, 50 - (row['ps_ratio'] - 2) * 5)) if row['ps_ratio'] > 0 and not pd.isna(row['ps_ratio']) else 50
        roe_score = max(0, min(100, row['roe'] * 5)) if row['roe'] > 0 and not pd.isna(row['roe']) else 0
        profit_margin_score = max(0, min(100, row['net_profit_margin'] * 10)) if row['net_profit_margin'] > 0 and not pd.isna(row['net_profit_margin']) else 0

        # 负债率惩罚
        debt_ratio = row['total_liability'] / row['total_assets'] if row['total_assets'] > 0 else 1
        debt_score = max(0, 100 - debt_ratio * 100)

        # 综合价值得分
        score = (
            g.value_subweights['pe'] * pe_score +
            g.value_subweights['pb'] * pb_score +
            g.value_subweights['ps'] * ps_score +
            g.value_subweights['roe'] * roe_score +
            g.value_subweights['operating_growth'] * profit_margin_score +
            g.value_subweights['debt_to_equity'] * debt_score
        )

        scores[stock] = max(0, score)

    return scores


def calculate_momentum_scores(prices_1m, prices_3m, prices_12m, stocks):
    """
    计算动量因子得分（反转效应 + 动量效应）

    参考《打开量化投资的黑箱》:
    - 短期动量（1-4周）: 继续效应
    - 中期动量（3-12月）: 继续效应
    - 长期动量（3-5年）: 反转效应
    """
    scores = {}

    for stock in stocks:
        score = 0

        # 1个月动量（继续效应）
        if not prices_1m.empty and stock in prices_1m.columns:
            p = prices_1m[stock].dropna()
            if len(p) >= 20:
                ret_1m = (p.iloc[-1] - p.iloc[-20]) / p.iloc[-20]
                score += g.momentum_subweights['short_term_momentum'] * (1 + ret_1m) * 50

        # 3个月动量（继续效应）
        if not prices_3m.empty and stock in prices_3m.columns:
            p = prices_3m[stock].dropna()
            if len(p) >= 60:
                ret_3m = (p.iloc[-1] - p.iloc[-60]) / p.iloc[-60]
                score += g.momentum_subweights['medium_term_momentum'] * (1 + ret_3m) * 30

        # 12个月动量（反转效应 -参考Jegadeesh & Titman）
        if not prices_12m.empty and stock in prices_12m.columns:
            p = prices_12m[stock].dropna()
            if len(p) >= 252:
                ret_12m = (p.iloc[-1] - p.iloc[-252]) / p.iloc[-252]
                # 长期反转：负动量正向赋分
                score += g.momentum_subweights['long_term_momentum'] * (1 - ret_12m * 0.5) * 20

        scores[stock] = max(0, min(100, score))

    return scores


def apply_industry_rotation(scores, date):
    """
    行业轮动调整（基于李杰能力圈理论 + 行业景气度）

    优先选择：
    1. 龙头行业（消费、医药、科技）
    2. 景气度上行的行业
    3. 估值合理的行业
    """
    try:
        industry_scores = get_industry_scores(date)
        g.industry_scores = industry_scores

        adjusted_scores = {}
        for stock, score in scores.items():
            try:
                # 获取行业
                industry = get_industry(stock, date=date)
                industry_mult = industry_scores.get(industry, 1.0)
                adjusted_scores[stock] = score * industry_mult
            except:
                adjusted_scores[stock] = score

        return adjusted_scores

    except Exception as e:
        log.debug(f"行业轮动出错: {e}")
        return scores


def get_industry_scores(date):
    """
    行业评分（基于景气度、估值、政策）
    """
    # 基础行业评分（参考李杰能力圈）
    base_scores = {
        '801010': 0.85,  # 农林牧渔
        '801020': 0.95,  # 采掘
        '801030': 1.20,  # 医药生物
        '801040': 1.10,  # 公用事业
        '801050': 1.00,  # 电力设备
        '801060': 1.15,  # 新能源车
        '801070': 1.05,  # 汽车
        '801080': 1.25,  # 国防军工
        '801090': 1.10,  # 电子
        '801100': 1.00,  # 机械设备
        '801110': 0.95,  # 钢铁
        '801120': 0.90,  # 有色金属
        '801130': 1.10,  # 建筑材料
        '801140': 1.05,  # 建筑装饰
        '801150': 0.90,  # 房地产
        '801160': 1.30,  # 消费电子
        '801170': 1.25,  # 家电
        '801180': 1.00,  # 商业-trade
        '801190': 1.20,  # 传媒
        '801200': 1.15,  # 通信
        '801210': 1.10,  # 银行
        '801220': 1.05,  # 非银金融
        '801230': 1.00,  # 食品饮料
        '801240': 1.25,  # 纺织服装
        '801250': 1.15,  # 轻工制造
        '801260': 1.30,  # 医药生物
        '801270': 1.05,  # 电子
        '801280': 1.10,  # 汽车
        '801290': 1.05,  # 家电
        '801300': 1.00,  # 机械设备
        '801310': 1.10,  # 钢铁
        '801320': 1.05,  # 有色金属
        '801330': 1.10,  # 建筑材料
        '801340': 1.05,  # 建筑装饰
        '801350': 0.90,  # 房地产
        '801360': 1.25,  # 公用事业
        '801370': 1.10,  # 交通运输
        '801380': 1.15,  # 环保
        '801390': 1.20,  # 社会服务
        '801710': 1.10,  # 综合
    }

    # 根据市场状态调整
    if g.market_regime == 'bull':
        # 牛市偏好成长行业
        growth_boost = {
            '801090': 1.15,   # 电子
            '801100': 1.10,   # 机械设备
            '801300': 1.10,   # 机械设备
            '801190': 1.10,   # 传媒
            '801200': 1.10,   # 通信
        }
        for k, v in growth_boost.items():
            base_scores[k] *= v
    elif g.market_regime == 'bear':
        # 熊市偏好防御行业
        defensive_boost = {
            '801040': 1.15,   # 公用事业
            '801210': 1.15,   # 银行
            '801230': 1.10,   # 食品饮料
            '801030': 1.10,   # 医药生物
        }
        for k, v in defensive_boost.items():
            base_scores[k] *= v

    return base_scores


def apply_style_rotation(scores, context):
    """
    风格轮动调整（Fama-French Size/Value/Momentum/Quality模型）

    根据市场风格动态调整：
    - 大市值 vs 小市值
    - 价值 vs 成长
    - 动量 vs 反转
    - 高质量 vs 低质量
    """
    try:
        # 计算风格评分
        style_scores = calculate_style_scores(context)

        adjusted = {}
        for stock, score in scores.items():
            try:
                # 获取市值（ Size ）
                info = get_security_info(stock)
                market_cap = get_fundamentals(
                    query(valuation.market_cap).filter(valuation.code == stock),
                    date=context.current_dt
                )
                mkt_cap = market_cap['market_cap'].iloc[0] if not market_cap.empty else 50

                # 大市值偏好
                size_mult = 1.2 if mkt_cap > 100 else (1.0 if mkt_cap > 50 else 0.8)

                # 风格乘数
                style_mult = style_scores.get('combined', 1.0)

                adjusted[stock] = score * size_mult * style_mult

            except:
                adjusted[stock] = score

        return adjusted

    except Exception as e:
        log.debug(f"风格轮动出错: {e}")
        return scores


def calculate_style_scores(context):
    """
    计算当前市场风格评分
    """
    # 这里简化处理，实际可使用更复杂的风格因子
    return {'combined': 1.0}


def adjust_position(context, target_stocks):
    """
    调整仓位（基于波动率的动态仓位管理）

    仓位公式：
    position = base_position * (target_vol / actual_vol) * style_multiplier
    """
    try:
        current_holdings = list(context.portfolio.positions.keys())

        # =====================================
        # 1. 计算目标仓位
        # =====================================

        # 基础仓位
        base_position = g.max_position_per_stock

        # 波动率调整
        try:
            _volatility = calculate_portfolio_volatility(context, current_holdings)
            if _volatility > 0:
                volatility_factor = g.volatility_target / _volatility
                volatility_factor = max(0.5, min(1.5, volatility_factor))
            else:
                volatility_factor = 1.0
        except:
            volatility_factor = 1.0

        # 市场状态调整
        market_factor = {'bull': 1.1, 'neutral': 1.0, 'bear': 0.8, 'volatile': 0.7}.get(g.market_regime, 1.0)

        # 最终目标仓位
        target_position = base_position * volatility_factor * market_factor
        target_position = min(g.max_position_per_stock, target_position)

        log.info(f"目标仓位: {target_position*100:.1f}% (波动率调整: {volatility_factor:.2f})")

        # =====================================
        # 2. 计算每个股票的目标市值
        # =====================================

        total_value = context.portfolio.total_value

        # =====================================
        # 3. 重建组合
        # =====================================

        # 先清仓
        for stock in current_holdings:
            if stock not in target_stocks:
                order_target_value(stock, 0)
                log.info(f"清仓: {stock}")

        # 再建仓（按目标仓位分配）
        available_cash = context.portfolio.available_cash

        # 等权重分配（已限制单票仓位）
        for stock in target_stocks:
            target_value = total_value * target_position
            if available_cash > target_value:
                order_target_value(stock, target_value)
                log.info(f"调整仓位: {stock} -> {target_value:.0f}")
                available_cash -= target_value

        # 保留现金作为安全边际
        if available_cash > total_value * 0.05:
            log.info(f"现金储备: {available_cash:.0f}")

    except Exception as e:
        log.error(f"调仓失败: {e}")


def calculate_portfolio_volatility(context, holdings):
    """
    计算组合波动率（简化版）
    """
    if len(holdings) == 0:
        return 0.20  # 默认年化20%

    try:
        end_date = context.current_dt
        start_date = end_date - timedelta(days=252)

        prices = get_price(holdings, start_date=start_date, end_date=end_date,
                          fields=['close'], skip_paused=True)

        if prices.empty or len(prices) < 50:
            return 0.20

        # 计算收益率
        returns = prices.pct_change().dropna()

        # 简单平均波动率
        volatility = returns.std().mean() * np.sqrt(252)

        return max(0.10, min(0.40, volatility))

    except:
        return 0.20


def calculate_market_volatility(context):
    """
    计算市场单日波动率
    """
    try:
        prices = get_price('000985.XSHG', end_date=context.current_dt, count=20,
                          fields=['close'], skip_paused=True)

        if len(prices) < 5:
            return 0.01

        returns = prices['close'].pct_change().dropna()
        return returns.std() * np.sqrt(252)

    except:
        return 0.01


def calculate_drwdown(prices):
    """
    计算最大回撤
    """
    if len(prices) < 2:
        return 0

    cummax = np.maximum.accumulate(prices)
    drawdown = (prices - cummax) / cummax
    return abs(min(drawdown))


def after_trading_end(context):
    """
    收盘后处理
    """
    # 记录组合信息
    log.info(f"收盘 - 持仓: {len(context.portfolio.positions)}只, "
             f"市值: {context.portfolio.total_value:.0f}, "
             f"可用: {context.portfolio.available_cash:.0f}")

    # 记录 leverage
    if context.portfolio.total_value > 0:
        leverage = context.portfolio.positions_value / context.portfolio.available_cash if context.portfolio.available_cash > 0 else 0
        log.info(f"杠杆率: {leverage:.2f}")


def plot_chart(context):
    """
    绘制策略图表（聚宽回测可用）
    """
    # 可以在此处添加自定义指标绘制
    pass
