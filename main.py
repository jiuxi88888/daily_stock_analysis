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

def create_report(results: list) -> str:
    """
    输出：
    1. 固定自选股分析
    2. 精选 Top 3 股票分析（绝不遗漏）
    """

    # ✅ 精选股票（只看 is_selected）
    selected_stocks = [r for r in results if r.get("is_selected")]

    # ✅ 普通自选股（排除精选股，防止重复和覆盖）
    selected_codes = {r.get("code") for r in selected_stocks}
    normal_stocks = [
        r for r in results
        if not r.get("is_selected") and r.get("code") not in selected_codes
    ]

    report = ""

    if normal_stocks:
        report += "## 📌 自选股分析\n\n"
        for r in normal_stocks:
            pred = r.get("ai_prediction") or r.get("ai_summary", "")
            if pred:
                report += f"### {r.get('name')}({r.get('code')})\n{pred}\n\n"

    if selected_stocks:
        report += "---\n\n## 🎯 精选 Top 3 股票\n\n"
        for r in selected_stocks:
            pred = r.get("ai_prediction") or r.get("ai_summary", "")
            if pred:
                report += f"### {r.get('name')}({r.get('code')})\n{pred}\n\n"

    if not report.strip():
        return "今日暂无有效分析"

    return report.strip()[:6000]


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("🚀 股票分析系统 - 固定股票 + 精选预测")
    logger.info("=" * 60)

    config = get_config()

    warnings = config.validate()
    if warnings:
        for w in warnings:
            logger.warning(w)

    os.makedirs('reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    try:
        data_loader = DataLoader(config)
        ai_engine = AIEngine(config)
        stock_analyzer = StockAnalyzer(data_loader, ai_engine, config)
        notifier = Notifier(config)

        logger.info("✅ 组件初始化成功")

        all_results = []

        # 1️⃣ 分析固定自选股（全量）
        if config.stock_list:
            logger.info(f"📈 分析固定自选股: {len(config.stock_list)} 只")
            all_results.extend(stock_analyzer.analyze_stocks(config.stock_list))

        # 2️⃣ 额外精选 Top 3 只股票
        if config.enable_selection:
            logger.info("🎯 额外精选 Top 3 只股票")
            selected = stock_analyzer.select_and_analyze(count=3)
            if not selected:
                logger.warning("⚠️ 今日无符合技术条件的精选股票")
            all_results.extend(selected)

        # 3️⃣ 生成报告
        report = create_report(all_results)

        # 4️⃣ 保存本地
        report_date = datetime.now().strftime("%Y%m%d")
        report_file = f"reports/report_{report_date}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"✅ 报告已保存: {report_file}")

        # 5️⃣ 推送
        notifier.send_all("📈 股票分析 + 精选预测", report)
        logger.info("✅ 推送完成")

        return True

    except Exception as e:
        logger.error(f"❌ 任务失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
