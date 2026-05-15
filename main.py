#!/usr/bin/env python3
""" A股股票分析系统 - 优化版：输出精选3只预测分析 """
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
    """
    优化：只拼接精选的 3 只股票的 AI 完整预测分析（未来走势/涨幅）
    不含大盘、不含评分、不含自选股列表等任何冗余文字
    """
    parts = []
    # 只取被标记为精选（Top 3）的结果
    for r in results:
        if r.get("is_selected"):
            name = r.get('name', r.get('code', ''))
            prediction = r.get("ai_prediction", "")
            if prediction and prediction != "分析暂时不可用":
                parts.append(f"## {name}\n{prediction}")

    if not parts:
        return "今日暂无符合技术条件的精选预测分析"
    
    # 直接返回纯净的预测内容
    return "\n\n---\n\n".join(parts)

def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("🚀 股票分析系统 - 精选 Top 3 预测优化版")
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

        # 1. 先分析自选股基础数据（供精选池使用）
        if config.stock_list:
            logger.info(f"📈 加载自选股: {len(config.stock_list)} 只")
            self_results = stock_analyzer.analyze_stocks(config.stock_list)
            all_results.extend(self_results)

        # 2. 精选 Top 3 只股票，并做 AI 未来走势/涨幅预测
        if config.enable_selection:
            logger.info("🎯 精选 Top 3 只股票，生成 AI 预测分析...")
            selected_results = stock_analyzer.select_and_analyze(count=3)
            all_results.extend(selected_results)
            logger.info(f"✅ 精选预测分析完成: {len(selected_results)} 只")
        else:
            logger.warning("⚠️ 精选功能未开启")

        # 3. 获取大盘数据（仅供 DataLoader 内部使用，不进报告）
        market_data = data_loader.get_market_index()

        # 4. 生成【只含 3 只股票预测分析】的纯净报告
        logger.info("📝 生成精选预测报告...")
        report_content = create_report(all_results, market_data)

        report_date = datetime.now().strftime("%Y%m%d")
        report_file = f"reports/report_{report_date}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.info(f"✅ 报告已保存: {report_file}")

        # 5. 推送标题简化，内容只发 AI 预测文本
        title = f"📈 精选预测分析 {datetime.now().strftime('%m-%d')}"
        notifier.send_all(title, report_content)
        logger.info("✅ 所有任务完成")

        return True

    except Exception as e:
        logger.error(f"❌ 任务失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
