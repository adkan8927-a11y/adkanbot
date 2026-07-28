import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        print("🚀 Playwright 브라우저 기동 중...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 네트워크 요청 모니터링
        def handle_request(request):
            if "todaydisclosure.do" in request.url:
                print(f"\n[Request Detected] URL: {request.url}")
                print(f"  Method: {request.method}")
                print(f"  Headers: {request.headers}")
                post_data = request.post_data
                if post_data:
                    print(f"  Post Data: {post_data}")
        
        page.on("request", handle_request)
        
        print("📥 KIND 오늘의공시 페이지 접속...")
        await page.goto("https://kind.krx.co.kr/disclosure/todaydisclosure.do?method=searchTodayDisclosureMain&marketType=0")
        await page.wait_for_timeout(5000)
        
        # 06.26 (금) 날짜 탭 클릭 유도
        # 스크린샷 기준으로 '06.26 (금)' 텍스트가 담긴 요소를 찾아 클릭
        print("🖱️ 06.26 날짜 탭 찾아서 클릭...")
        tabs = await page.query_selector_all("a")
        for tab in tabs:
            text = await tab.inner_text()
            if "06.26" in text:
                print(f"  → 날짜 탭 클릭 대상 발견: '{text.strip()}'")
                await tab.click()
                break
                
        await page.wait_for_timeout(5000)
        await browser.close()
        print("\n✅ 분석 완료.")

if __name__ == "__main__":
    asyncio.run(main())
