#!/usr/bin/env python3
"""
A股股票分析系统 - 升级版
增强功能：
1. 全市场扫描精选股票
2. 技术指标分析（MACD、KDJ、RSI、布林带）
3. 资金流向追踪
4. AI专业分析框架
5. 精选8只优质股票
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
    
    logger.info("=" * 60)
    logger.info("🚀 股票分析系统 v2.0 - 升级版")
    logger.info("=" * 60)
    
    # 加载配置
    config = Config.load()
    
    # 验证配置
    errors = config.validate()
    if errors:
        logger.error("配置错误:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info(f"AI模型: {config.ai.model}")
    logger.info(f"报告类型: {config.runtime.report_type.value}")
    
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
        
        # ========== 升级版核心功能 ==========
        
        all_results = []
        
        # 1. 分析自选股票（如果有配置）
        if config.runtime.stock_list:
            logger.info(f"📈 第一部分：分析自选股 {len(config.runtime.stock_list)} 只")
            logger.info(f"股票列表: {', '.join(config.runtime.stock_list)}")
            
            results = stock_analyzer.analyze_stocks(config.runtime.stock_list)
            all_results.extend(results)
            
            success_count = sum(1 for r in results if 'error' not in r)
            logger.info(f"✅ 自选股分析完成: {success_count}/{len(results)} 成功")
        
        # 2. 精选股票分析（升级版核心功能）
        if config.runtime.enable_selection:
            selected_count = getattr(config.runtime, 'selection_count', 8)
            logger.info(f"🎯 第二部分：精选市场优质股票（目标: {selected_count}只）")
            
            selected_results = stock_analyzer.select_and_analyze(count=selected_count)
            
            if selected_results:
                # 标记为精选股
                for r in selected_results:
                    r['is_selected'] = True
                
                all_results.extend(selected_results)
                logger.info(f"✅ 精选完成，共 {len(selected_results)} 只")
            else:
                logger.warning("⚠️ 精选功能未返回结果")
        
        # 统计总结果
        total = len(all_results)
        success = sum(1 for r in all_results if 'error' not in r)
        selected = sum(1 for r in all_results if r.get('is_selected', False))
        
        logger.info(f"📊 总计：分析 {total} 只股票，成功 {success} 只（包含 {selected} 只精选）")
        
        # 3. 获取大盘数据
        market_data = data_loader.get_market_index()
        
        # 4. 生成报告
        report_content = create_report(all_results, market_data)
        
        # 保存报告
        report_date = datetime.now().strftime("%Y%m%d")
        report_file = f"reports/report_{report_date}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"📄 报告已保存: {report_file}")
        
        # 5. 发送通知
        notification_title = f"📈 股票分析 {datetime.now().strftime('%m-%d')}"
        notification_content = f"分析完成\n"
        notification_content += f"- 自选股: {success}/{len(config.runtime.stock_list) if config.runtime.stock_list else 0} 成功\n"
        if selected > 0:
            notification_content += f"- 精选股: {selected} 只\n"
        notification_content += f"- 总计: {total} 只"
        
        notifier.send_all(notification_title, notification_content)
        
        logger.info("✅ 所有任务完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 分析过程出错: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
