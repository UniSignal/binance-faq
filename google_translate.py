import asyncio

import aiohttp

BASE_URL = "https://translate.googleapis.com/translate_a/single"


async def translate(
    session: aiohttp.ClientSession,
    text: str,
    *,
    source_lang: str = "auto",
    target_lang: str = "zh-CN",
    timeout_seconds: float = 10.0,
    retry_times: int = 2,
) -> str:
    if not text:
        return ""

    params = {
        "client": "gtx",
        "sl": source_lang,
        "tl": target_lang,
        "dt": "t",
        "q": text,
    }

    retry_times = max(1, retry_times)
    last_exc: Exception | None = None
    for attempt in range(1, retry_times + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            async with session.get(
                BASE_URL,
                params=params,
                timeout=timeout,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"unexpected status: {resp.status}")

                data = await resp.json(content_type=None)
                translated: str | None = None
                if isinstance(data, list) and data and isinstance(data[0], list):
                    out: list[str] = []
                    for part in data[0]:
                        if isinstance(part, list) and part and isinstance(part[0], str):
                            out.append(part[0])
                    translated = "".join(out) if out else None
                if translated is None:
                    raise RuntimeError("response format changed")
                return translated
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            last_exc = exc
            if attempt < retry_times:
                await asyncio.sleep(0.3 * attempt)

    raise RuntimeError(f"translate failed: {last_exc}")
