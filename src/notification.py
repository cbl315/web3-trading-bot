import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config):
        """
        初始化通知管理器
        
        Args:
            config (dict): 配置信息
        """
        self.config = config
        self.notification_config = config.get('notification', {})
        
    def send_email(self, subject, message):
        """
        发送邮件通知
        
        Args:
            subject (str): 邮件主题
            message (str): 邮件内容
        """
        email_config = self.notification_config.get('email', {})
        
        # 检查是否配置了邮件通知
        if not email_config.get('enabled', False):
            return
            
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = email_config.get('sender')
            msg['To'] = email_config.get('recipient')
            msg['Subject'] = subject
            
            # 添加邮件内容
            msg.attach(MIMEText(message, 'plain'))
            
            # 连接SMTP服务器并发送邮件
            server = smtplib.SMTP(email_config.get('smtp_server'), email_config.get('smtp_port'))
            server.starttls()
            server.login(email_config.get('username'), email_config.get('password'))
            server.send_message(msg)
            server.quit()
            
            logger.info(f"邮件通知已发送: {subject}")
        except Exception as e:
            logger.error(f"发送邮件通知失败: {str(e)}")
    
    def send_notification(self, title, message):
        """
        发送通知（支持多种通知方式）
        
        Args:
            title (str): 通知标题
            message (str): 通知内容
        """
        # 发送邮件通知
        self.send_email(title, message)
        
        # 记录到日志
        logger.info(f"通知 - {title}: {message}")