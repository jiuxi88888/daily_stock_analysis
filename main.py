#!/usr/bin/env python3
""" A股股票分析系统 - 升级版 v2.0 """
import os
import sys
import logging
from datetime import datetime

# 导入模块
from config import get_config
from data_loader import DataLoader
from analyzer import StockAnalyzer, AIEngine
from notifier import Notifier

def setup_logging():
    """设置日志"""
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"analysis_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def create_report(results: list, market_data: dict) -> str:
    """生成精简版分析报告（适配 PushPlus）"""
    today = datetime.now().strftime('%Y-%m-%d')
    report = f"# 📈 A股分析日报 {today}\n\n"

    # 1. 大盘概览
    if market_data:
        sz = market_data.get('000001', {})
        sz2 = market_data.get('399001', {})
        cy = market_data.get('399006', {})
        report += "| 指数 | 涨跌幅 |\n"
        report += "| :--- | :--- |\n"
        report += f"| 上证指数 | {sz.get('pct_change', 'N/A')}% |\n"
        report += f"| 深证成指 | {sz2.get('pct_change', 'N/A')}% |\n"
        report += f"| 创业板指 | {cy.get('pct_change', 'N/A')}% |\n\n"

    # 2. 自选股（非精选）
    self_stocks = [r for r in results if not r.get('is_selected', False)]
    if self_stocks:
        report += "## 📌 自选股\n\n"
        report += "| 代码 | 名称 | 评分 | 决策 | 涨幅% |\n"
        report += "| :--- | :--- | :--- | :--- | :--- |\n"
        for r in self_stocks[:6]:
            if 'error' in r:
                continue
            report += (
                f"| {r.get('code')} "
                f"| {r.get('name', '-')} "
                f"| {r.get('ai_score', 0)} "
                f"| {r.get('decision', 'N/A')} "
                f"| {r.get('change_percent', 0):+.2f}% |\n"
            )
        report += "\n"

    # 3. 精选股票
    selected = [r for r in results if r.get('is_selected', False)]
    if selected:
        report += "## 🎯 精选股票\n\n"
        report += "| 代码 | 名称 | 评分 | 决策 | 精选理由 |\n"
        report += "| :--- | :--- | :--- | :--- | :--- |\n"
        for r in selected:
            reason = r.get('selection_reason', '-')
            report += (
                f"| {r.get('code')} "
                f"| {r.get('name', '-')} "
                f"| {r.get('ai_score', 0)} "
                f"| {r.get('decision', 'N/A')} "
                f"| {reason} |\n"
            )
        report += "\n"

    report += f"---\n"
    report += f"📊 自选股: {len(self_stocks)} 只 | 精选股: {len(selected)} 只\n"
    report += f"*生成时间: {datetime.now().strftime('%H:%M')}*"
    return report

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("🚀 股票分析系统 v2.0 - 升级版")
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

        if config.stock_list:
            logger.info(f"📈 分析自选股: {len(config.stock_list)} 只")
            self_results = stock_analyzer.analyze_stocks(config.stock_list)
            all_results.extend(self_results)
            logger.info(f"✅ 自选股完成: {len([r for r in self_results if 'error' not in r])}/{len(self_results)}")

        enable_selection = config.enable_selection
        selection_count = config.selection_count

        if enable_selection:
            logger.info(f"🎯 精选股票（目标: {selection_count}只）")
            selected_results = stock_analyzer.select_and_analyze(count=selection_count)
            if selected_results:
                all_results.extend(selected_results)
                logger.info(f"✅ 精选完成: {len(selected_results)} 只")
        else:
            logger.warning("⚠️ 精选功能未开启")

        logger.info("📊 获取大盘数据...")
        market_data = data_loader.get_market_index()

        logger.info("📝 生成报告...")
        report_content = create_report(all_results, market_data)

        report_date = datetime.now().strftime("%Y%m%d")
        report_file = f"reports/report_{report_date}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.info(f"✅ 报告已保存: {report_file}")

        total = len(all_results)
        success = len([r for r in all_results if 'error' not in r])
        selected_count = len([r for r in all_results if r.get('is_selected', False)])

        title = f"📈 股票分析 {datetime.now().strftime('%m-%d')}"
        content = f"分析完成\n- 自选股: {success}/{len(config.stock_list)} 成功\n"
        if selected_count > 0:
            content += f"- 精选股: {selected_count} 只\n"
        content += f"- 总计: {total} 只"

        notifier.send_all(title, content)
        logger.info("✅ 所有任务完成")

        return True

    except Exception as e:
        logger.error(f"❌ 任务失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
