"""URL Collector - Google 검색 결과 Feedback 자동화 모듈

이 모듈은 Google 검색 결과 페이지에서 Feedback을 자동으로 제출하는 기능을 제공합니다.

주요 기능:
- 검색 결과의 "..." 버튼 클릭 및 상세 패널 열기
- Feedback 버튼 클릭
- "기타" -> "스팸 콘텐츠" 옵션 선택
- 템플릿 텍스트 입력 및 제출

사용 시나리오:
1. 자동화 모드: 여러 검색 결과에 대해 순차적으로 Feedback 제출
2. 단일 제출 모드: 사용자가 이미 상세 패널을 열어놓은 상태에서 Feedback만 제출
"""

import asyncio
from typing import Callable, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, Page


# Selector 상수 정의
FEEDBACK_SELECTORS = [
    'button:has-text("Feedback")',
    'button:has-text("의견")',
    '[role="button"]:has-text("Feedback")',
    '[role="button"]:has-text("의견")',
    'div[aria-label*="Feedback"] button',
    'div[aria-label*="의견"] button',
    '[aria-label*="Feedback"]',
    '[aria-label*="의견"]',
]

OTHER_SELECTORS = [
    'div[role="listitem"]:has-text("기타")',
    'div[role="option"]:has-text("기타")',
    'button:has-text("기타")',
    'button:has-text("Other")',
    'div[role="button"]:has-text("기타")',
    '[data-value*="other"]',
]

SPAM_SELECTORS = [
    'button:has-text("스팸 콘텐츠")',
    'div[role="button"]:has-text("스팸")',
    'button:has-text("Spam")',
    '[data-value*="spam"]',
    'div[role="listitem"]:has-text("스팸")',
]

TEXTAREA_SELECTORS = [
    'textarea[placeholder*="선택사항"]',
    'textarea[placeholder*="세부정보"]',
    'textarea[placeholder*="detail"]',
    'textarea[aria-label*="세부정보"]',
    'div[role="dialog"] textarea',
    'form textarea',
]

SUBMIT_SELECTORS = [
    'button:has-text("제출")',
    'button:has-text("Submit")',
    'button[type="submit"]',
    'div[role="dialog"] button[aria-label*="제출"]',
    'form button[type="submit"]',
]


@dataclass
class FeedbackConfig:
    """Feedback 자동화 설정"""
    headless: bool = False  # 브라우저 표시 여부
    delay_between_submissions: float = 3.0  # 제출 간 딜레이 (초)


class GoogleFeedbackReporter:
    """Google 검색 결과 Feedback 자동화 클래스"""

    def __init__(self, config: FeedbackConfig = None):
        self.config = config or FeedbackConfig()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._playwright = None
        self._running = False
        self._cancelled = False

    async def start(self):
        """브라우저 시작"""
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ko-KR'
        )
        self.page = await context.new_page()

    async def stop(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    def cancel(self):
        """작업 취소"""
        self._cancelled = True

    async def _click_more_button(self, result_index: int) -> bool:
        """특정 검색 결과의 "..." 버튼 클릭"""
        try:
            # 검색 결과 div 찾기 (여러 selector 시도)
            selectors = [
                f'div.g:nth-of-type({result_index + 1}) button[aria-label*="추가"]',
                f'div.g:nth-of-type({result_index + 1}) button[aria-label*="More"]',
                f'div.g:nth-of-type({result_index + 1}) div[role="button"]',
                f'#search div.g:nth-of-type({result_index + 1}) button.action-menu',
            ]

            for selector in selectors:
                try:
                    more_btn = await self.page.wait_for_selector(selector, timeout=2000)
                    if more_btn:
                        await more_btn.click()
                        await asyncio.sleep(0.5)
                        return True
                except:
                    continue

            return False

        except Exception as e:
            print(f"More 버튼 클릭 실패: {e}")
            return False

    async def _click_feedback_button(self) -> bool:
        """상세 패널에서 Feedback 버튼 클릭 (패널이 이미 열려있다고 가정)"""
        try:
            for selector in FEEDBACK_SELECTORS:
                try:
                    feedback_btn = await self.page.wait_for_selector(selector, timeout=2000)
                    if feedback_btn:
                        # 버튼이 보이는지 확인
                        is_visible = await feedback_btn.is_visible()
                        if is_visible:
                            await feedback_btn.click()
                            await asyncio.sleep(0.8)
                            return True
                except:
                    continue

            return False

        except Exception as e:
            print(f"Feedback 버튼 클릭 실패: {e}")
            return False

    async def _submit_feedback(self, template_text: str) -> bool:
        """Feedback 모달에서 내용 입력 및 제출"""
        try:
            # 모달이 열릴 때까지 대기
            await asyncio.sleep(0.5)

            # 1. "기타" 버튼 클릭
            clicked = False
            for selector in OTHER_SELECTORS:
                try:
                    other_btn = await self.page.wait_for_selector(selector, timeout=3000)
                    if other_btn and await other_btn.is_visible():
                        await other_btn.click()
                        await asyncio.sleep(0.5)
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                print("'기타' 버튼을 찾지 못했습니다")
                return False

            # 2. "스팸 콘텐츠" 버튼 클릭
            clicked = False
            for selector in SPAM_SELECTORS:
                try:
                    spam_btn = await self.page.wait_for_selector(selector, timeout=3000)
                    if spam_btn and await spam_btn.is_visible():
                        await spam_btn.click()
                        await asyncio.sleep(0.5)
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                print("'스팸 콘텐츠' 버튼을 찾지 못했습니다")
                return False

            # 3. 텍스트 영역에 템플릿 입력
            typed = False
            for selector in TEXTAREA_SELECTORS:
                try:
                    textarea = await self.page.wait_for_selector(selector, timeout=3000)
                    if textarea and await textarea.is_visible():
                        await textarea.click()
                        await asyncio.sleep(0.2)
                        await textarea.fill(template_text)
                        await asyncio.sleep(0.5)
                        typed = True
                        break
                except:
                    continue

            if not typed:
                print("텍스트 영역을 찾지 못했습니다")
                return False

            # 4. "제출" 버튼 클릭
            submitted = False
            for selector in SUBMIT_SELECTORS:
                try:
                    submit_btn = await self.page.wait_for_selector(selector, timeout=3000)
                    if submit_btn and await submit_btn.is_visible():
                        await submit_btn.click()
                        await asyncio.sleep(1.5)
                        submitted = True
                        break
                except:
                    continue

            if not submitted:
                print("'제출' 버튼을 찾지 못했습니다")
                return False

            return True

        except Exception as e:
            print(f"Feedback 제출 실패: {e}")
            return False

    async def run_automation(
        self,
        search_url: str,
        result_indices: list[int],
        template: str,
        on_progress: Callable[[int, int, str], None] = None,
        on_complete: Callable[[bool, str], None] = None
    ):
        """
        Google 검색 결과 페이지에서 여러 결과에 Feedback 제출

        Args:
            search_url: Google 검색 결과 URL
            result_indices: Feedback을 제출할 검색 결과 인덱스 (0부터 시작)
            template: Feedback 템플릿 텍스트
            on_progress: 진행 콜백 (current, total, message)
            on_complete: 완료 콜백 (success, message)
        """
        self._running = True
        self._cancelled = False

        success_count = 0
        fail_count = 0
        total = len(result_indices)

        try:
            if not self.browser or not self.page:
                await self.start()

            if on_progress:
                on_progress(0, total, "검색 결과 페이지로 이동 중...")

            # 검색 결과 페이지 이동
            await self.page.goto(search_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)

            if self._cancelled:
                if on_complete:
                    on_complete(False, "사용자에 의해 취소됨")
                return

            # 각 검색 결과에 대해 Feedback 제출
            for i, result_idx in enumerate(result_indices):
                if self._cancelled:
                    if on_complete:
                        on_complete(False, f"사용자에 의해 취소됨 ({success_count}/{total} 완료)")
                    return

                current = i + 1
                if on_progress:
                    on_progress(current, total, f"결과 #{result_idx + 1} 처리 중...")

                try:
                    # 1. More 버튼 클릭
                    if not await self._click_more_button(result_idx):
                        fail_count += 1
                        print(f"결과 #{result_idx + 1}: More 버튼 클릭 실패")
                        continue

                    # 2. Feedback 버튼 클릭
                    if not await self._click_feedback_button():
                        fail_count += 1
                        print(f"결과 #{result_idx + 1}: Feedback 버튼 클릭 실패")
                        # 패널 닫기
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.5)
                        continue

                    # 3. Feedback 제출
                    if not await self._submit_feedback(template):
                        fail_count += 1
                        print(f"결과 #{result_idx + 1}: Feedback 제출 실패")
                        # 모달 닫기
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.5)
                        continue

                    success_count += 1
                    print(f"결과 #{result_idx + 1}: Feedback 제출 완료 ✓")

                    # 다음 작업 전 딜레이
                    if current < total:
                        await asyncio.sleep(self.config.delay_between_submissions)

                except Exception as e:
                    fail_count += 1
                    print(f"결과 #{result_idx + 1} 처리 중 오류: {e}")
                    # 에러 발생시 모든 모달/패널 닫기
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
                    continue

            # 완료 메시지
            if on_complete:
                if success_count == total:
                    on_complete(True, f"모든 Feedback 제출 완료 ({success_count}/{total})")
                elif success_count > 0:
                    on_complete(True, f"일부 Feedback 제출 완료 ({success_count}/{total})")
                else:
                    on_complete(False, f"모든 Feedback 제출 실패 (0/{total})")

        except Exception as e:
            if on_complete:
                on_complete(False, f"오류 발생: {str(e)}")
        finally:
            self._running = False

    async def submit_single_feedback(
        self,
        template_text: str,
        on_progress: Callable[[str], None] = None,
        on_complete: Callable[[bool, str], None] = None
    ):
        """
        현재 열려있는 상세 패널에서 단일 Feedback 제출

        사용자가 이미 Google 검색 결과에서 "..." 버튼을 클릭하여
        상세 패널을 열어놓은 상태에서 시작합니다.

        Args:
            template_text: Feedback 템플릿 텍스트
            on_progress: 진행 콜백 (message)
            on_complete: 완료 콜백 (success, message)
        """
        self._running = True
        self._cancelled = False

        try:
            if not self.browser or not self.page:
                await self.start()

            if on_progress:
                on_progress("Feedback 버튼 클릭 중...")

            # 1. Feedback 버튼 클릭
            if not await self._click_feedback_button():
                if on_complete:
                    on_complete(False, "Feedback 버튼을 찾을 수 없습니다")
                return

            if self._cancelled:
                if on_complete:
                    on_complete(False, "사용자에 의해 취소됨")
                return

            if on_progress:
                on_progress("Feedback 양식 작성 중...")

            # 2. Feedback 제출
            if not await self._submit_feedback(template_text):
                if on_complete:
                    on_complete(False, "Feedback 제출 실패")
                return

            if on_complete:
                on_complete(True, "Feedback 제출 완료")

        except Exception as e:
            if on_complete:
                on_complete(False, f"오류 발생: {str(e)}")
        finally:
            self._running = False
