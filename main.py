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


# ================= 报告生成 =================
def create_normal_report(results):
    if not results:
        return "📊 今日无自选股分析数据"

    report = "## 📈 自选股分析报告\n\n"
    for s in results:
        name = s.get("name", "未知")
        code = s.get("code", "未知")
        prediction = s.get("ai_prediction", "").strip() or "暂无分析"

        report += f"### {name}({code})\n{prediction}\n\n"

    report += f"---\n📊 共分析 {len(results)} 只股票"
    return report[:4000]


def create_selection_report(selections):
    if not selections:
        return None

    report = "## 🎯 精选 Top 股票（技术面最优）\n\n"
    for s in selections:
        name = s.get("name", "未知")
        code = s.get("code", "未知")
        score = s.get("technical", {}).get("score", "N/A")
        prediction = s.get("ai_prediction", "").strip() or "暂无分析"

        report += f"### {name}({code})｜技术评分：{score}\n{prediction}\n\n"

    report += f"---\n📌 以上为系统自动筛选，不构成投资建议"
    return report[:4000]


# ================= 主流程 =================
def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("🚀 股票分析系统")
    logger.info("=" * 60)

    config = get_config()
    for w in config.validate():
        logger.warning(w)

    os.makedirs('reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    try:
        data_loader = DataLoader(config)
        ai_engine = AIEngine(config)
        analyzer = StockAnalyzer(data_loader, ai_engine, config)
        notifier = Notifier(config)

        # 1️⃣ 分析自选股
        logger.info(f"📈 分析自选股: {len(config.stock_list)} 只")
        all_results = analyzer.analyze_stocks(config.stock_list)

        if not all_results:
            logger.warning("⚠️ 没有获取到任何股票数据")
            return False

        # 2️⃣ 生成自选股报告
        normal_report = create_normal_report(all_results)
        notifier.send_all("📈 自选股分析", normal_report)

        # 3️⃣ 精选股票（单独推送）
        selections = analyzer.select_top_stocks(all_results)
        if selections:
            selection_report = create_selection_report(selections)
            if selection_report:
                notifier.send_all("🎯 精选 Top 股票", selection_report)
                logger.info(f"✅ 精选推送完成（{len(selections)} 只）")

        # 4️⃣ 保存文件
        today = datetime.now().strftime("%Y%m%d")
        with open(f"reports/report_{today}.md", "w", encoding="utf-8") as f:
            f.write(normal_report)

        logger.info("✅ 全部完成")
        return True

    except Exception as e:
        logger.error(f"❌ 任务失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
