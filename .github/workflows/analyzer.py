"""
分析模块 - 适配便携AI
"""
import logging
import time
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIEngine:
    """AI 分析引擎 - 适配便携AI"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self._init_ai()
    
    def _init_ai(self):
        """初始化便携AI客户端"""
        if self.config.ai.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.config.ai.api_key,
                    base_url=self.config.ai.base_url,
                    timeout=self.config.ai.timeout
                )
                logger.info(f"✅ AI客户端初始化成功 (BaseURL: {self.config.ai.base_url})")
            except Exception as e:
                logger.error(f"❌ AI客户端初始化失败: {e}")
        else:
            logger.warning("⚠️  AI API Key 未配置")
    
    def analyze_stock(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> Optional[str]:
        """使用便携AI分析股票"""
        if not self.client:
            return "⚠️ AI分析不可用（未配置API密钥）"
        
        try:
            prompt = self._build_analysis_prompt(stock_data, market_data)
            
            response = self.client.chat.completions.create(
                model=self.config.ai.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个专业的股票分析师，请用中文进行专业的股票分析。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.config.ai.max_tokens,
                temperature=self.config.ai.temperature
            )
            
            analysis = response.choices[0].message.content
            logger.info(f"✅ AI分析完成 (模型: {self.config.ai.model})")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ AI分析失败: {e}")
            return None
    
    def _build_analysis_prompt(self, stock_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> str:
        """构建分析提示词"""
        prompt = f"""请分析以下股票数据：

股票：{stock_data.get('name', '')} ({stock_data.get('code', '')})
当前价格：{stock_data.get('price', 0):.2f} 元
涨跌幅：{stock_data.get('pct_change', 0):.2f}%
涨跌额：{stock_data.get('change', 0):.2f} 元
成交量：{stock_data.get('volume', 0):,} 手
成交额：{stock_data.get('amount', 0):,.2f} 元
开盘价：{stock_data.get('open', 0):.2f} 元
最高价：{stock_data.get('high', 0):.2f} 元
最低价：{stock_data.get('low', 0):.2f} 元
数据时间：{stock_data.get('time', '')}
"""
        
        if market_data:
            prompt += "\n大盘指数：\n"
            for code, data in market_data.items():
                pct = data.get('pct_change', 0)
                emoji = "📈" if pct > 0 else "📉" if pct < 0 else "➡️"
                prompt += f"{emoji} {data.get('name', code)}：{data.get('price', 0):.2f} ({pct:+.2f}%)\n"
        
        prompt += """
请从以下角度分析：
1. 技术面分析（价格走势、成交量）
2. 市场情绪分析
3. 短期走势预测
4. 操作建议（买入/持有/卖出）
5. 风险提示

请用中文回答，保持专业客观，300字左右。
"""
        return prompt

class StockAnalyzer:
    """股票分析器"""
    
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
    
    def analyze_single_stock(self, symbol: str) -> Dict[str, Any]:
        """分析单个股票"""
        logger.info(f"📈 分析股票: {symbol}")
        
        # 获取实时数据
        data = self.data_loader.get_realtime_data(symbol)
        if not data:
            return {"error": "获取数据失败", "code": symbol}
        
        # 获取大盘数据
        market_data = self.data_loader.get_market_index()
        
        # AI分析
        ai_analysis = None
        if self.config.runtime.report_type != "simple":
            ai_analysis = self.ai_engine.analyze_stock(data, market_data)
        
        return {
            "code": symbol,
            "name": data.get("name", symbol),
            "data": data,
            "market": market_data,
            "ai_analysis": ai_analysis,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
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
                logger.error(f"❌ 分析 {symbol} 失败: {e}")
                results.append({"error": str(e), "code": symbol})
        
        return results
