import asyncio
import logging
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv(
    "BOT_TOKEN", "8520132181:AAGli6V5x7flqkfognrwo91OfpCz61dlofQ"
)
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6259865244")


async def monitor():
    seen = set()
    logger.info("开始监控 Binance FAQ")
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=15)
    ) as session:
        while True:
            try:
                async with session.get(
                    "https://www.binance.com/bapi/apex/v1/public/apex/cms/article/list/query?type=2&pageNo=1&pageSize=50",
                    headers={
                        "accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "bnc-level": "0",
                        "bnc-location": "CN",
                        "bnc-time-zone": "Asia/Shanghai",
                        "clienttype": "web",
                        "content-type": "application/json",
                        "lang": "zh-CN",
                        "priority": "u=1, i",
                        "referer": "https://www.binance.com/zh-CN/support/faq/list/359",
                        "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"Windows"',
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "same-origin",
                        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                        "x-host": "www.binance.com",
                        "x-passthrough-token": "",
                    },
                ) as resp:
                    data = await resp.json()

                articles = []
                catalogs = data.get("data", {}).get("catalogs", [])[:]
                while catalogs:
                    catalog = catalogs.pop()
                    for article in catalog.get("articles") or []:
                        article["catalogName"] = catalog.get("catalogName", "")
                        articles.append(article)
                    catalogs.extend(catalog.get("catalogs") or [])

                if not seen:
                    seen = {
                        article["code"] for article in articles if article.get("code")
                    }
                    logger.info("首次启动，已记录 %s 条现有内容", len(seen))
                    latest = max(
                        articles, key=lambda x: x.get("releaseDate", 0), default=None
                    )
                    if latest and latest.get("code"):
                        logger.info(
                            "最近一条 FAQ: [%s] %s https://www.binance.com/zh-CN/support/faq/detail/%s",
                            latest.get("catalogName", ""),
                            latest.get("title", ""),
                            latest["code"],
                        )
                else:
                    new_articles = [
                        article
                        for article in articles
                        if article.get("code") and article["code"] not in seen
                    ]
                    if new_articles:
                        logger.info("发现 %s 条新增 FAQ", len(new_articles))
                    for article in sorted(
                        new_articles, key=lambda x: x.get("releaseDate", 0)
                    ):
                        async with session.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": CHAT_ID,
                                "text": f"Binance FAQ 新增内容如下\n分类: {article.get('catalogName', '')}\n标题: {article.get('title', '')}\n链接: https://www.binance.com/zh-CN/support/faq/detail/{article['code']}",
                                "disable_web_page_preview": True,
                            },
                        ) as resp:
                            await resp.json()
                        seen.add(article["code"])
                        logger.info("已发送: %s", article.get("title", ""))
            except Exception:
                logger.exception("监控 FAQ 失败")

            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(monitor())
