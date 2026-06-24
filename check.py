import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://support.amaranth10.com/user/am10manage/login"
RESULT_FILE = r"C:\monitor\results.json"

async def check_site():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    result = {"timestamp": timestamp, "status": "", "message": ""}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(URL, timeout=15000)

            if response and response.status == 200:
                result["status"] = "success"
                result["message"] = "접속 성공"
            else:
                result["status"] = "fail"
                result["message"] = f"HTTP {response.status if response else '응답없음'}"

            await browser.close()

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    # 기존 결과 불러오기
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.append(result)

    # 최근 500개만 유지
    data = data[-500:]

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[{timestamp}] {result['status']} - {result['message']}")

asyncio.run(check_site())