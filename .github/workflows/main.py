#!/usr/bin/env python3
"""
A股股票分析系统 - 适配便携AI
"""
import os
import sys
import logging
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data_loader import DataLoader
from analyzer import StockAnalyzer, AIEngine
from notifier import Notifier
from utils import setup_logging, create_report

def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("🚀 开始股票分析 (适配便携AI)")
    logger.info("=" * 50)
    
    # 加载配置
    config = Config.load()
    
    # 验证配置
    errors = config.validate()
    if errors:
        logger.error("配置错误:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info(f"分析股票: {config.runtime.stock_list}")
    logger.info(f"报告类型: {config.runtime.report_type.value}")
    logger.info(f"AI模型: {config.ai.model}")
    
    # 创建目录
    os.makedirs('reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    try:
        # 初始化组件
        data_loader = DataLoader(config)
        ai_engine = AIEngine(config)
        stock_analyzer = StockAnalyzer(data_loader, ai_engine, config)
        notifier = Notifier(config)
        
        logger.info("✅ 所有组件初始化成功")
        
        # 分析股票
        logger.info(f"📈 开始分析 {len(config.runtime.stock_list)} 只股票...")
        results = stock_analyzer.analyze_stocks(config.runtime.stock_list)
        
        # 统计结果
        success_count = sum(1 for r in results if 'error' not in r)
        logger.info(f"✅ 分析完成: {success_count}/{len(results)} 成功")
        
        # 获取大盘数据
        market_data = data_loader.get_market_index()
        
        # 生成报告
        report_content = create_report(results, market_data)
        
        # 保存报告
        report_date = datetime.now().strftime("%Y%m%d")
        report_file = f"reports/report_{report_date}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"📄 报告已保存: {report_file}")
        
        # 发送通知
        notification_title = f"📈 股票分析 {datetime.now().strftime('%m-%d')}"
        notification_content = f"分析完成: {success_count}/{len(results)} 成功"
        
        notifier.send_all(notification_title, notification_content)
        
        logger.info("✅ 所有任务完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 分析过程出错: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
