#!/usr/bin/env python3
"""
A股股票分析系统 - 主程序
"""
import os
import sys
import logging
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data_loader import DataLoader
from analyzer import StockAnalyzer, MarketAnalyzer, AIEngine
from notifier import Notifier
from utils import setup_logging, export_to_json, format_stock_analysis, format_market_data

logger = logging.getLogger(__name__)

def main(market_review: bool = True):
    """主函数"""
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("🚀 A股自选股智能分析系统启动")
    logger.info("=" * 60)
    logger.info(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建必要目录
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # 加载配置
    try:
        config = Config.load()
        logger.info("✅ 配置加载成功")
        
        # 验证配置
        errors = config.validate()
        if errors:
            logger.error("❌ 配置验证失败:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info(f"📊 自选股列表: {config.runtime.stock_list}")
        logger.info(f"📝 报告类型: {config.runtime.report_type.value}")
        
    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        return False
    
    # 初始化组件
    try:
        data_loader = DataLoader(config)
        ai_engine = AIEngine(config)
        stock_analyzer = StockAnalyzer(data_loader, ai_engine, config)
        market_analyzer = MarketAnalyzer(data_loader, ai_engine, config)
        notifier = Notifier(config)
        logger.info("✅ 所有组件初始化成功")
        
    except Exception as e:
        logger.error(f"❌ 组件初始化失败: {e}")
        return False
    
    # 分析股票
    stock_results = []
    try:
        logger.info(f"📈 开始分析 {len(config.runtime.stock_list)} 只股票...")
        stock_results = stock_analyzer.analyze_stocks(config.runtime.stock_list)
        
        # 统计成功分析的数量
        success_count = sum(1 for r in stock_results if 'error' not in r)
        logger.info(f"✅ 股票分析完成: {success_count}/{len(stock_results)} 成功")
        
    except Exception as e:
        logger.error(f"❌ 股票分析失败: {e}")
        stock_results = []
    
    # 分析大盘
    market_result = None
    if market_review and config.runtime.market_review_enabled:
        try:
            logger.info("📊 开始大盘分析...")
            market_result = market_analyzer.analyze_market()
            if 'error' not in market_result:
                logger.info(f"✅ 大盘分析完成，市场情绪: {market_result.get('summary', {}).get('sentiment', '未知')}")
            else:
                logger.warning("⚠️  大盘分析失败")
        except Exception as e:
            logger.error(f"❌ 大盘分析失败: {e}")
    
    # 生成报告
    report_content = ""
    report_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # 报告头部
        report_content += f"# 📈 股票分析报告 {report_date}\n\n"
        report_content += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_content += f"分析股票: {', '.join(config.runtime.stock_list)}\n"
        report_content += f"报告类型: {config.runtime.report_type.value}\n\n"
        
        # 大盘分析
        if market_result and 'error' not in market_result:
            report_content += "## 📊 大盘概览\n\n"
            
            summary = market_result.get('summary', {})
            report_content += f"**市场情绪**: {summary.get('sentiment', '未知')}\n"
            report_content += f"**上涨指数**: {summary.get('rising_count', 0)} 个\n"
            report_content += f"**下跌指数**: {summary.get('falling_count', 0)} 个\n"
            report_content += f"**平均涨跌**: {summary.get('avg_change', 0):+.2f}%\n\n"
            
            # 指数详情
            indices = market_result.get('indices', {})
            for code, data in indices.items():
                pct = data.get('pct_change', 0)
                if pct > 0:
                    emoji = "📈"
                elif pct < 0:
                    emoji = "📉"
                else:
                    emoji = "➡️"
                
                report_content += f"{emoji} **{data.get('name', code)}**: {data.get('price', 0):.2f} ({pct:+.2f}%)\n"
            
            report_content += "\n"
            
            # AI分析
            if market_result.get('market_analysis'):
                report_content += "### 🤖 AI市场分析\n"
                report_content += f"{market_result.get('market_analysis', '')}\n\n"
        
        # 股票分析
        if stock_results:
            report_content += "## 📈 个股分析\n\n"
            
            for i, result in enumerate(stock_results, 1):
                if 'error' in result:
                    report_content += f"### {i}. {result.get('code', '未知')} - 分析失败\n"
                    report_content += f"错误: {result.get('error', '未知错误')}\n\n"
                else:
                    report_content += f"### {i}. {result.get('name', '未知')} ({result.get('code', '未知')})\n"
                    
                    # 实时数据
                    realtime = result.get('realtime', {})
                    pct_change = realtime.get('pct_change', 0)
                    
                    if pct_change > 0:
                        trend = "📈 上涨"
                    elif pct_change < 0:
                        trend = "📉 下跌"
                    else:
                        trend = "➡️ 平盘"
                    
                    report_content += f"**{trend}** {pct_change:+.2f}%\n\n"
                    report_content += f"- **当前价格**: ¥{realtime.get('price', 0):.2f}\n"
                    report_content += f"- **涨跌额**: ¥{realtime.get('change', 0):+.2f}\n"
                    report_content += f"- **成交量**: {realtime.get('volume', 0):,} 手\n"
                    report_content += f"- **成交额**: ¥{realtime.get('amount', 0):,.2f}\n"
                    report_content += f"- **开盘**: ¥{realtime.get('open', 0):.2f}\n"
                    report_content += f"- **最高**: ¥{realtime.get('high', 0):.2f}\n"
                    report_content += f"- **最低**: ¥{realtime.get('low', 0):.2f}\n"
                    report_content += f"- **昨收**: ¥{realtime.get('pre_close', 0):.2f}\n"
                    report_content += f"- **数据时间**: {realtime.get('time', '未知')}\n\n"
                    
                    # 技术分析
                    technical = result.get('technical', {})
                    if technical:
                        report_content += "**技术指标**:\n"
                        
                        if 'ma' in technical and technical['ma']:
                            ma_str = " | ".join([f"MA{period}: ¥{price:.2f}" for period, price in technical['ma'].items()])
                            report_content += f"- 移动平均线: {ma_str}\n"
                        
                        if 'macd' in technical and technical['macd']:
                            macd_data = technical['macd']
                            report_content += f"- MACD: {macd_data.get('signal', '')} (DIF={macd_data.get('dif', 0):.3f}, DEA={macd_data.get('dea', 0):.3f})\n"
                        
                        if 'rsi' in technical and technical['rsi'] is not None:
                            rsi_value = technical['rsi']
                            rsi_status = "超买" if rsi_value > 70 else "超卖" if rsi_value < 30 else "正常"
                            report_content += f"- RSI: {rsi_value:.1f} ({rsi_status})\n"
                        
                        if 'boll' in technical and technical['boll']:
                            boll_data = technical['boll']
                            report_content += f"- 布林带: {boll_data.get('signal', '')} (位置: {boll_data.get('position', 0)*100:.1f}%)\n"
                        
                        if 'volume' in technical and technical['volume']:
                            volume_data = technical['volume']
                            report_content += f"- 成交量: {volume_data.get('signal', '')} (量比: {volume_data.get('volume_ratio_5', 1):.2f})\n"
                        
                        report_content += "\n"
                    
                    # AI分析
                    if result.get('ai_analysis'):
                        report_content += "**AI分析**:\n"
                        report_content += f"{result.get('ai_analysis', '')}\n\n"
                    
                    # 分析摘要
                    if result.get('summary'):
                        report_content += f"**分析摘要**: {result.get('summary', '')}\n\n"
                    
                    report_content += "---\n\n"
        
        # 保存报告
        report_file = f"reports/stock_analysis_{report_date}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"📄 报告已保存: {report_file}")
        
        # 保存JSON数据
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "stocks": stock_results,
            "market": market_result
        }
        json_file = f"data/analysis_{report_date}.json"
        export_to_json(json_data, json_file)
        
    except Exception as e:
        logger.error(f"❌ 生成报告失败: {e}")
        report_content = f"❌ 报告生成失败: {e}"
    
    # 发送通知
    try:
        if config.runtime.report_type != "simple" or len(report_content) > 500:
            # 如果内容太长，发送精简版
            notification_content = f"📈 今日股票分析完成\n\n"
            
            if market_result and 'error' not in market_result:
                summary = market_result.get('summary', {})
                notification_content += f"📊 大盘: {summary.get('sentiment', '未知')} ({summary.get('avg_change', 0):+.2f}%)\n"
            
            for result in stock_results:
                if 'error' not in result:
                    realtime = result.get('realtime', {})
                    notification_content += f"{result.get('name', '')}: ¥{realtime.get('price', 0):.2f} ({realtime.get('pct_change', 0):+.2f}%) - {result.get('summary', '')}\n"
            
            notification_content += f"\n详细报告已保存，请查看完整分析。"
        else:
            notification_content = report_content
        
        # 发送通知
        title = f"📈 股票分析 {report_date}"
        notification_results = notifier.send_all(title, notification_content, config.runtime.report_type.value)
        
        # 统计通知结果
        success_notifications = sum(1 for v in notification_results.values() if v)
        total_notifications = len(notification_results)
        logger.info(f"📱 通知发送结果: {success_notifications}/{total_notifications} 成功")
        
    except Exception as e:
        logger.error(f"❌ 发送通知失败: {e}")
    
    # 统计运行时间
    elapsed_time = time.time() - start_time
    logger.info(f"⏱️  总运行时间: {elapsed_time:.2f} 秒")
    logger.info("✅ 分析完成")
    
    return True

if __name__ == "__main__":
    # 设置日志
    log_date = datetime.now().strftime("%Y%m%d")
    setup_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=f"logs/stock_analysis_{log_date}.log"
    )
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='A股股票分析系统')
    parser.add_argument('--no-market-review', action='store_true', 
                       help='不进行大盘复盘')
    parser.add_argument('--market-review', action='store_true',
                       help='仅进行大盘复盘')
    
    args = parser.parse_args()
    
    try:
        if args.market_review:
            logger.info("运行模式: 仅大盘复盘")
            # 这里可以调用专门的大盘分析函数
            main(market_review=True)
        elif args.no_market_review:
            logger.info("运行模式: 仅股票分析")
            main(market_review=False)
        else:
            logger.info("运行模式: 完整分析")
            main()
            
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 程序运行异常: {e}")
        sys.exit(1)
