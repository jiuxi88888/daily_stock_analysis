"""
通知模块 - 适配便携AI版本
"""
import logging
import requests
import json
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class Notifier:
    """通知管理器"""
    
    def __init__(self, config):
        self.config = config.notification
    
    def send_pushplus(self, title: str, content: str) -> bool:
        """发送PushPlus通知"""
        if not self.config.pushplus_token:
            return False
        
        try:
            url = "http://www.pushplus.plus/send"
            data = {
                "token": self.config.pushplus_token,
                "title": title,
                "content": content,
                "template": "markdown"
            }
            
            response = requests.post(
                url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    logger.info("✅ PushPlus通知发送成功")
                    return True
                else:
                    logger.error(f"❌ PushPlus发送失败: {result.get('msg')}")
            else:
                logger.error(f"❌ PushPlus请求失败: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ PushPlus异常: {e}")
        
        return False
    
    def send_wechat(self, title: str, content: str) -> bool:
        """发送企业微信通知"""
        if not self.config.wechat_webhook_url:
            return False
        
        try:
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"**{title}**\n\n{content}"
                }
            }
            
            response = requests.post(
                self.config.wechat_webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ 企业微信通知发送成功")
                return True
            else:
                logger.error(f"❌ 企业微信发送失败: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ 企业微信异常: {e}")
        
        return False
    
    def send_all(self, title: str, content: str) -> Dict[str, bool]:
        """发送所有通知"""
        results = {
            "pushplus": self.send_pushplus(title, content),
            "wechat": self.send_wechat(title, content)
        }
        return results
