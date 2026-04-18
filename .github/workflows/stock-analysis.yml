"""
分析模块 - 技术分析和AI分析
"""
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import google.generativeai as genai
import requests
import json

logger = logging.getLogger(__name__)

class AIEngine:
    """AI 分析引擎"""
    
    def __init__(self, config):
        self.config = config
        self.gemini_client = None
        self.openai_client = None
        self._init_ai()
    
    def _init_ai(self):
        """初始化AI客户端"""
        # 初始化Gemini
        if self.config.ai.gemini_api_key:
            try:
                genai.configure(api_key=self.config.ai.gemini_api_key)
                self.gemini_client = genai
                logger.info("✅ Gemini AI 初始化成功")
            except Exception as e:
                logger.error(f"❌ Gemini AI 初始化失败: {e}")
        
        # 初始化OpenAI（如果有配置）
        if self.config.ai.openai_api_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(
                    api_key=self.config.ai.openai_api_key,
                    base_url=self.config.ai.openai_base_url or "https://api.openai.com/v1"
                )
                logger.info("✅ OpenAI 客户端初始化成功")
            except Exception as e:
                logger.error(f"❌ OpenAI 客户端初始化失败: {e}")
    
    def analyze_with_gemini(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> Optional[str]:
        """使用Gemini分析股票"""
        if not self.gemini_client:
            return None
            
        try:
            prompt = self._build_analysis_prompt(stock_data, market_data)
            
            # 尝试主模型
            try:
                model = self.gemini_client.GenerativeModel(self.config.ai.gemini_model)
                response = model.generate_content(prompt)
                analysis = response.text
                logger.info(f"✅ Gemini AI 分析完成（使用模型: {self.config.ai.gemini_model}）")
                return analysis
            except Exception as e:
                logger.warning(f"⚠️  主模型失败，尝试回退模型: {e}")
                if self.config.ai.gemini_model_fallback:
                    time.sleep(self.config.ai.gemini_request_delay)
                    model = self.gemini_client.GenerativeModel(self.config.ai.gemini_model_fallback)
                    response = model.generate_content(prompt)
                    analysis = response.text
                    logger.info(f"✅ Gemini AI 分析完成（使用回退模型: {self.config.ai.gemini_model_fallback}）")
                    return analysis
            
        except Exception as e:
            logger.error(f"❌ Gemini AI 分析失败: {e}")
            
        return None
    
    def analyze_with_openai(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> Optional[str]:
        """使用OpenAI分析股票"""
        if not self.openai_client:
            return None
            
        try:
            prompt = self._build_analysis_prompt(stock_data, market_data)
            
            response = self.openai_client.chat.completions.create(
                model=self.config.ai.openai_model or "gpt-4",
                messages=[
                    {"role": "system", "content": "你是一个专业的股票分析师，请用中文进行专业的股票分析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            analysis = response.choices[0].message.content
            logger.info("✅ OpenAI 分析完成")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ OpenAI 分析失败: {e}")
            return None
    
    def _build_analysis_prompt(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> str:
        """构建分析提示词"""
        prompt = f"""请分析以下股票数据，并提供专业的投资建议：

股票信息：
- 代码：{stock_data.get('code', 'N/A')}
- 名称：{stock_data.get('name', 'N/A')}
- 当前价格：{stock_data.get('price', 0):.2f} 元
- 涨跌幅：{stock_data.get('pct_change', 0):.2f}%
- 涨跌额：{stock_data.get('change', 0):.2f} 元
- 成交量：{stock_data.get('volume', 0):,} 手
- 成交额：{stock_data.get('amount', 0):,.2f} 元
- 开盘价：{stock_data.get('open', 0):.2f} 元
- 最高价：{stock_data.get('high', 0):.2f} 元
- 最低价：{stock_data.get('low', 0):.2f} 元
- 昨收价：{stock_data.get('pre_close', 0):.2f} 元
- 数据时间：{stock_data.get('time', 'N/A')}
- 数据源：{stock_data.get('source', 'N/A')}
"""

        if market_data:
            prompt += "\n大盘指数情况：\n"
            for idx_code, idx_data in market_data.items():
                prompt += f"- {idx_data.get('name', idx_code)}：{idx_data.get('price', 0):.2f} ({idx_data.get('pct_change', 0):+.2f}%)\n"
        
        prompt += """
请从以下角度进行分析：
1. 技术面分析（价格走势、成交量、支撑阻力等）
2. 市场情绪分析
3. 短期走势预测
4. 操作建议（买入/持有/卖出）
5. 风险提示

请用中文回答，保持专业、客观。
"""
        return prompt
    
    def analyze_stock(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> Optional[str]:
        """分析股票（自动选择AI引擎）"""
        # 优先使用Gemini
        if self.gemini_client:
            analysis = self.analyze_with_gemini(stock_data, market_data)
            if analysis:
                return analysis
        
        # 回退到OpenAI
        if self.openai_client:
            analysis = self.analyze_with_openai(stock_data, market_data)
            if analysis:
                return analysis
        
        logger.warning("⚠️  所有AI引擎都不可用")
        return None

class TechnicalAnalyzer:
    """技术分析器"""
    
    @staticmethod
    def calculate_ma(data: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> Dict[int, float]:
        """计算移动平均线"""
        ma_values = {}
        for period in periods:
            if len(data) >= period:
                ma_values[period] = data['close'].tail(period).mean()
        return ma_values
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame) -> Dict[str, float]:
        """计算MACD"""
        if len(data) < 26:
            return {}
        
        close_prices = data['close']
        
        # 计算EMA
        ema12 = close_prices.ewm(span=12, adjust=False).mean()
        ema26 = close_prices.ewm(span=26, adjust=False).mean()
        
        # 计算DIF
        dif = ema12 - ema26
        
        # 计算DEA
        dea = dif.ewm(span=9, adjust=False).mean()
        
        # 计算MACD柱
        macd_bar = 2 * (dif - dea)
        
        return {
            'dif': dif.iloc[-1],
            'dea': dea.iloc[-1],
            'macd': macd_bar.iloc[-1],
            'signal': '金叉' if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2] else
                     '死叉' if dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2] else
                     '多头' if dif.iloc[-1] > dea.iloc[-1] else '空头'
        }
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """计算RSI"""
        if len(data) < period + 1:
            return None
        
        close_prices = data['close']
        deltas = close_prices.diff()
        
        gain = (deltas.where(deltas > 0, 0)).rolling(window=period).mean()
        loss = (-deltas.where(deltas < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """计算布林带"""
        if len(data) < period:
            return {}
        
        close_prices = data['close']
        middle_band = close_prices.rolling(window=period).mean()
        std = close_prices.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        current_price = close_prices.iloc[-1]
        position = (current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1]) if upper_band.iloc[-1] != lower_band.iloc[-1] else 0.5
        
        return {
            'upper': upper_band.iloc[-1],
            'middle': middle_band.iloc[-1],
            'lower': lower_band.iloc[-1],
            'position': position,
            'signal': '突破上轨' if current_price > upper_band.iloc[-1] else
                     '突破下轨' if current_price < lower_band.iloc[-1] else
                     '中轨上方' if current_price > middle_band.iloc[-1] else '中轨下方'
        }
    
    @staticmethod
    def analyze_volume(data: pd.DataFrame) -> Dict[str, Any]:
        """分析成交量"""
        if len(data) < 2:
            return {}
        
        current_volume = data['volume'].iloc[-1]
        avg_volume_5 = data['volume'].tail(5).mean()
        avg_volume_20 = data['volume'].tail(20).mean()
        
        volume_ratio_5 = current_volume / avg_volume_5 if avg_volume_5 > 0 else 1
        volume_ratio_20 = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
        
        return {
            'current_volume': current_volume,
            'avg_volume_5': avg_volume_5,
            'avg_volume_20': avg_volume_20,
            'volume_ratio_5': volume_ratio_5,
            'volume_ratio_20': volume_ratio_20,
            'signal': '放量' if volume_ratio_5 > 1.5 else
                     '缩量' if volume_ratio_5 < 0.7 else '平量'
        }

class StockAnalyzer:
    """股票分析器"""
    
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
        self.tech_analyzer = TechnicalAnalyzer()
    
    def analyze_single_stock(self, symbol: str) -> Dict[str, Any]:
        """分析单个股票"""
        logger.info(f"📈 开始分析股票: {symbol}")
        
        # 获取实时数据
        realtime_data = self.data_loader.get_realtime_data(symbol)
        if not realtime_data:
            logger.error(f"❌ 无法获取股票 {symbol} 的实时数据")
            return {"error": "获取数据失败", "code": symbol}
        
        # 获取K线数据用于技术分析
        kline_data = self.data_loader.get_kline_data(symbol, days=60)
        
        # 技术分析
        technical_analysis = {}
        if kline_data is not None and not kline_data.empty:
            # 计算技术指标
            technical_analysis['ma'] = self.tech_analyzer.calculate_ma(kline_data)
            technical_analysis['macd'] = self.tech_analyzer.calculate_macd(kline_data)
            technical_analysis['rsi'] = self.tech_analyzer.calculate_rsi(kline_data)
            technical_analysis['boll'] = self.tech_analyzer.calculate_bollinger_bands(kline_data)
            technical_analysis['volume'] = self.tech_analyzer.analyze_volume(kline_data)
        
        # 获取大盘数据
        market_data = self.data_loader.get_market_index()
        
        # AI分析
        ai_analysis = None
        if self.config.runtime.report_type != "simple":
            if self.ai_engine:
                ai_analysis = self.ai_engine.analyze_stock(realtime_data, market_data)
            else:
                ai_analysis = "⚠️ AI分析不可用（未配置API密钥）"
        
        # 生成综合分析
        analysis_result = {
            "code": symbol,
            "name": realtime_data.get("name", symbol),
            "realtime": realtime_data,
            "technical": technical_analysis,
            "market": market_data,
            "ai_analysis": ai_analysis,
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": self._generate_summary(realtime_data, technical_analysis, ai_analysis)
        }
        
        logger.info(f"✅ 股票 {symbol} 分析完成")
        return analysis_result
    
    def _generate_summary(self, realtime_data: Dict, technical: Dict, ai_analysis: str = None) -> str:
        """生成分析摘要"""
        summary = []
        
        # 基本信息
        price = realtime_data.get('price', 0)
        pct_change = realtime_data.get('pct_change', 0)
        
        if pct_change > 0:
            trend = "📈上涨"
        elif pct_change < 0:
            trend = "📉下跌"
        else:
            trend = "➡️平盘"
        
        summary.append(f"{trend} {pct_change:+.2f}%")
        
        # 技术分析摘要
        if technical:
            if 'ma' in technical and technical['ma']:
                ma5 = technical['ma'].get(5)
                ma10 = technical['ma'].get(10)
                ma20 = technical['ma'].get(20)
                
                if ma5 and ma10 and ma20:
                    if price > ma5 > ma10 > ma20:
                        summary.append("多头排列")
                    elif price < ma5 < ma10 < ma20:
                        summary.append("空头排列")
                    else:
                        summary.append("均线纠结")
            
            if 'macd' in technical and technical['macd']:
                summary.append(f"MACD: {technical['macd'].get('signal', '')}")
            
            if 'volume' in technical and technical['volume']:
                summary.append(f"成交量: {technical['volume'].get('signal', '')}")
        
        # 添加AI分析的关键词
        if ai_analysis:
            keywords = ["买入", "持有", "卖出", "突破", "回调", "支撑", "阻力", "观望"]
            for keyword in keywords:
                if keyword in ai_analysis:
                    if keyword not in summary:
                        summary.append(keyword)
                    break
        
        return " | ".join(summary) if summary else "无技术信号"
    
    def analyze_stocks(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """批量分析股票"""
        results = []
        
        for i, symbol in enumerate(symbols):
            # 添加延迟避免请求过快
            if i > 0 and self.config.runtime.analysis_delay > 0:
                time.sleep(self.config.runtime.analysis_delay)
            
            try:
                result = self.analyze_single_stock(symbol)
                results.append(result)
            except Exception as e:
                logger.error(f"❌ 分析股票 {symbol} 时出错: {e}")
                results.append({"error": str(e), "code": symbol})
        
        return results

class MarketAnalyzer:
    """大盘分析器"""
    
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
    
    def analyze_market(self) -> Dict[str, Any]:
        """分析大盘"""
        logger.info("📊 开始大盘分析")
        
        # 获取主要指数
        indices = self.data_loader.get_market_index()
        
        if not indices:
            logger.error("❌ 无法获取大盘指数数据")
            return {"error": "获取大盘数据失败"}
        
        # 计算总体表现
        total_stocks = len(indices)
        rising_count = sum(1 for idx in indices.values() if idx.get('pct_change', 0) > 0)
        falling_count = sum(1 for idx in indices.values() if idx.get('pct_change', 0) < 0)
        
        # 计算平均涨跌幅
        avg_change = sum(idx.get('pct_change', 0) for idx in indices.values()) / total_stocks if total_stocks > 0 else 0
        
        # 生成市场情绪
        if avg_change > 1:
            sentiment = "🔥 强势上涨"
        elif avg_change > 0.5:
            sentiment = "📈 温和上涨"
        elif avg_change > 0:
            sentiment = "↗️ 小幅上涨"
        elif avg_change > -0.5:
            sentiment = "↘️ 小幅下跌"
        elif avg_change > -1:
            sentiment = "📉 温和下跌"
        else:
            sentiment = "💥 大幅下跌"
        
        # AI分析市场
        market_analysis = None
        if self.config.runtime.report_type != "simple" and self.ai_engine:
            market_prompt = self._build_market_prompt(indices)
            market_analysis = self.ai_engine.analyze_with_gemini({"name": "A股大盘", "pct_change": avg_change}, {})
            if not market_analysis:
                market_analysis = self.ai_engine.analyze_with_openai({"name": "A股大盘", "pct_change": avg_change}, {})
        
        result = {
            "indices": indices,
            "summary": {
                "total_indices": total_stocks,
                "rising_count": rising_count,
                "falling_count": falling_count,
                "avg_change": avg_change,
                "sentiment": sentiment,
                "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "market_analysis": market_analysis
        }
        
        logger.info(f"✅ 大盘分析完成，市场情绪: {sentiment}")
        return result
    
    def _build_market_prompt(self, indices: Dict[str, Any]) -> str:
        """构建大盘分析提示词"""
        prompt = "请分析当前A股市场情况，基于以下主要指数表现：\n\n"
        
        for idx_code, idx_data in indices.items():
            prompt += f"- {idx_data.get('name', idx_code)}：{idx_data.get('price', 0):.2f} ({idx_data.get('pct_change', 0):+.2f}%)\n"
        
        prompt += """
请从以下角度进行分析：
1. 整体市场情绪
2. 各板块表现差异
3. 资金流向分析
4. 短期市场展望
5. 投资建议

请用中文回答，保持专业、客观。
"""
        return prompt
