"""Telegram 服务

封装 Telegram Bot API 相关功能
"""

import asyncio
import logging
from typing import Literal

import httpx

from auperator.config import settings
from auperator.events import EventCenter
from auperator.schemas.event import EventType


logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram 服务类

    提供发送消息、消费者任务等功能
    """

    def __init__(self, event_center: EventCenter):
        """初始化 Telegram 服务

        Args:
            event_center: 事件中心
        """
        self.event_center = event_center
        self._consumer_task: asyncio.Task | None = None

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Literal["Markdown", "HTML", "None"] = "Markdown"
    ) -> bool:
        """发送消息到 Telegram

        Args:
            chat_id: Telegram 聊天 ID
            text: 消息文本
            parse_mode: 解析模式 (Markdown/HTML/None)

        Returns:
            bool: 发送是否成功
        """
        if not settings.telegram_bot_token:
            logger.warning("⚠️ Telegram Bot Token 未配置，无法发送消息")
            return False

        try:
            telegram_api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

            # 消息长度限制：Telegram 限制 4096 字符
            max_length = 4096
            if len(text) > max_length:
                # 分片发送
                chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]
                for i, chunk in enumerate(chunks, 1):
                    payload = {
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": parse_mode if parse_mode != "None" else None,
                    }
                    async with httpx.AsyncClient() as client:
                        response = await client.post(telegram_api_url, json=payload, timeout=10.0)
                        result = response.json()

                        if not result.get("ok"):
                            logger.error(f"❌ 发送 Telegram 消息失败 (chunk {i}/{len(chunks)}): {result}")
                            return False

                        logger.debug(f"✅ Telegram 消息已发送 (chunk {i}/{len(chunks)}): chat_id={chat_id}")
            else:
                # 单次发送
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode if parse_mode != "None" else None,
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post(telegram_api_url, json=payload, timeout=10.0)
                    result = response.json()

                    if not result.get("ok"):
                        logger.error(f"❌ 发送 Telegram 消息失败: {result}")
                        return False

                    logger.debug(f"✅ Telegram 消息已发送: chat_id={chat_id}, text={text[:50]}...")

            return True

        except Exception as e:
            logger.exception(f"❌ 发送 Telegram 消息异常: {e}")
            return False

    async def set_webhook(self, webhook_url: str, secret_token: str | None = None) -> dict:
        """设置 Telegram Webhook

        Args:
            webhook_url: Webhook URL
            secret_token: 可选的密钥令牌，用于验证请求

        Returns:
            dict: Telegram API 响应
            {
                "ok": bool,
                "result": bool,
                "description": str
            }
        """
        if not settings.telegram_bot_token:
            return {
                "ok": False,
                "error": "Telegram Bot Token 未配置"
            }

        try:
            telegram_api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"

            payload = {"url": webhook_url}
            if secret_token:
                payload["secret_token"] = secret_token

            async with httpx.AsyncClient() as client:
                response = await client.post(telegram_api_url, json=payload, timeout=10.0)
                result = response.json()

                if result.get("ok"):
                    logger.info(f"✅ Telegram Webhook 设置成功: {webhook_url}")
                    return {
                        "ok": True,
                        "result": True,
                        "description": result.get("description", "Webhook 设置成功"),
                        "webhook_url": webhook_url
                    }
                else:
                    logger.error(f"❌ Telegram Webhook 设置失败: {result}")
                    return {
                        "ok": False,
                        "error": result.get("description", "Unknown error")
                    }

        except Exception as e:
            logger.exception(f"❌ 设置 Telegram Webhook 异常: {e}")
            return {
                "ok": False,
                "error": str(e)
            }

    async def get_webhook_info(self) -> dict:
        """获取 Telegram Webhook 信息

        Returns:
            dict: Webhook 信息
            {
                "ok": bool,
                "url": str | None,
                "has_custom_certificate": bool,
                "pending_update_count": int
            }
        """
        if not settings.telegram_bot_token:
            return {
                "ok": False,
                "error": "Telegram Bot Token 未配置"
            }

        try:
            telegram_api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getWebhookInfo"

            async with httpx.AsyncClient() as client:
                response = await client.get(telegram_api_url, timeout=10.0)
                result = response.json()

                if result.get("ok"):
                    return {
                        "ok": True,
                        **result.get("result", {})
                    }
                else:
                    return {
                        "ok": False,
                        "error": result.get("description", "Unknown error")
                    }

        except Exception as e:
            logger.exception(f"❌ 获取 Webhook 信息异常: {e}")
            return {
                "ok": False,
                "error": str(e)
            }

    def get_config_info(self) -> dict:
        """获取 Telegram 配置信息

        Returns:
            dict: 配置信息
        """
        bot_token = settings.telegram_bot_token
        webhook_url = settings.telegram_webhook_url

        # 脱敏处理
        masked_token = f"{bot_token[:7]}...{bot_token[-4:]}" if bot_token and len(bot_token) > 11 else "***"

        return {
            "bot_token": masked_token,
            "webhook_url": webhook_url,
            "is_configured": bool(bot_token),
            "webhook_set": bool(webhook_url),
        }

    async def _run_consumer(self):
        """Telegram 消息消费者任务（内部方法）

        监听 AGENT 事件并发送到 Telegram
        """
        if not settings.telegram_bot_token:
            logger.warning("⚠️ Telegram Bot Token 未配置，Telegram 消费者未启动")
            return

        logger.info("🚀 启动 Telegram 消息消费者")

        try:
            async for event in self.event_center.consume("telegram"):
                # 只处理 AGENT 事件
                if event.event_type != EventType.AGENT:
                    continue

                # 直接使用 thread_id 作为 chat_id（thread_id 就是 str(chat_id)）
                try:
                    chat_id = int(event.thread_id)
                except (ValueError, TypeError):
                    logger.debug(f"⚠️ thread_id 不是有效的 chat_id: {event.thread_id}")
                    continue

                # 获取消息内容
                content = event.data.get("content", "")
                if not content:
                    continue

                # 特殊标记：[Done] 不发送
                if content == "[Done]":
                    continue

                logger.info(f"📤 发送 Agent 响应到 Telegram: chat_id={chat_id}, thread_id={event.thread_id}")

                # 发送到 Telegram
                await self.send_message(chat_id, content)

        except asyncio.CancelledError:
            logger.info("⏹️ Telegram 消费者已停止")
        except Exception as e:
            logger.exception(f"❌ Telegram 消费者异常: {e}")

    async def start_consumer(self):
        """启动 Telegram 消费者

        Returns:
            bool: 是否成功启动
        """
        if not settings.telegram_bot_token:
            logger.warning("⚠️ Telegram Bot Token 未配置")
            return False

        if self._consumer_task and not self._consumer_task.done():
            logger.warning("⚠️ Telegram 消费者已在运行")
            return False

        loop = asyncio.get_event_loop()
        self._consumer_task = loop.create_task(self._run_consumer())
        logger.info("✅ Telegram 消费者已启动")
        return True

    async def stop_consumer(self):
        """停止 Telegram 消费者

        Returns:
            bool: 是否成功停止
        """
        if not self._consumer_task or self._consumer_task.done():
            logger.warning("⚠️ Telegram 消费者未运行")
            return False

        self._consumer_task.cancel()
        try:
            await self._consumer_task
        except asyncio.CancelledError:
            pass

        logger.info("✅ Telegram 消费者已停止")
        return True

    def is_running(self) -> bool:
        """检查消费者是否在运行

        Returns:
            bool: 是否正在运行
        """
        return self._consumer_task is not None and not self._consumer_task.done()
