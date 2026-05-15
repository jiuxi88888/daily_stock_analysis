# -*- coding: utf-8 -*-
""" A股股票分析器 - 最终稳定版 v2.1 """
import os
import sys
import logging
import time
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ================= 股票精选器（✅ 技术评分驱动） =================
class StockSelector:
    def __init__(self, data_loader, config):
        self.data_loader = data_loader
        self.config = config
        self.logger = logging.getLogger(__name__)

    def select_stocks(self, count=8):
        self.logger.info(f"🎯 开始精选股票（目标: {count}只）...")
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

        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = candidates[:count]

        if len(selected) < count:
            self.logger.warning(f"⚠️ 精选不足，仅 {len(selected)} 只达标")

        self.logger.info(f"✅ 精选完成，共 {len(selected)} 只")
        return selected


# ================= AI 引擎（✅ 只解释，不决策） =================
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
            return self._parse(resp.choices[0].message.content)
        except Exception:
            return {
                "advice": "观望",
                "score": 50,
                "summary": "AI分析不可用",
                "risk": "",
                "trend": "震荡"
            }

    def _build_prompt(self, d):
        return f"""
你是A股分析师，只做一句话解读。
股票：{d.get('name')}({d.get('code')})
技术评分：{d.get('technical', {}).get('score')}
趋势：{d.get('technical', {}).get('trend')}
MACD：{d.get('technical', {}).get('macd_status')}
RSI：{d.get('technical', {}).get('rsi')}

请用一句话说明风险和机会，不要给出买卖建议。
"""

    def _parse(self, text):
        import json
        try:
            return json.loads(text[text.find("{"):text.rfind("}") + 1])
        except:
            return {
                "advice": "观望",
                "score": 50,
                "summary": text[:80],
                "risk": "",
                "trend": "震荡"
            }


# ================= 主分析器（✅ 决策只认技术评分） =================
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
                results.append({"code": code, "error": "数据失败"})
                continue

            ai = self.ai_engine.analyze_stock(data)
            data.update(ai)

            # ✅ 决策只来自技术评分
            tech = data.get("technical", {})
            score = tech.get("score", 0)
            if score >= 7:
                data["decision"] = "🟢 买入"
            elif score >= 4:
                data["decision"] = "🟡 观望"
            else:
                data["decision"] = "🔴 卖出"

            data["is_selected"] = False
            results.append(data)
            time.sleep(random.uniform(1, 2))
        return results

    def select_and_analyze(self, count=8):
        selected = self.stock_selector.select_stocks(count)
        results = self.analyze_stocks([s["code"] for s in selected])
        for r in results:
            r["is_selected"] = True
            for s in selected:
                if s["code"] == r["code"]:
                    r["selection_reason"] = s.get("reason", "")
        return results
