import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://support.amaranth10.com/user/am10manage/login"
REPO_DIR = r"C:\Users\wndi1\OneDrive\바탕 화면\A10 이용가이드 사이트 접속 확인"
RESULT_FILE = os.path.join(REPO_DIR, "results.json")

LOGIN_ID = "minzz@douzone.com"
LOGIN_PW = "wndi1328*"

async def check_site():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    result = {"timestamp": timestamp, "status": "", "message": "", "mode": mode}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 페이지 접속
            response = await page.goto(URL, timeout=15000)

            if not response or response.status != 200:
                result["status"] = "fail"
                result["message"] = f"페이지 접속 실패 HTTP {response.status if response else '응답없음'}"
                await browser.close()
                return result

            # 로그인 시도
            await page.fill("input[type='email'], input[name='userId'], input[name='id'], input[type='text']", LOGIN_ID)
            await page.fill("input[type='password']", LOGIN_PW)
            await page.click("button[type='submit'], input[type='submit']")

            # 로그인 결과 대기
            await page.wait_for_timeout(3000)

            current_url = page.url

            if current_url != URL and "login" not in current_url:
                result["status"] = "success"
                result["message"] = "로그인 성공"
            else:
                result["status"] = "fail"
                result["message"] = "로그인 실패 (아이디/비밀번호 오류 또는 페이지 변화 없음)"

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
    data = data[-500:]

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[{timestamp}] {result['status']} - {result['message']}")

    # GitHub에 자동 push
    try:
        subprocess.run(["git", "-C", REPO_DIR, "add", "results.json"], check=True)
        subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", f"update {timestamp}"], check=True)
        subprocess.run(["git", "-C", REPO_DIR, "push", "origin", "main"], check=True)
        print("GitHub 업로드 완료")
    except subprocess.CalledProcessError as e:
        print(f"GitHub 업로드 실패: {e}")

mode = "수동" if len(sys.argv) > 1 and sys.argv[1] == "manual" else "자동"
asyncio.run(check_site())