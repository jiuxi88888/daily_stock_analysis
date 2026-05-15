# -*- coding: utf-8 -*-
""" A股股票分析器 - 优化版：精选3只 + AI未来走势预测 """
import os
import logging
import time
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ================= 股票精选器（✅ 固定精选 Top 3） =================
class StockSelector:
    def __init__(self, data_loader, config):
        self.data_loader = data_loader
        self.config = config
        self.logger = logging.getLogger(__name__)

    def select_stocks(self, count=3):
        """
        基于技术评分精选 Top 3 只股票
        （count 参数预留接口，内部强制 Top 3）
        """
        self.logger.info("🎯 开始基于技术评分精选 Top 3 只股票...")
        watchlist = self.config.stock_list
        if not watchlist:
            self.logger.warning("⚠️ 自选股为空，无法精选")
            return []

        candidates = []
        for code in watchlist:
            try:
                data = self.data_loader.get_stock_data(code)
                if not data or data.get("error"):
                    continue

                tech = data.get("technical", {})
                score = tech.get("score", 0)
                # 只保留有操作价值的票（评分 >= 4）
                if score < 4:
                    continue

                candidates.append({
                    "code": code,
                    "name": data.get("name", code),
                    "score": score,
                    "reason": f"技术评分 {score}｜趋势 {tech.get('trend')}"
                })
            except Exception as e:
                self.logger.warning(f"⚠️ 精选失败 {code}: {e}")

        # 按技术评分降序排序
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = candidates[:3]  # ✅ 强制只取前 3 只

        if len(selected) < 3:
            self.logger.warning(f"⚠️ 达标股票不足 3 只，实际精选: {len(selected)} 只")
        self.logger.info(f"✅ 精选完成，共 {len(selected)} 只")
        return selected


# ================= AI 引擎（✅ 专注未来走势与涨幅预测） =================
class AIEngine:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.bianxie.ai/v1")
        self.model = os.getenv("AI_MODEL", "gpt-4o")
        self.logger.info(f"🤖 AI引擎初始化: {self.base_url}/{self.model}")

    def analyze_stock(self, stock_data):
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30
            )
            prompt = self._build_prompt(stock_data)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            # 直接返回 AI 生成的完整预测文本
            return {"ai_prediction": resp.choices[0].message.content.strip()}
        except Exception:
            return {"ai_prediction": "分析暂时不可用"}

    def _build_prompt(self, d):
        """
        优化后的 Prompt：强制要求完整预测分析 + 未来走势涨幅，不带废话
        """
        return f"""
你是一位资深A股量化分析师。
请基于以下数据，直接生成一份**完整的股票预测分析**，必须重点包含未来走势和涨幅预判。

股票：{d.get('name')}({d.get('code')})
当前价：{d.get('current_price')}
技术评分：{d.get('technical', {}).get('score')}
趋势：{d.get('technical', {}).get('trend')}
MACD：{d.get('technical', {}).get('macd_status')}
RSI：{d.get('technical', {}).get('rsi')}

请严格按照以下结构输出（Markdown格式，语言专业简练，不要返回JSON，不要任何客套话如“好的，这是分析”）：
1. 当前技术面定调（趋势/量能/MACD/RSI解读）
2. 短期未来走势预判（明确向上/震荡/向下，逻辑简述）
3. 预估未来3-5日潜在涨幅区间（例如：预计震荡偏强，潜在上行空间约 2%~4%）
4. 核心操作思路（低吸/持股/观望/风控位）

只输出上述分析文本，严禁输出其他无关文字。
"""


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
        """
        对外接口：精选 Top 3 只，并做 AI 未来走势预测分析
        """
        selected = self.stock_selector.select_stocks(count=3)
        results = self.analyze_stocks([s["code"] for s in selected])
        for r in results:
            r["is_selected"] = True
            for s in selected:
                if s["code"] == r["code"]:
                    r["selection_reason"] = s.get("reason", "")
        return results
