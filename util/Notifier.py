from abc import ABC, abstractmethod
import threading
import loguru
import time
from dataclasses import dataclass
from typing import Optional

class NotifierBase(ABC):
    """
    循环通知发送基类，使用请实现send_message方法
    """
    def __init__(
        self,
        title:str,
        content:str,
        interval_seconds=10,
        duration_minutes=10 #B站订单保存上限
    ):
        super().__init__()
        self.title = title
        self.content = content
        self.interval_seconds = interval_seconds
        self.duration_minutes = duration_minutes
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=False)

    def run(self):
        """线程运行函数，实现间隔发送通知"""
        start_time = time.time()
        end_time = start_time + (self.duration_minutes * 60)
        count = 0

        while time.time() < end_time and not self.stop_event.is_set():
            try:
                # 构建消息内容，包含剩余时间
                remaining_minutes = int((end_time - time.time()) / 60)
                remaining_seconds = int((end_time - time.time()) % 60)
                message = f"{self.content} [#{count}, 剩余 {remaining_minutes}分{remaining_seconds}秒]"

                # 使用send_message方法发送
                self.send_message(self.title, message)
                # 确认发送成功后停止发送
                break 

            except Exception as e:
                loguru.logger.error(f"通知发送失败: {e}")
                time.sleep(self.interval_seconds)  # 发生错误时等待重试

        loguru.logger.info(f"通知发送成功")
    
    def start(self):
        if not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.run, daemon=False)
            self.thread.start()
    
    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3)

    @abstractmethod
    def send_message(self, title, message):
        """用于发送消息，子类必须实现此方法发送推送消息"""
        pass

@dataclass
class NotifierConfig:
    """推送配置统一管理"""
    serverchan_key: Optional[str] = None
    serverchan3_api_url: Optional[str] = None
    pushplus_token: Optional[str] = None
    bark_token: Optional[str] = None
    ntfy_url: Optional[str] = None
    ntfy_username: Optional[str] = None
    ntfy_password: Optional[str] = None
    audio_path: Optional[str] = None
    
    @classmethod
    def from_config_db(cls):
        """从ConfigDB加载配置"""
        from util import ConfigDB
        return cls(
            serverchan_key=ConfigDB.get("serverchanKey"),
            serverchan3_api_url=ConfigDB.get("serverchan3ApiUrl"),
            pushplus_token=ConfigDB.get("pushplusToken"),
            bark_token=ConfigDB.get("barkToken"),
            ntfy_url=ConfigDB.get("ntfyUrl"),
            ntfy_username=ConfigDB.get("ntfyUsername"),
            ntfy_password=ConfigDB.get("ntfyPassword"),
            audio_path=ConfigDB.get("audioPath")
        )

class NotifierManager():
    def __init__(self):
        self.notifier_dict:dict[str,NotifierBase] = {}

    def regiseter_notifier(self, name:str, notifer:NotifierBase):
        if name in self.notifier_dict:
            loguru.logger.error(f"推送器添加失败: 已存在名为{name}的推送器")
        else:
            self.notifier_dict[name] = notifer
            loguru.logger.info(f"成功添加推送器: {name}")
    
    def remove_notifier(self, name:str):
        if name in self.notifier_dict:
            loguru.logger.error(f"推送器删除失败: 不存在名为{name}的推送器")
        else:
            self.notifier_dict.pop(name)
            loguru.logger.info(f"成功删除推送器: {name}")
    
    def start_all(self):
        for notifer in self.notifier_dict.values():
            notifer.start()

    def stop_all(self):
        for notifer in self.notifier_dict.values():
            notifer.stop()

    def start_notifer(self, name: str):
        notifer = self.notifier_dict.get(name)
        if notifer:
            notifer.start()
        else:
            loguru.logger.error(f"推送器启动失败: 不存在名为{name}的推送器")

    def stop_notifer(self, name: str):
        notifer = self.notifier_dict.get(name)
        if notifer:
            notifer.stop()
        else:
            loguru.logger.error(f"推送器停止失败: 不存在名为{name}的推送器")
    
    def list_notifers(self):
        return list(self.notifier_dict.keys())

    @staticmethod
    def create_from_config(config: NotifierConfig, title: str, content: str, 
                          interval_seconds: int = 10, duration_minutes: int = 10) -> 'NotifierManager':
        """通过配置创建NotifierManager，统一的工厂方法"""
        manager = NotifierManager()
        
        # ServerChan Turbo
        if config.serverchan_key:
            try:
                from util.ServerChanUtil import ServerChanTurboNotifier
                notifier = ServerChanTurboNotifier(
                    token=config.serverchan_key,
                    title=title,
                    content=content,
                    interval_seconds=interval_seconds,
                    duration_minutes=duration_minutes
                )
                manager.regiseter_notifier("ServerChanTurbo", notifier)
            except ImportError as e:
                loguru.logger.error(f"ServerChanTurbo导入失败: {e}")
            except Exception as e:
                loguru.logger.error(f"ServerChanTurbo创建失败: {e}")

        # ServerChan3
        if config.serverchan3_api_url:
            try:
                from util.ServerChanUtil import ServerChan3Notifier
                notifier = ServerChan3Notifier(
                    api_url=config.serverchan3_api_url,
                    title=title,
                    content=content,
                    interval_seconds=interval_seconds,
                    duration_minutes=duration_minutes
                )
                manager.regiseter_notifier("ServerChan3", notifier)
            except ImportError as e:
                loguru.logger.error(f"ServerChan3导入失败: {e}")
            except Exception as e:
                loguru.logger.error(f"ServerChan3创建失败: {e}")

        # PushPlus
        if config.pushplus_token:
            try:
                from util.PushPlusUtil import PushPlusNotifier
                notifier = PushPlusNotifier(
                    token=config.pushplus_token,
                    title=title,
                    content=content,
                    interval_seconds=interval_seconds,
                    duration_minutes=duration_minutes
                )
                manager.regiseter_notifier("PushPlus", notifier)
            except ImportError as e:
                loguru.logger.error(f"PushPlus导入失败: {e}")
            except Exception as e:
                loguru.logger.error(f"PushPlus创建失败: {e}")

        # Bark
        if config.bark_token:
            try:
                from util.BarkUtil import BarkNotifier
                notifier = BarkNotifier(
                    token=config.bark_token,
                    title=title,
                    content=content,
                    interval_seconds=interval_seconds,
                    duration_minutes=duration_minutes
                )
                manager.regiseter_notifier("Bark", notifier)
            except ImportError as e:
                loguru.logger.error(f"Bark导入失败: {e}")
            except Exception as e:
                loguru.logger.error(f"Bark创建失败: {e}")

        # Ntfy
        if config.ntfy_url:
            try:
                from util.NtfyUtil import NtfyNotifier
                notifier = NtfyNotifier(
                    url=config.ntfy_url,
                    username=config.ntfy_username,
                    password=config.ntfy_password,
                    title=title,
                    content=content,
                    interval_seconds=interval_seconds,
                    duration_minutes=duration_minutes
                )
                manager.regiseter_notifier("Ntfy", notifier)
            except ImportError as e:
                loguru.logger.error(f"Ntfy导入失败: {e}")
            except Exception as e:
                loguru.logger.error(f"Ntfy创建失败: {e}")

        # Audio
        if config.audio_path:
            try:
                from util.AudioUtil import AudioNotifier
                notifier = AudioNotifier(
                    audio_path=config.audio_path,
                    title=title,
                    content=content,
                    interval_seconds=interval_seconds,
                    duration_minutes=duration_minutes
                )
                manager.regiseter_notifier("Audio", notifier)
            except ImportError as e:
                loguru.logger.error(f"Audio导入失败: {e}")
            except Exception as e:
                loguru.logger.error(f"Audio创建失败: {e}")

        return manager

    @staticmethod
    def test_all_notifiers() -> str:
        """测试所有已配置的推送渠道"""
        config = NotifierConfig.from_config_db()
        results = []
        
        # 使用统一的工厂方法创建测试管理器
        test_manager = NotifierManager.create_from_config(
            config=config,
            title="抢票提醒",
            content="测试推送"
        )
        
        # 测试每个已配置的推送渠道
        test_cases = [
             ("ServerChanTurbo", config.serverchan_key, "Server酱ᵀᵘʳᵇᵒ"),
             ("ServerChan3", config.serverchan3_api_url, "Server酱³"),
             ("PushPlus", config.pushplus_token, "PushPlus"),
             ("Bark", config.bark_token, "Bark"),
             ("Ntfy", config.ntfy_url, "Ntfy"),
             ("Audio", config.audio_path, "音频通知")
        ]
        
        for notifier_name, config_value, display_name in test_cases:
            if not config_value:
                results.append(f"⚠️ {display_name}: 未配置")
                continue
                
            if notifier_name in test_manager.notifier_dict:
                try:
                    notifier = test_manager.notifier_dict[notifier_name]
                    notifier.send_message("🎫 抢票测试", f"这是一条{display_name}测试推送消息")
                    results.append(f"✅ {display_name}: 测试推送已发送")
                except Exception as e:
                    results.append(f"❌ {display_name}: 推送失败 - {str(e)}")
            else:
                results.append(f"❌ {display_name}: 创建失败")
        
        return "\n".join(results)