# -*- coding: utf-8 -*-
"""
行业轮动与风格轮动模块

基于理论：
1. 《量化交易：如何建立自己的算法交易事业》- 资产配置与再平衡
2. 《打开量化投资的黑箱》- 多因子模型
3. GICS行业分类 + 风格因子（Size, Value, Momentum, Quality）

核心功能：
- 行业景气度 tracking
- 风格轮动（大小盘、价值成长）
- 市场周期判断
- 风格中性化
"""

import numpy as np
import pandas as pd
from jqdata import *
from datetime import datetime, timedelta

# ========================================
# 行业分类配置（申万一级行业）
# ========================================

# 行业代码映射（申万一级行业）
SW1_CODES = {
    '801010.SI': '农林牧渔',
    '801020.SI': '采掘',
    '801030.SI': '医药生物',
    '801040.SI': '公用事业',
    '801050.SI': '电力设备',
    '801060.SI': '新能源车',
    '801070.SI': '汽车',
    '801080.SI': '国防军工',
    '801090.SI': '电子',
    '801100.SI': '机械设备',
    '801110.SI': '钢铁',
    '801120.SI': '有色金属',
    '801130.SI': '建筑材料',
    '801140.SI': '建筑装饰',
    '801150.SI': '房地产',
    '801160.SI': '商业贸易',
    '801170.SI': '家用电器',
    '801180.SI': '食品饮料',
    '801190.SI': '纺织服装',
    '801200.SI': '轻工制造',
    '801210.SI': '医药生物',
    '801220.SI': '电子',
    '801230.SI': '汽车',
    '801240.SI': '家用电器',
    '801250.SI': '机械设备',
    '801260.SI': '医药生物',
    '801270.SI': '电子',
    '801280.SI': '汽车',
    '801290.SI': '家用电器',
    '801300.SI': '机械设备',
    '801310.SI': '钢铁',
    '801320.SI': '有色金属',
    '801330.SI': '建筑材料',
    '801340.SI': '建筑装饰',
    '801350.SI': '房地产',
    '801360.SI': '公用事业',
    '801370.SI': '交通运输',
    '801380.SI': '环保',
    '801390.SI': '社会服务',
    '801710.SI': '综合',
}

# 行业属性配置
INDUSTRY_ATTR = {
    '消费': ['801180.SI', '801170.SI', '801230.SI', '801240.SI', '801250.SI', '801260.SI', '801270.SI', '801280.SI', '801290.SI', '801300.SI'],
    '成长': ['801090.SI', '801050.SI', '801060.SI', '801370.SI', '801380.SI'],
    '防御': ['801040.SI', '801210.SI', '801360.SI', '801390.SI'],
    '周期': ['801110.SI', '801120.SI', '801130.SI', '801140.SI', '801150.SI', '801330.SI', '801340.SI'],
}

# 基础行业评分（李杰能力圈理论）
# 评分依据：护城河厚度、行业集中度、毛利率水平
BASE_INDUSTRY_SCORE = {
    '801030.SI': 1.25,   # 医药生物 - 强护城河
    '801180.SI': 1.20,   # 食品饮料 - 经典消费
    '801090.SI': 1.15,   # 电子 - 技术驱动
    '801230.SI': 1.15,   # 汽车 - 成长行业
    '801240.SI': 1.10,   # 家用电器 - 品牌护城河
    '801050.SI': 1.10,   # 电力设备 - 新能源
    '801360.SI': 1.05,   # 公用事业 - 稳定现金流
    '801170.SI': 1.05,   # 家用电器 - 成熟行业
    '801210.SI': 1.05,   # 医药生物
    '801260.SI': 1.05,   # 医药生物
    '801270.SI': 1.05,   # 电子
    '801280.SI': 1.05,   # 汽车
    '801290.SI': 1.05,   # 家用电器
    '801300.SI': 1.05,   # 机械设备
    '801040.SI': 1.00,   # 公用事业
    '801370.SI': 1.00,   # 交通运输
    '801380.SI': 1.00,   # 环保
    '801390.SI': 1.00,   # 社会服务
    '801710.SI': 1.00,   # 综合
    '801020.SI': 0.95,   # 采掘 - 周期性
    '801110.SI': 0.95,   # 钢铁 - 周期性
    '801120.SI': 0.95,   # 有色金属 - 周期性
    '801130.SI': 0.95,   # 建筑材料 - 周期性
    '801140.SI': 0.95,   # 建筑装饰 - 周期性
    '801150.SI': 0.90,   # 房地产 - 高周期
    '801010.SI': 0.90,   # 农林牧渔 - 政策影响大
    '801060.SI': 0.95,   # 新能源车 - 政策驱动
    '801070.SI': 0.95,   # 汽车
    '801080.SI': 1.00,   # 国防军工 - 政策支持
    '801100.SI': 0.95,   # 机械设备
    '801200.SI': 0.90,   # 轻工制造
    '801190.SI': 0.90,   # 纺织服装
    '801160.SI': 0.90,   # 商业贸易
}

# ========================================

def get_industry_rotation_scores(context):
    """
    计算行业轮动评分

    评分维度：
    1. 宏观经济指标匹配
    2. 行业景气度
    3. 估值水平
    4. 政策导向
    """
    try:
        current_date = context.current_dt

        # 计算各行业指标
        industry_scores = {}

        for industry_code, industry_name in SW1_CODES.items():
            try:
                # 获取行业成分股
                industry_stocks = get_industry_stocks(industry_code, current_date)

                if len(industry_stocks) == 0:
                    continue

                # 1. 景气度评分
                brightness_score = calculate_industry_brightness(industry_stocks, current_date)

                # 2. 估值评分（低估值加分）
                valuation_score = calculate_industry_valuation(industry_stocks, current_date)

                # 3. 动量评分
                momentum_score = calculate_industry_momentum(industry_stocks, current_date)

                # 4. 政策评分（A股特色）
                policy_score = calculate_policy_score(industry_name, current_date)

                # 综合评分
                total_score = (
                    0.35 * brightness_score +
                    0.25 * valuation_score +
                    0.25 * momentum_score +
                    0.15 * policy_score
                )

                industry_scores[industry_code] = {
                    'score': total_score,
                    'brightness': brightness_score,
                    'valuation': valuation_score,
                    'momentum': momentum_score,
                    'policy': policy_score,
                    'name': industry_name
                }

            except Exception as e:
                log.debug(f"计算行业 {industry_name} 评分出错: {e}")
                continue

        # 排序行业
        sorted_industries = sorted(
            industry_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )

        return industry_scores, sorted_industries

    except Exception as e:
        log.error(f"行业轮动评分出错: {e}")
        return {}, []


def calculate_industry_brightness(stocks, date):
    """
    计算行业景气度
    """
    try:
        # 获取财务数据
        financial = get_fundamentals(
            query(
                indicator.code, indicator.operating_revenue_year_on_year,
                indicator.operating_profit_year_on_year,
                indicator.net_profit_year_on_year,
                indicator.roe
            ).filter(indicator.code.in_(stocks)),
            date=date
        )

        if financial.empty:
            return 50

        # 计算平均指标
        avg_revenue_growth = financial['operating_revenue_year_on_year'].mean()
        avg_profit_growth = financial['operating_profit_year_on_year'].mean()
        avg_roe = financial['roe'].mean()

        # 景气度评分（0-100）
        # 收入增长 > 20%: 100分
        # 收入增长 0-20%: 50-100分
        # 收入增长 < 0%: 0-50分
        revenue_score = min(100, max(0, (avg_revenue_growth + 20) * 2.5))

        # ROE > 15%: 100分
        roe_score = min(100, max(0, avg_roe * 6.67))

        return (revenue_score + roe_score) / 2

    except:
        return 50


def calculate_industry_valuation(stocks, date):
    """
    计算行业估值评分（低估值加分）
    """
    try:
        valuation = get_fundamentals(
            query(
                valuation.code, valuation.pe_ratio, valuation.pb_ratio
            ).filter(valuation.code.in_(stocks)),
            date=date
        )

        if valuation.empty:
            return 50

        # 计算中位数PE/PB
        pe_median = valuation['pe_ratio'].median()
        pb_median = valuation['pb_ratio'].median()

        # 评分（估值越低越好）
        # PE < 15: 100分, PE > 40: 0分
        pe_score = max(0, min(100, 100 - (pe_median - 15)))

        # PB < 2: 100分, PB > 5: 0分
        pb_score = max(0, min(100, 100 - (pb_median - 2) * 20))

        return (pe_score + pb_score) / 2

    except:
        return 50


def calculate_industry_momentum(stocks, date):
    """
    计算行业动量
    """
    try:
        end_date = date
        start_date = end_date - timedelta(days=90)

        prices = get_price(stocks, start_date=start_date, end_date=end_date,
                          fields=['close'], skip_paused=True)

        if prices.empty:
            return 50

        # 计算行业整体收益率
        industry_return = (prices.iloc[-1].mean() - prices.iloc[0].mean()) / prices.iloc[0].mean()

        # 动量评分（正收益加分）
        score = min(100, max(0, 50 + industry_return * 1000))

        return score

    except:
        return 50


def calculate_policy_score(industry_name, date):
    """
    计算政策评分（A股特色）

    关注政策支持的行业：
    - 新能源、半导体、人工智能
    - 医药医疗
    - 绿色环保
    - 国防军工
    """
    policy_boost = {
        '新能源': 1.15,
        '电力设备': 1.15,
        '电子': 1.10,
        '医药生物': 1.10,
        '国防军工': 1.10,
        '公用事业': 1.05,
        '环保': 1.15,
        '社会服务': 1.05,
    }

    for key, value in policy_boost.items():
        if key in industry_name:
            return 100 * value

    return 100


def get_style_scores(context):
    """
    计算当前市场风格评分

    风格维度（Fama-French扩展）：
    1. Size: 大市值 vs 小市值
    2. Value: 价值 vs 成长
    3. Momentum: 动量 vs 反转
    4. Quality: 高质量 vs 低质量
    """
    try:
        current_date = context.current_dt

        # 获取市场分组
        valuation = get_fundamentals(
            query(valuation.code, valuation.market_cap, valuation.pe_ratio, valuation.pb_ratio),
            date=current_date
        )

        if valuation.empty:
            return {'size': 0.5, 'value': 0.5, 'momentum': 0.5, 'quality': 0.5}

        # 计算各风格指标
        size_score = calculate_size_score(valuation)
        value_score = calculate_value_score(valuation)
        momentum_score = calculate_momentum_score(current_date)
        quality_score = calculate_quality_score(current_date)

        return {
            'size': size_score,
            'value': value_score,
            'momentum': momentum_score,
            'quality': quality_score,
            'combined': (size_score + value_score + momentum_score + quality_score) / 4
        }

    except Exception as e:
        log.debug(f"风格评分出错: {e}")
        return {'combined': 0.5}


def calculate_size_score(valuation):
    """
    计算大小盘风格
    """
    try:
        # 按市值分组
        median_cap = valuation['market_cap'].median()
        large_cap = valuation[valuation['market_cap'] >= median_cap]['market_cap'].mean()
        small_cap = valuation[valuation['market_cap'] < median_cap]['market_cap'].mean()

        # 大盘股相对强度
        prices = get_price(
            list(valuation[valuation['market_cap'] >= median_cap].head(50).index),
            end_date=context.current_dt, count=252, fields=['close'], skip_paused=True
        ) if len(valuation) > 50 else pd.DataFrame()

        small_prices = get_price(
            list(valuation[valuation['market_cap'] < median_cap].head(50).index),
            end_date=context.current_dt, count=252, fields=['close'], skip_paused=True
        ) if len(valuation) > 50 else pd.DataFrame()

        if not prices.empty and not small_prices.empty:
            large_return = (prices.iloc[-1].mean() - prices.iloc[0].mean()) / prices.iloc[0].mean()
            small_return = (small_prices.iloc[-1].mean() - small_prices.iloc[0].mean()) / small_prices.iloc[0].mean()

            # 大盘相对强度
            strength = (large_return - small_return + 0.2) / 0.4
            return max(0, min(1, strength))

        return 0.5

    except:
        return 0.5


def calculate_value_score(valuation):
    """
    计算价值成长风格
    """
    try:
        # 计算 Value Proxy (BP ratio)
        valuation['bp'] = 1 / valuation['pb_ratio']
        valuation['ep'] = 1 / valuation['pe_ratio']

        # 高BP组合 vs 低BP组合
        median_bp = valuation['bp'].median()
        high_bp_stocks = valuation[valuation['bp'] >= median_bp]
        low_bp_stocks = valuation[valuation['bp'] < median_bp]

        return 0.5 + (len(high_bp_stocks) - len(low_bp_stocks)) / len(valuation) * 0.2

    except:
        return 0.5


def calculate_momentum_score(date):
    """
    计算动量风格（参考Jegadeesh & Titman）
    """
    try:
        end_date = date
        start_date_1m = end_date - timedelta(days=1)
        start_date_12m = end_date - timedelta(days=252)

        # 获取所有股票
        stocks = list(get_all_securities(['stock'], end_date).index)

        # 1个月价格
        prices_1m = get_price(stocks, start_date=start_date_1m, end_date=end_date,
                             fields=['close'], skip_paused=True) if len(stocks) > 0 else pd.DataFrame()

        # 12个月价格
        prices_12m = get_price(stocks, start_date=start_date_12m, end_date=end_date,
                              fields=['close'], skip_paused=True) if len(stocks) > 0 else pd.DataFrame()

        # 计算动量得分
        score = 0.5

        if not prices_1m.empty and not prices_12m.empty:
            # 短期动量（继续效应）
            short_mom = (prices_1m.iloc[-1] / prices_1m.iloc[0] - 1).mean()

            # 长期动量（反转效应）
            long_mom = (prices_12m.iloc[-1] / prices_12m.iloc[0] - 1).mean()

            # 综合动量（短期 positive + 长期 negative = 动量策略）
            score = 0.5 + short_mom * 5 - long_mom * 2
            score = max(0, min(1, score))

        return score

    except:
        return 0.5


def calculate_quality_score(date):
    """
    计算质量风格
    """
    try:
        financial = get_fundamentals(
            query(
                indicator.code, indicator.roe, indicator.gross_profit_margin,
                indicator.net_profit_margin, indicator.total_assets_turnover
            ),
            date=date
        )

        if financial.empty:
            return 0.5

        # 计算高质量股票占比
        median_roe = financial['roe'].median()
        median_gp_margin = financial['gross_profit_margin'].median()

        high_quality = financial[
            (financial['roe'] > median_roe) &
            (financial['gross_profit_margin'] > median_gp_margin)
        ]

        return len(high_quality) / len(financial)

    except:
        return 0.5


def recommend_industries(context, top_n=5):
    """
    推荐投资行业

    基于：
    1. 行业轮动评分
    2. 当前市场风格
    3. 政策导向
    """
    try:
        industry_scores, sorted_industries = get_industry_rotation_scores(context)
        style_scores = get_style_scores(context)

        # 根据风格调整推荐
        recommended = []

        for industry_code, scores in sorted_industries[:top_n * 2]:
            score = scores['score']

            # 风格适配
            style_bonus = 0

            # 大盘风格偏好大市值行业
            if style_scores.get('size', 0.5) > 0.6:
                if is_large_cap_industry(industry_code):
                    style_bonus = 5

            # 价值风格偏好低估值行业
            if style_scores.get('value', 0.5) > 0.6:
                if scores['valuation'] > 60:
                    style_bonus = 5

            # 成长风格偏好高景气行业
            if style_scores.get('momentum', 0.5) > 0.6:
                if scores['brightness'] > 50:
                    style_bonus = 5

            final_score = score + style_bonus

            recommended.append({
                'code': industry_code,
                'name': scores['name'],
                'score': final_score,
                'brightness': scores['brightness'],
                'valuation': scores['valuation'],
                'momentum': scores['momentum'],
            })

        # 排序
        recommended.sort(key=lambda x: x['score'], reverse=True)

        return recommended[:top_n]

    except Exception as e:
        log.error(f"推荐行业出错: {e}")
        return []


def is_large_cap_industry(industry_code):
    """
    判断是否为大市值行业
    """
    large_cap_industries = [
        '801210.SI', '801220.SI', '801180.SI',  # 金融、消费
        '801040.SI', '801360.SI',  # 公用事业
        '801030.SI',  # 医药生物
    ]
    return industry_code in large_cap_industries


def apply_industry_rotation(scores, context):
    """
    应用行业轮动调整
    """
    try:
        industry_scores, _ = get_industry_rotation_scores(context)

        adjusted = {}
        for stock, score in scores.items():
            try:
                industry = get_industry(stock, context.current_dt)
                industry_mult = industry_scores.get(industry, {}).get('score', 50) / 50
                adjusted[stock] = score * industry_mult
            except:
                adjusted[stock] = score

        return adjusted

    except Exception as e:
        log.debug(f"应用行业轮动出错: {e}")
        return scores


def style_neutralization(scores, context):
    """
    风格中性化（Fama-French方法）

    确保组合在各风格上接近市场中性
    """
    try:
        style_scores = get_style_scores(context)

        # 计算当前组合风格暴露
        portfolio_style = calculate_portfolio_style(scores, context)

        # 中性化调整
        adjusted = {}
        for stock, score in scores.items():
            # 简单的风格调整
            style_adjustment = 1.0

            # Size中性
            try:
                info = get_security_info(stock)
                if info and info.market_cap:
                    if style_scores.get('size', 0.5) > 0.6 and info.market_cap < 100:
                        style_adjustment *= 1.1  # 小市值超额收益补偿
                    elif style_scores.get('size', 0.5) < 0.4 and info.market_cap > 200:
                        style_adjustment *= 1.05
            except:
                pass

            adjusted[stock] = score * style_adjustment

        return adjusted

    except Exception as e:
        log.debug(f"风格中性化出错: {e}")
        return scores


def calculate_portfolio_style(scores, context):
    """
    计算组合风格暴露
    """
    try:
        stocks = list(scores.keys())

        # 获取市值和估值信息
        valuation = get_fundamentals(
            query(valuation.code, valuation.market_cap, valuation.pb_ratio)
            .filter(valuation.code.in_(stocks)),
            date=context.current_dt
        )

        if valuation.empty:
            return {'size': 0.5, 'value': 0.5}

        size_median = valuation['market_cap'].median()
        value_median = valuation['pb_ratio'].median()

        size_exposure = len(valuation[valuation['market_cap'] > size_median]) / len(valuation)
        value_exposure = len(valuation[valuation['pb_ratio'] < value_median]) / len(valuation)

        return {'size': size_exposure, 'value': 1 - value_exposure}

    except:
        return {'size': 0.5, 'value': 0.5}


def get_market_regime(context):
    """
    判断市场所处周期阶段

    周期阶段：
    1. 复苏期：经济回暖，业绩预期上升
    2. 过热期：经济过热，通胀上升
    3. 滞胀期：经济放缓，通胀高企
    4. 衰退期：经济衰退，政策宽松
    """
    try:
        end_date = context.current_dt
        start_date = end_date - timedelta(days=365)

        # 获取宏观经济proxy指标
        bench_prices = get_price('000985.XSHG', start_date=start_date, end_date=end_date,
                                fields=['close'], skip_paused=True)

        if len(bench_prices) < 50:
            return 'unknown'

        # 计算指标
        returns = bench_prices['close'].pct_change().dropna()

        # 市场状态
        volatility = returns.std() * np.sqrt(252)
        trend = (bench_prices['close'].iloc[-1] - bench_prices['close'].iloc[-50]) / bench_prices['close'].iloc[-50]
        momentum_12m = (bench_prices['close'].iloc[-1] - bench_prices['close'].iloc[-252]) / bench_prices['close'].iloc[-252] if len(bench_prices) >= 252 else 0

        # 判断周期阶段
        if volatility < 0.18 and trend > 0.05 and momentum_12m > 0:
            return 'bull'  # 复苏/过热期
        elif volatility > 0.25 and trend < -0.10:
            return ' bear'  # 衰退期
        elif volatility > 0.22:
            return 'volatile'  # 滞胀期
        else:
            return 'neutral'  # 正常

    except:
        return 'neutral'


def initialize_rotation_module(context):
    """
    初始化轮动模块
    """
    g.market_regime = 'neutral'
    g.last_rotation_check = None

    log.info("行业/风格轮动模块初始化完成")


def handle_rotation(context):
    """
    处理轮动逻辑
    """
    try:
        # 每月检查一次轮动
        if g.last_rotation_check and (context.current_dt.month == g.last_rotation_check.month):
            return

        g.last_rotation_check = context.current_dt

        # 获取市场状态
        g.market_regime = get_market_regime(context)

        # 推荐行业
        recommended = recommend_industries(context, top_n=3)

        log.info(f"市场状态: {g.market_regime}")
        log.info("推荐行业:")
        for ind in recommended:
            log.info(f"  {ind['name']}: {ind['score']:.2f}")

    except Exception as e:
        log.debug(f"轮动处理出错: {e}")


# 集成到主策略的接口
def initialize(context):
    initialize_rotation_module(context)


def trade(context):
    handle_rotation(context)
