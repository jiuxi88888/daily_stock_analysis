# -*- coding: utf-8 -*-
""" A股股票分析器 - 固定股票 + 精选3只预测版 """
import os
import logging
import time
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ================= 股票精选器（✅ 额外精选 Top 3） =================
class StockSelector:
    def __init__(self, data_loader, config):
        self.data_loader = data_loader
        self.config = config
        self.logger = logging.getLogger(__name__)

    def select_stocks(self, count=3):
        """
        在自选股基础上，额外精选 Top 3 只技术面最强的股票
        """
        self.logger.info("🎯 在自选股基础上精选 Top 3 只股票...")
        watchlist = self.config.stock_list
        if not watchlist:
            return []

        candidates = []
        for code in watchlist:
            try:
                data = self.data_loader.get_stock_data(code)
                if not data or data.get("error"):
                    continue

                tech = data.get("technical", {})
                score = tech.get("score", 0)
                if score < 4:
                    continue

                candidates.append({
                    "code": code,
                    "name": data.get("name", code),
                    "score": score
                })
            except Exception:
                continue

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:count]


# ================= AI 引擎（✅ 修复配置读取问题） =================
class AIEngine:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # ✅ 核心修复：从 config 实例中读取配置，而不是 os.getenv
        self.api_key = config.openai_api_key
        self.base_url = config.openai_base_url
        self.model = config.openai_model
        self.temperature = config.openai_temperature
        
        # ✅ 如果 OpenAI 没有配置，尝试使用 Gemini
        if not self.api_key and config.gemini_api_key:
            self.logger.info("⚠️ OpenAI API Key 未配置，将使用 Gemini")
            self.api_key = config.gemini_api_key
            self.model = config.gemini_model
            self.temperature = config.gemini_temperature
            # Gemini 官方 API 端点
            self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        if not self.api_key:
            self.logger.error("❌ 未配置任何 AI API Key (OpenAI 或 Gemini)")
            self.client = None
            return
        
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30
            )
            self.logger.info(f"✅ AI 引擎初始化成功")
            self.logger.info(f"   - 模型: {self.model}")
            self.logger.info(f"   - 接口: {self.base_url[:30]}...")
        except Exception as e:
            self.logger.error(f"❌ AI 引擎初始化失败: {e}")
            self.client = None

    def analyze_stock(self, stock_data):
        """分析单只股票，返回包含 ai_prediction 的字典"""
        if not self.client:
            return {"ai_prediction": "AI引擎未初始化，请检查API Key配置"}
        
        try:
            prompt = self._build_prompt(stock_data)
            
            self.logger.debug(f"正在调用AI分析: {stock_data.get('code')}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            
            return {
                "ai_prediction": content,
                "ai_model": self.model
            }
            
        except Exception as e:
            self.logger.error(f"AI 分析失败 {stock_data.get('code', '')}: {e}")
            return {
                "ai_prediction": f"⚠️ AI分析暂时不可用: {str(e)[:80]}",
                "ai_model": "error"
            }

    def _build_prompt(self, stock_data):
        """构建AI分析提示词"""
        tech = stock_data.get("technical", {})
        
        prompt = f"""你是一位资深A股量化分析师。请基于以下股票数据，生成一份专业、客观的分析报告。

【股票基本信息】
- 名称：{stock_data.get('name', 'N/A')}
- 代码：{stock_data.get('code', 'N/A')}
- 当前价：{stock_data.get('current_price', 'N/A')}
- 涨跌幅：{stock_data.get('pct_chg', 'N/A')}%
- 成交量：{stock_data.get('volume', 'N/A')}
- 成交额：{stock_data.get('amount', 'N/A')}

【技术指标分析】
- 趋势方向：{tech.get('trend', 'N/A')}
- MACD状态：{tech.get('macd_status', 'N/A')}
- RSI指标：{tech.get('rsi', 'N/A')}
- 支撑位：{tech.get('support', 'N/A')}
- 压力位：{tech.get('resistance', 'N/A')}
- 综合评分：{tech.get('score', 'N/A')}/10

请严格按照以下结构输出分析报告（使用Markdown格式）：
1. **技术面分析**：解读当前技术指标和形态
2. **趋势预判**：未来3-5个交易日的可能走势方向
3. **关键价位**：重要的支撑位、压力位和目标位
4. **操作建议**：具体的操作策略（买入/持有/卖出/观望）
5. **风险提示**：需要注意的主要风险因素

请保持客观、理性，不要使用夸张词汇。如果数据不足，请明确指出。
"""
        return prompt
# ================= 主分析器 =================
class StockAnalyzer:
    def __init__(self, data_loader, ai_engine, config):
        self.data_loader = data_loader
        self.ai_engine = ai_engine
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stock_selector = StockSelector(data_loader, config)

    def analyze_stocks(self, stock_codes):
        results = []
        for code in stock_codes:
            self.logger.info(f"📊 分析: {code}")
            data = self.data_loader.get_stock_data(code)
            if not data or data.get("error"):
                continue

            ai = self.ai_engine.analyze_stock(data)
            data.update(ai)
            data["is_selected"] = False
            results.append(data)
            time.sleep(random.uniform(1, 2))
        return results

    def select_and_analyze(self, count=3):
        selected = self.stock_selector.select_stocks(count)
        results = self.analyze_stocks([s["code"] for s in selected])
        for r in results:
            r["is_selected"] = True
        return results
