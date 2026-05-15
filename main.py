#!/usr/bin/env python3
import os
import sys
import logging
from datetime import datetime

from config import get_config
from data_loader import DataLoader
from analyzer import StockAnalyzer, AIEngine
from notifier import Notifier

def setup_logging():
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"{log_dir}/analysis_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def create_report(results: list, market_data: dict) -> str:
    """只输出完整股票预测分析（无任何其他文字）"""
    parts = []
    for r in results:
        summary = r.get("ai_summary", "")
        if summary and summary != "分析暂时不可用":
            parts.append(f"## {r.get('name')}({r.get('code')})\n\n{summary}")

    if not parts:
        return "分析完成，暂无有效预测"
    return "\n\n---\n\n".join(parts)

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    config = get_config()
    data_loader = DataLoader(config)
    ai_engine = AIEngine(config)
    stock_analyzer = StockAnalyzer(data_loader, ai_engine, config)
    notifier = Notifier(config)

    all_results = []

    if config.stock_list:
        all_results.extend(stock_analyzer.analyze_stocks(config.stock_list))

    if config.enable_selection:
        all_results.extend(stock_analyzer.select_and_analyze(config.selection_count))

    report = create_report(all_results, data_loader.get_market_index())
    notifier.send_all("📈 股票预测分析", report)

    logger.info("✅ 完成")
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
