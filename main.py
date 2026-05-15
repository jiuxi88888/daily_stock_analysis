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

def create_report(results: list):
    """
    输出：
    1. 固定自选股分析
    2. 精选 Top 3 股票分析
    """
    normal_stocks = [r for r in results if not r.get("is_selected")]
    selected_stocks = [r for r in results if r.get("is_selected")]

    report = ""

    if normal_stocks:
        report += "## 📌 自选股分析\n\n"
        for r in normal_stocks:
            summary = r.get("ai_prediction", "")
            if summary:
                report += f"### {r.get('name')}({r.get('code')})\n{summary}\n\n"

    if selected_stocks:
        report += "---\n\n## 🎯 精选 Top 3 股票\n\n"
        for r in selected_stocks:
            summary = r.get("ai_prediction", "")
            if summary:
                report += f"### {r.get('name')}({r.get('code')})\n{summary}\n\n"

    if not report:
        return "今日暂无有效分析"
    return report.strip()

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    config = get_config()
    data_loader = DataLoader(config)
    ai_engine = AIEngine(config)
    stock_analyzer = StockAnalyzer(data_loader, ai_engine, config)
    notifier = Notifier(config)

    all_results = []

    # 1️⃣ 分析固定自选股（全量）
    if config.stock_list:
        logger.info(f"📈 分析固定自选股: {len(config.stock_list)} 只")
        all_results.extend(stock_analyzer.analyze_stocks(config.stock_list))

    # 2️⃣ 额外精选 Top 3 只股票
    if config.enable_selection:
        logger.info("🎯 额外精选 Top 3 只股票")
        all_results.extend(stock_analyzer.select_and_analyze(count=3))

    report = create_report(all_results)
    notifier.send_all("📈 股票分析 + 精选预测", report)

    logger.info("✅ 完成")
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
