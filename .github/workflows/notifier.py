"""
通知模块 - 支持多种通知渠道
"""
import logging
import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class Notifier:
    """通知管理器"""
    
    def __init__(self, config):
        self.config = config.notification
        
    def send_all(self, title: str, content: str, report_type: str = "simple") -> Dict[str, bool]:
        """发送到所有配置的通知渠道"""
        results = {}
        
        # 企业微信
        if self.config.wechat_webhook_url:
            results["wechat"] = self._send_wechat(title, content)
        
        # 飞书
        if self.config.feishu_webhook_url:
            results["feishu"] = self._send_feishu(title, content)
        
        # Telegram
        if self.config.telegram_bot_token and self.config.telegram_chat_id:
            results["telegram"] = self._send_telegram(title, content)
        
        # 邮件
        if self.config.email_sender and self.config.email_password and self.config.email_receivers:
            results["email"] = self._send_email(title, content)
        
        # Pushover
        if self.config.pushover_user_key and self.config.pushover_api_token:
            results["pushover"] = self._send_pushover(title, content)
        
        # PushPlus
        if self.config.pushplus_token:
            results["pushplus"] = self._send_pushplus(title, content)
        
        # Discord
        if self.config.discord_webhook_url:
            results["discord"] = self._send_discord(title, content)
        
        # 自定义Webhook
        if self.config.custom_webhook_urls:
            results["custom_webhook"] = self._send_custom_webhook(title, content)
        
        # AstrBot
        if self.config.astrbot_url and self.config.astrbot_token:
            results["astrbot"] = self._send_astrbot(title, content)
        
        # Server酱3
        if self.config.serverchan3_sendkey:
            results["serverchan3"] = self._send_serverchan3(title, content)
        
        # 飞书云文档
        if self.config.feishu_app_id and self.config.feishu_app_secret and self.config.feishu_folder_token:
            results["feishu_doc"] = self._send_feishu_doc(title, content, report_type)
        
        return results
    
    def _send_wechat(self, title: str, content: str) -> bool:
        """发送企业微信通知"""
        try:
            if self.config.wechat_msg_type == "markdown":
                message = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": f"**{title}**\n\n{content}"
                    }
                }
            else:
                message = {
                    "msgtype": "text",
                    "text": {
                        "content": f"{title}\n\n{content}",
                        "mentioned_list": ["@all"]
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
                logger.error(f"❌ 企业微信通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 企业微信通知异常: {e}")
            return False
    
    def _send_feishu(self, title: str, content: str) -> bool:
        """发送飞书通知"""
        try:
            message = {
                "msg_type": "interactive",
                "card": {
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": f"**{title}**\n\n{content}"
                        }
                    ],
                    "header": {
                        "title": {
                            "content": "📈 股票分析报告",
                            "tag": "plain_text"
                        }
                    }
                }
            }
            
            response = requests.post(
                self.config.feishu_webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ 飞书通知发送成功")
                return True
            else:
                logger.error(f"❌ 飞书通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 飞书通知异常: {e}")
            return False
    
    def _send_telegram(self, title: str, content: str) -> bool:
        """发送Telegram通知"""
        try:
            import html
            
            # 转义HTML特殊字符
            escaped_content = html.escape(content)
            
            # 构建消息
            message = f"<b>{html.escape(title)}</b>\n\n{escaped_content}"
            
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            params = {
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            if self.config.telegram_message_thread_id:
                params["message_thread_id"] = self.config.telegram_message_thread_id
            
            response = requests.post(url, json=params, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Telegram通知发送成功")
                return True
            else:
                logger.error(f"❌ Telegram通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Telegram通知异常: {e}")
            return False
    
    def _send_email(self, title: str, content: str) -> bool:
        """发送邮件通知"""
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title
            msg['From'] = f"{self.config.email_sender_name} <{self.config.email_sender}>"
            msg['To'] = ', '.join(self.config.email_receivers)
            
            # 纯文本版本
            text_part = MIMEText(content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # HTML版本
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    h1 {{ color: #333; }}
                    .stock {{ margin: 10px 0; padding: 10px; background: #f5f5f5; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <pre>{content}</pre>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </body>
            </html>
            """
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:  # 以QQ邮箱为例
                server.login(self.config.email_sender, self.config.email_password)
                server.send_message(msg)
            
            logger.info("✅ 邮件通知发送成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 邮件通知发送失败: {e}")
            return False
    
    def _send_pushover(self, title: str, content: str) -> bool:
        """发送Pushover通知"""
        try:
            url = "https://api.pushover.net/1/messages.json"
            data = {
                "token": self.config.pushover_api_token,
                "user": self.config.pushover_user_key,
                "title": title,
                "message": content,
                "html": 1
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Pushover通知发送成功")
                return True
            else:
                logger.error(f"❌ Pushover通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Pushover通知异常: {e}")
            return False
    
    def _send_pushplus(self, title: str, content: str) -> bool:
        """发送PushPlus通知"""
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
                    logger.error(f"❌ PushPlus通知发送失败: {result.get('msg')}")
                    return False
            else:
                logger.error(f"❌ PushPlus通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ PushPlus通知异常: {e}")
            return False
    
    def _send_discord(self, title: str, content: str) -> bool:
        """发送Discord通知"""
        try:
            # 截断内容，避免过长
            if len(content) > 1500:
                content = content[:1500] + "..."
            
            message = {
                "embeds": [
                    {
                        "title": title,
                        "description": content,
                        "color": 0x00ff00,
                        "timestamp": datetime.now().isoformat(),
                        "footer": {
                            "text": "股票分析系统"
                        }
                    }
                ]
            }
            
            response = requests.post(
                self.config.discord_webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info("✅ Discord通知发送成功")
                return True
            else:
                logger.error(f"❌ Discord通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Discord通知异常: {e}")
            return False
    
    def _send_custom_webhook(self, title: str, content: str) -> bool:
        """发送自定义Webhook通知"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.config.custom_webhook_bearer_token:
                headers["Authorization"] = f"Bearer {self.config.custom_webhook_bearer_token}"
            
            message = {
                "title": title,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "source": "stock-analysis"
            }
            
            all_success = True
            for url in self.config.custom_webhook_urls:
                try:
                    response = requests.post(
                        url.strip(),
                        json=message,
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code not in [200, 201, 204]:
                        logger.error(f"❌ 自定义Webhook发送失败 ({url}): {response.text}")
                        all_success = False
                        
                except Exception as e:
                    logger.error(f"❌ 自定义Webhook异常 ({url}): {e}")
                    all_success = False
            
            if all_success:
                logger.info("✅ 自定义Webhook通知发送成功")
            return all_success
                
        except Exception as e:
            logger.error(f"❌ 自定义Webhook异常: {e}")
            return False
    
    def _send_astrbot(self, title: str, content: str) -> bool:
        """发送AstrBot通知"""
        try:
            # 这里需要根据AstrBot的API文档调整
            message = {
                "token": self.config.astrbot_token,
                "title": title,
                "message": content,
                "type": "markdown"
            }
            
            response = requests.post(
                self.config.astrbot_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ AstrBot通知发送成功")
                return True
            else:
                logger.error(f"❌ AstrBot通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ AstrBot通知异常: {e}")
            return False
    
    def _send_serverchan3(self, title: str, content: str) -> bool:
        """发送Server酱3通知"""
        try:
            url = f"https://sctapi.ftqq.com/{self.config.serverchan3_sendkey}.send"
            data = {
                "title": title,
                "desp": content
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    logger.info("✅ Server酱3通知发送成功")
                    return True
                else:
                    logger.error(f"❌ Server酱3通知发送失败: {result.get('message')}")
                    return False
            else:
                logger.error(f"❌ Server酱3通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Server酱3通知异常: {e}")
            return False
    
    def _send_feishu_doc(self, title: str, content: str, report_type: str) -> bool:
        """发送到飞书云文档"""
        try:
            # 先获取访问令牌
            token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            token_data = {
                "app_id": self.config.feishu_app_id,
                "app_secret": self.config.feishu_app_secret
            }
            
            token_response = requests.post(token_url, json=token_data, timeout=10)
            if token_response.status_code != 200:
                logger.error(f"❌ 获取飞书访问令牌失败: {token_response.text}")
                return False
            
            access_token = token_response.json().get("tenant_access_token")
            if not access_token:
                logger.error("❌ 获取飞书访问令牌失败")
                return False
            
            # 创建文档
            doc_url = "https://open.feishu.cn/open-apis/docx/v1/documents"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            doc_data = {
                "folder_token": self.config.feishu_folder_token,
                "title": title
            }
            
            doc_response = requests.post(doc_url, json=doc_data, headers=headers, timeout=10)
            if doc_response.status_code not in [200, 201]:
                logger.error(f"❌ 创建飞书文档失败: {doc_response.text}")
                return False
            
            doc_id = doc_response.json().get("data", {}).get("document", {}).get("document_id")
            if not doc_id:
                logger.error("❌ 获取飞书文档ID失败")
                return False
            
            # 更新文档内容
            update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}"
            update_data = {
                "requests": [
                    {
                        "replace_block": {
                            "block_id": doc_id,
                            "blocks": [
                                {
                                    "block_type": 2,  # 文本块
                                    "text": {
                                        "elements": [
                                            {
                                                "text_run": {
                                                    "content": content
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            
            update_response = requests.patch(update_url, json=update_data, headers=headers, timeout=10)
            if update_response.status_code == 200:
                logger.info("✅ 飞书云文档创建成功")
                return True
            else:
                logger.error(f"❌ 更新飞书文档内容失败: {update_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 飞书云文档异常: {e}")
            return False
