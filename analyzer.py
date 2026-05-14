# -*- coding: utf-8 -*-
""" A股股票分析器 - 升级版 v2.0 """
import os
import sys
import logging
import time
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """技术指标计算器"""
    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Optional[float]]:
        if len(prices) < slow:
            return {'macd': None, 'signal': None, 'histogram': None}
        
        def calc_ema(data, period):
            ema = [sum(data[:period]) / period]
            multiplier = 2 / (period + 1)
            for price in data[period:]:
                ema.append((price - ema[-1]) * multiplier + ema[-1])
            return ema

        ema_fast = calc_ema(prices, fast)
        ema_slow = calc_ema(prices, slow)
        dif = ema_fast[-1] - ema_slow[-1]
        macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast))]
        
        if len(macd_line) < signal:
            return {'macd': dif, 'signal': None, 'histogram': None}
        
        dea = sum(macd_line[-signal:]) / signal
        return {
            'macd': dif,
            'signal': dea,
            'histogram': (dif - dea) * 2
        }

    @staticmethod
    def calculate_kdj(highs: List[float], lows: List[float], closes: List[float], period: int = 9, k_period: int = 3, d_period: int = 3) -> Dict[str, Optional[float]]:
        if len(closes) < period:
            return {'k': None, 'd': None, 'j': None}
        
        rsv_list = []
        for i in range(period - 1, len(closes)):
            high = max(highs[i - period + 1:i + 1])
            low = min(lows[i - period + 1:i + 1])
            close = closes[i]
            if high == low:
                rsv = 50
            else:
                rsv = (close - low) / (high - low) * 100
            rsv_list.append(rsv)

        if len(rsv_list) < k_period:
            return {'k': None, 'd': None, 'j': None}

        k = 50.0
        d = 50.0
        multiplier_k = 1 / k_period
        multiplier_d = 1 / d_period
        
        for rsv in rsv_list[-k_period:]:
            k = rsv * multiplier_k + k * (1 - multiplier_k)
        for k_val in rsv_list[-d_period:]:
            d = k_val * multiplier_d + d * (1 - multiplier_d)
        
        j = 3 * k - 2 * d
        return {'k': k, 'd': d, 'j': j}

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: int = 2) -> Dict[str, Optional[float]]:
        if len(prices) < period:
            return {'upper': None, 'middle': None, 'lower': None}
        
        import statistics
        recent_prices = prices[-period:]
        middle = statistics.mean(recent_prices)
        std = statistics.stdev(recent_prices)
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

class StockSelector:
    """股票精选器"""
    def __init__(self, data_loader, config):
        self.data_loader = data_loader
        self.config = config
        self.logger = logging.getLogger(__name__)

    def select_stocks(self, count: int = 8) -> List[Dict[str, Any]]:
        """精选股票核心逻辑"""
        self.logger.info(f"🎯 开始精选股票（目标: {count}只）...")
        selected = []
        
        try:
            strong_stocks = self._get_strong_stocks()
            if strong_stocks:
                selected.extend(strong_stocks[:count])
                self.logger.info(f"✅ 从强势股票中精选: {len(strong_stocks[:count])}只")

            if len(selected) < count:
                industry_leaders = self._get_industry_leaders(count - len(selected))
                selected.extend(industry_leaders)
                self.logger.info(f"✅ 补充行业龙头: {len(industry_leaders)}只")

            if len(selected) < count:
                backup_stocks = self._get_backup_stocks(count - len(selected))
                selected.extend(backup_stocks)
                self.logger.info(f"✅ 补充备选股票: {len(backup_stocks)}只")

            seen = set()
            unique_selected = []
            for stock in selected:
                code = stock.get('code')
                if code and code not in seen:
                    seen.add(code)
                    unique_selected.append(stock)

            self.logger.info(f"✅ 精选完成，共 {len(unique_selected)} 只股票")
            return unique_selected[:count]
        except Exception as e:
            self.logger.error(f"❌ 精选股票失败: {e}")
            return []

    def _get_strong_stocks(self) -> List[Dict[str, Any]]:
        """获取今日强势股票"""
        try:
            import akshare as ak
            df = ak.stock_zt_pool_strong_em()
            stocks = []
            for _, row in df.head(10).iterrows():
                try:
                    code = str(row.get('代码', ''))
                    name = str(row.get('名称', ''))
                    if code and not code.startswith('8') and not code.startswith('4'):
                        stocks.append({
                            'code': code,
                            'name': name,
                            'source': '强势股',
                            'reason': f"涨停强势股"
                        })
                except:
                    continue
            return stocks
        except Exception as e:
            self.logger.warning(f"⚠️ 获取强势股票失败: {e}")
            return []

    def _get_industry_leaders(self, count: int) -> List[Dict[str, Any]]:
        """获取行业龙头股"""
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            top_industries = df.nlargest(5, '涨跌幅')
            stocks = []
            
            for _, industry in top_industries.iterrows():
                try:
                    industry_name = industry.get('名称', '')
                    if industry_name:
                        industry_df = ak.stock_board_industry_cons_em(symbol=industry_name)
                        if not industry_df.empty:
                            for _, stock in industry_df.head(2).iterrows():
                                code = str(stock.get('代码', ''))
                                name = str(stock.get('名称', ''))
                                if code and not code.startswith('8') and not code.startswith('4'):
                                    stocks.append({
                                        'code': code,
                                        'name': name,
                                        'source': '行业龙头',
                                        'reason': f"行业龙头：{industry_name}"
                                    })
                except:
                    continue
            return stocks[:count]
        except Exception as e:
            self.logger.warning(f"⚠️ 获取行业龙头失败: {e}")
            return []

    def _get_backup_stocks(self, count: int) -> List[Dict[str, Any]]:
        """获取备选优质股"""
        backup_list = [
            {'code': '600519', 'name': '贵州茅台', 'source': '备选', 'reason': '白酒龙头'},
            {'code': '000858', 'name': '五粮液', 'source': '备选', 'reason': '白酒龙头'},
            {'code': '300750', 'name': '宁德时代', 'source': '备选', 'reason': '新能源龙头'},
            {'code': '601318', 'name': '中国平安', 'source': '备选', 'reason': '保险龙头'},
            {'code': '600036', 'name': '招商银行', 'source': '备选', 'reason': '银行龙头'},
            {'code': '000001', 'name': '平安银行', 'source': '备选', 'reason': '银行股'},
            {'code': '002594', 'name': '比亚迪', 'source': '备选', 'reason': '汽车龙头'},
            {'code': '300059', 'name': '东方财富', 'source': '备选', 'reason': '券商龙头'},
        ]
        return backup_list[:count]

class AIEngine:
    """AI分析引擎"""
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.bianxie.ai/v1')
        self.model = os.getenv('AI_MODEL', 'gpt-4o')
        self.logger.info(f"🤖 AI引擎初始化: {self.base_url}/{self.model}")

    def analyze_stock(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI分析单只股票"""
        try:
            prompt = self._build_analysis_prompt(stock_data)
            response = self._call_api(prompt)
            result = self._parse_response(response)
            return {
                'ai_advice': result.get('advice', '观望'),
                'ai_score': result.get('score', 50),
                'ai_summary': result.get('summary', ''),
                'ai_risk': result.get('risk', ''),
                'ai_trend': result.get('trend', '震荡')
            }
        except Exception as e:
            self.logger.error(f"AI分析失败: {e}")
            return {
                'ai_advice': '观望',
                'ai_score': 50,
                'ai_summary': 'AI分析暂时不可用',
                'ai_risk': '',
                'ai_trend': '震荡'
            }

    def _build_analysis_prompt(self, stock_data: Dict[str, Any]) -> str:
        """构建AI分析提示词"""
        code = stock_data.get('code', '')
        name = stock_data.get('name', '')
        price = stock_data.get('current_price', 0)
        change_pct = stock_data.get('change_percent', 0)
        volume_ratio = stock_data.get('volume_ratio', 0)
        turnover = stock_data.get('turnover_rate', 0)
        ma5 = stock_data.get('ma5', 0)
        ma10 = stock_data.get('ma10', 0)
        ma20 = stock_data.get('ma20', 0)
        tech = stock_data.get('technical', {})
        
        macd = tech.get('macd', {})
        kdj = tech.get('kdj', {})
        rsi = tech.get('rsi', 0)
        bollinger = tech.get('bollinger', {})

        prompt = f"""你是一位专业的A股股票分析师，请分析以下股票并给出专业建议。

**股票信息**
- 代码: {code}
- 名称: {name}
- 当前价: {price:.2f}元
- 涨跌幅: {change_pct:+.2f}%

**均线位置**
- MA5: {ma5:.2f}
- MA10: {ma10:.2f}  
- MA20: {ma20:.2f}
- 当前价格: {price:.2f}
- 均线多头排列: {'是' if price > ma5 > ma10 > ma20 else '否'}

**量能指标**
- 量比: {volume_ratio:.2f}
- 换手率: {turnover:.2f}%

**技术指标**
- MACD: DIF={macd.get('macd', 0):.3f}, DEA={macd.get('signal', 0):.3f}, 柱={macd.get('histogram', 0):.3f}
- KDJ: K={kdj.get('k', 0):.2f}, D={kdj.get('d', 0):.2f}, J={kdj.get('j', 0):.2f}
- RSI(14): {rsi:.2f}
- 布林带: 上轨={bollinger.get('upper', 0):.2f}, 中轨={bollinger.get('middle', 0):.2f}, 下轨={bollinger.get('lower', 0):.2f}

**评分标准（请严格按此评分）**：
- 70-100分：强势上涨趋势，有明显买入信号
- 50-69分：震荡或温和上涨，观望为主
- 30-49分：弱势或下跌趋势，注意风险
- 0-29分：明显下跌趋势，建议卖出

请根据以上指标综合分析，给出:
1. 决策建议：买入/观望/卖出
2. 评分(0-100的整数)
3. 简要理由(50字内)
4. 风险提示(30字内)
5. 趋势：上涨/震荡/下跌

返回JSON格式:
{{"advice":"买入","score":75,"summary":"股价站稳均线，MACD金叉，量能放大","risk":"注意大盘回调风险","trend":"上涨"}}
"""
        return prompt

    def _call_api(self, prompt: str) -> str:
        """调用API"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的A股股票分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"API调用失败: {e}")
            raise

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析API响应"""
        try:
            import json
            if '{' in response and '}' in response:
                json_str = response[response.find('{'):response.rfind('}')+1]
                return json.loads(json_str)
            return {
                'advice': '观望',
                'score': 50,
                'summary': response[:100],
                'risk': '',
                'trend': '震荡'
            }
        except:
            return {
                'advice': '观望',
                'score': 50,
                'summary': response[:100] if response else '',
                'risk': '',
                'trend': '震荡'
            }

class StockAnalyzer:
    """股票分析器主类"""
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.tech_indicator = TechnicalIndicators()
        self.stock_selector = StockSelector(data_loader, config)

    def analyze_stocks(self, stock_codes: List[str]) -> List[Dict[str, Any]]:
        """分析股票列表"""
        results = []
        for code in stock_codes:
            try:
                self.logger.info(f"📊 正在分析: {code}")
                stock_data = self.data_loader.get_stock_data(code)
                
                if not stock_data or 'error' in stock_data:
                    results.append({
                        'code': code,
                        'error': stock_data.get('error', '获取数据失败')
                    })
                    continue

                stock_data['technical'] = self._calculate_technical(stock_data)
                ai_result = self.ai_engine.analyze_stock(stock_data)
                stock_data.update(ai_result)
                stock_data['decision'] = self._make_decision(stock_data)
                results.append(stock_data)
                
                time.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                self.logger.error(f"分析 {code} 失败: {e}")
                results.append({
                    'code': code,
                    'error': str(e)
                })
        return results

    def select_and_analyze(self, count: int = 8) -> List[Dict[str, Any]]:
        """精选股票并分析"""
        selected_stocks = self.stock_selector.select_stocks(count)
        if not selected_stocks:
            self.logger.warning("⚠️ 未筛选到任何股票")
            return []
        
        codes = [s['code'] for s in selected_stocks]
        results = self.analyze_stocks(codes)
        
        for result in results:
            result['is_selected'] = True
            for selected in selected_stocks:
                if selected['code'] == result.get('code'):
                    result['selection_reason'] = selected.get('reason', '')
                    break
        
        return results

    def _calculate_technical(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算技术指标"""
        try:
            hist = stock_data.get('price_history', [])
            if len(hist) < 20:
                return {}
            
            closes = [h['close'] for h in hist]
            highs = [h['high'] for h in hist]
            lows = [h['low'] for h in hist]

            return {
                'macd': self.tech_indicator.calculate_macd(closes),
                'kdj': self.tech_indicator.calculate_kdj(highs, lows, closes),
                'rsi': self.tech_indicator.calculate_rsi(closes),
                'bollinger': self.tech_indicator.calculate_bollinger_bands(closes)
            }
        except Exception as e:
            self.logger.error(f"技术指标计算失败: {e}")
            return {}

    def _make_decision(self, stock_data: Dict[str, Any]) -> str:
        """综合决策"""
        score = stock_data.get('ai_score', 50)
        if score >= 70:
            return '🟢 买入'
        elif score >= 40:
            return '🟡 观望'
        else:
            return '🔴 卖出'
