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
    """生成自选股分析报告"""
    if not results:
        return "📊 今日无自选股分析数据"
    
    report = "## 📈 自选股分析报告\n\n"
    
    for stock in results:
        name = stock.get('name', stock.get('code', '未知'))
        code = stock.get('code', '未知')
        price = stock.get('current_price', stock.get('close', 'N/A'))
        pct_chg = stock.get('pct_chg', 'N/A')
        prediction = stock.get('ai_prediction', '暂无AI分析')
        
        # 确保 prediction 不为空
        if not prediction or prediction == "暂无AI分析":
            prediction = f"当前价: {price}, 涨跌幅: {pct_chg}%"
        
        report += f"### {name}({code})\n"
        report += f"**分析**: {prediction}\n\n"
    
    # 添加统计信息
    report += f"---\n📊 **统计**\n"
    report += f"- 分析股票: {len(results)} 只\n"
    report += f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    
    # 长度限制
    max_length = 4000
    if len(report) > max_length:
        report = report[:max_length] + "...\n(内容过长，已截断)"
    
    return report


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("🚀 股票分析系统 - 自选股分析")
    logger.info("=" * 60)

    config = get_config()

    warnings = config.validate()
    if warnings:
        for w in warnings:
            logger.warning(w)

    # 创建必要目录
    os.makedirs('reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    try:
        # 初始化组件
        data_loader = DataLoader(config)
        ai_engine = AIEngine(config)
        stock_analyzer = StockAnalyzer(data_loader, ai_engine, config)
        notifier = Notifier(config)

        logger.info("✅ 组件初始化成功")

        # 只分析自选股
        all_results = []
        if config.stock_list:
            logger.info(f"📈 分析自选股: {len(config.stock_list)} 只")
            all_results = stock_analyzer.analyze_stocks(config.stock_list)
            
            if not all_results:
                logger.warning("⚠️ 没有获取到任何股票数据")
                all_results = []

        # 生成报告
        report = create_report(all_results)
        logger.info(f"📄 生成报告长度: {len(report)} 字符")

        # 保存报告
        report_date = datetime.now().strftime("%Y%m%d")
        report_file = f"reports/report_{report_date}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"💾 报告已保存: {report_file}")

        # 推送通知
        title = f"📈 股票分析报告 {datetime.now().strftime('%m-%d %H:%M')}"
        notifier.send_all(title, report)
        logger.info("📤 推送完成")

        return True

    except Exception as e:
        logger.error(f"❌ 任务失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
