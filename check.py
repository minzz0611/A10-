import asyncio
import json
import os
import subprocess
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

URL = "https://support.amaranth10.com/user/am10manage/login"
REPO_DIR = r"C:\Users\wndi1\OneDrive\바탕 화면\A10 이용가이드 사이트 접속 확인"
RESULT_FILE = os.path.join(REPO_DIR, "results.json")

LOGIN_ID = os.getenv("LOGIN_ID")
LOGIN_PW = os.getenv("LOGIN_PW")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PW = os.getenv("MAIL_PW")
MAIL_TO = os.getenv("MAIL_TO")

mode = "수동" if len(sys.argv) > 1 and sys.argv[1] == "manual" else "자동"

def send_mail(timestamp, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_FROM
        msg['Subject'] = f"[긴급] A10 이용가이드 접속 실패 - {timestamp}"
        body = f"""
A10 이용가이드 사이트 접속 실패가 감지됐습니다.

━━━━━━━━━━━━━━━━━━━━
발생 시각 : {timestamp}
실패 원인 : {message}
사이트 URL : {URL}
━━━━━━━━━━━━━━━━━━━━

보고 사이트에서 상세 내용을 확인하세요.
https://minzz0611.github.io/A10-/report.html
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        recipients = [r.strip() for r in MAIL_TO.split(',')]
        msg['To'] = ', '.join(recipients)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MAIL_FROM, MAIL_PW)
            server.sendmail(MAIL_FROM, recipients, msg.as_string())
        print("메일 발송 완료")
    except Exception as e:
        print(f"메일 발송 실패: {e}")

async def check_site():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    result = {"timestamp": timestamp, "status": "", "message": "", "mode": mode}

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage'])
            page = await browser.new_page()

            response = await page.goto(URL, timeout=15000)

            if not response or response.status != 200:
                result["status"] = "fail"
                result["message"] = f"페이지 접속 실패 HTTP {response.status if response else '응답없음'}"
                send_mail(timestamp, result["message"])
                return

            await page.fill("input[type='email'], input[name='userId'], input[name='id'], input[type='text']", LOGIN_ID)
            await page.fill("input[type='password']", LOGIN_PW)
            await page.click("button.btn_login")
            await page.wait_for_timeout(3000)

            current_url = page.url
            if current_url != URL and "login" not in current_url:
                api_response = await page.request.get("https://support.amaranth10.com/api/user/home")
                if api_response.status == 500:
                    result["status"] = "fail"
                    result["message"] = "로그인 성공 but 서버 오류 (재기동 필요) - HTTP 500"
                    send_mail(timestamp, result["message"])
                else:
                    result["status"] = "success"
                    result["message"] = "로그인 성공"
            else:
                result["status"] = "fail"
                result["message"] = "로그인 실패 (아이디/비밀번호 오류 또는 페이지 변화 없음)"
                send_mail(timestamp, result["message"])

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
        send_mail(timestamp, result["message"])

    finally:
        if browser:
            await browser.close()

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

    try:
        CREATE_NO_WINDOW = 0x08000000
        subprocess.run(["git", "-C", REPO_DIR, "add", "results.json", "report.html"], check=True, creationflags=CREATE_NO_WINDOW)

        # 변경사항이 없으면 commit이 실패(returncode 1)하므로 별도 체크로 무시
        commit = subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", f"update {timestamp}"],
                                 creationflags=CREATE_NO_WINDOW, capture_output=True, text=True)
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            raise subprocess.CalledProcessError(commit.returncode, commit.args, commit.stdout, commit.stderr)

        # push 전에 원격 변경사항을 먼저 반영 (fast-forward 불가로 인한 rejected 방지)
        # rebase는 repo 내 무관한 파일에 unstaged 변경만 있어도 실패하므로, merge 방식(plain pull) 사용
        subprocess.run(["git", "-C", REPO_DIR, "pull", "origin", "main", "--no-edit"], check=True, creationflags=CREATE_NO_WINDOW)

        subprocess.run(["git", "-C", REPO_DIR, "push", "origin", "main"], check=True, creationflags=CREATE_NO_WINDOW)
        print("GitHub 업로드 완료")
    except subprocess.CalledProcessError as e:
        error_detail = getattr(e, "stderr", None) or str(e)
        print(f"GitHub 업로드 실패: {error_detail}")
        # 업로드 실패는 데이터 유실로 이어지므로 접속 성공/실패 여부와 무관하게 메일 발송
        send_mail(timestamp, f"GitHub 업로드 실패 (로컬에는 데이터가 정상 기록됐으나 원격 반영 실패)\n\n{error_detail}")

asyncio.run(check_site())