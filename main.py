from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Plain
import datetime
import asyncio

@register("astrbot_plugin_timer", "adx", "定时任务插件", "1.0.0")
class Timer(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.raw_tasks = self.config.get("tasks")
        self.switch = self.config.get("switch", False) 
        self.sleep_time = self.config.get("sleep_time",30)
        self.cmd_list = []
        self.time_list = []
        self.umo_list = []
    
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("timer start")
    async def reminder_loop(self, event: AstrMessageEvent):
        """启动定时任务循环"""
        if self.switch :
            yield event.plain_result("定时任务已经启动过了")
            return
        self.switch = True
        self.config["switch"] = True
        self.cmd_list = []
        self.time_list = []
        try:
            for i in self.raw_tasks :
                args = i.split("|")
                if len(args) == 2:
                    self.cmd_list.append(args[0])
                    self.time_list.append(args[1])
                else:
                    logger.error(f"定时任务配置不合法,已跳过：{str(i)}")
        except Exception as e:
            logger.error(f"定时任务配置异常：{str(e)}")
            yield event.plain_result(f"定时任务配置异常：{str(e)}")
            return

        logger.info(f"定时任务已启动，共 {len(self.cmd_list)} 个任务。{str(self.cmd_list)}")
        yield event.plain_result(f"定时任务已启动，共 {len(self.cmd_list)} 个任务")
        while self.switch:
            try:
                now = datetime.datetime.now()
                # 匹配时分，忽略秒数（解决精度问题）
                now_time = now.strftime("%H:%M")
                if now_time in self.time_list:
                     # 构造消息
                    idx = self.time_list.index(now_time)
                    event.message_obj.message.clear()
                    event.message_obj.message.append(Plain(self.cmd_list[idx]))
                    event.message_obj.message_str = self.cmd_list[idx]
                    event.message_str = self.cmd_list[idx]
                    self.context.get_event_queue().put_nowait(event)
                    event.should_call_llm(True)
                    logger.info(f"定时任务执行成功:{self.cmd_list[idx]}-{now_time}")
                    # 触发后休眠60秒，避免同一分钟重复触发
                    await asyncio.sleep(60)                  
                await asyncio.sleep(self.sleep_time)      
            except Exception as e:
                    logger.error(f"定时任务执行异常：{str(e)}", exc_info=True)
                    await asyncio.sleep(10)  # 异常时休眠10秒，避免频繁报错

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("timer stop")
    async def stop_timer(self, event: AstrMessageEvent):
        """停止定时任务"""
        self.switch = False
        self.cmd_list = []
        self.time_list = []
        self.config["switch"] = False
        logger.info("定时任务已停止")
        yield event.plain_result("定时任务已停止")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("timer stat")
    async def reminder_list(self, event: AstrMessageEvent):
        """定时器状态"""
        if self.switch :
            stat = "定时器状态：运行中✅"
        else:
            stat = "定时器状态：未运行💤"
        for i in range(len(self.cmd_list)):
            stat = (f"{stat}\n"
                    f"{i+1}.{self.cmd_list[i]}--{self.time_list[i]}\n")
        yield event.plain_result(f"{stat}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("timer add")
    async def add_task(self, event: AstrMessageEvent):
        """新增定时任务"""
        message_str = event.message_str.strip().split() 
        num = 0 
        try:
            for i in message_str :
                args = i.split("|")
                if len(args) == 2:
                    self.raw_tasks.append(i)
                    num+=1
                else:
                    logger.error(f"定时任务配置不合法,已跳过：{str(i)}")
        except Exception as e:
            logger.error(f"定时任务配置异常：{str(e)}")
            yield event.plain_result(f"定时任务配置异常：{str(e)}")
            return
        self.config["tasks"] = self.raw_tasks
        yield event.plain_result(f"新增定时任务 {num} 项")
        
    async def initialize(self):
        """插件初始化（可选）"""
        pass

    async def terminate(self):
        """插件销毁时终止定时任务"""
        self.switch=False  # 取消任务
        logger.info("定时任务已终止")