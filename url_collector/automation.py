"""URL Collector - Playwright 자동화 모듈 (JS 코드 직접 실행)"""

import asyncio
from typing import Callable, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, Page


@dataclass
class AutomationConfig:
    """자동화 설정"""
    headless: bool = False  # 브라우저 표시 여부
    delay_between_submissions: float = 3.0  # 제출 간 딜레이 (초)


class GoogleLegalReporter:
    """Google 법적 신고 자동화 클래스 - JS 코드 직접 실행"""

    REPORT_URL = "https://support.google.com/legal/contact/lr_legalother?product=websearch&uraw&ctx=magi&sjid=14649864030784806781-NC&hl=ko"

    def __init__(self, config: AutomationConfig = None):
        self.config = config or AutomationConfig()
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

    def _generate_js_code(self, urls: list[str], applicant: dict, template: dict, auto_submit: bool = True) -> str:
        """신고 코드 페이지와 동일한 JS 코드 생성"""

        # URL 배열 생성
        urls_js = ",\n".join([f'  "{url}"' for url in urls])

        # 템플릿 값 이스케이프
        reason = template.get("reason", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        evidence = template.get("evidence", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        check_explicit = "true" if template.get("check_explicit", False) else "false"
        check_subject = "true" if template.get("check_subject", False) else "false"
        check_telecom = "true" if template.get("check_telecom", False) else "false"
        report_reason = template.get("report_reason", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        victim_name = template.get("victim_name", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        search_keyword = template.get("search_keyword", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

        js_code = f'''
(async function() {{
  const delay = ms => new Promise(r => setTimeout(r, ms));

  // ========== 거주 국가 선택 (한국) ==========
  const countrySelectors = [
    'select[name="country"]',
    'select[name="reporter_country"]',
    'select[id*="country"]',
    'select[aria-label*="국가"]',
    '.country-select select',
    'select'
  ];

  let countrySelect = null;
  for (const selector of countrySelectors) {{
    const el = document.querySelector(selector);
    if (el && el.tagName === 'SELECT') {{
      const options = Array.from(el.options);
      const koreaOption = options.find(opt =>
        opt.value === 'KR' ||
        opt.value === 'kr' ||
        opt.value === 'Korea' ||
        opt.value === 'south_korea' ||
        opt.text.includes('한국') ||
        opt.text.includes('Korea')
      );
      if (koreaOption) {{
        countrySelect = el;
        countrySelect.value = koreaOption.value;
        countrySelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
        countrySelect.dispatchEvent(new Event('input', {{ bubbles: true }}));
        console.log('✓ 거주 국가: 한국 선택');
        break;
      }}
    }}
  }}
  await delay(300);

  // ========== 신청인 정보 ==========
  const applicant = {{
    fullName: "{applicant.get('full_name', '')}",
    company: "{applicant.get('company', '')}",
    organization: "{applicant.get('organization', '')}",
    email: "{applicant.get('email', '')}"
  }};

  const nameInput = document.querySelector('input[name="full_name"]');
  if (nameInput && applicant.fullName) {{
    nameInput.value = applicant.fullName;
    nameInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  const companyInput = document.querySelector('input[name="companyname"]');
  if (companyInput && applicant.company) {{
    companyInput.value = applicant.company;
    companyInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  const orgInput = document.querySelector('input[name="represented_copyright_holder"]');
  if (orgInput && applicant.organization) {{
    orgInput.value = applicant.organization;
    orgInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  // 이메일 - 여러 가능한 필드명 시도
  const emailSelectors = ['input[name="contact_email_noprefill"]', 'input[name="contact_email"]', 'input#contact_email_noprefill', 'input[type="email"]'];
  for (const sel of emailSelectors) {{
    const emailInput = document.querySelector(sel);
    if (emailInput && applicant.email) {{
      emailInput.value = applicant.email;
      emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
      console.log('✓ 이메일 입력 완료');
      break;
    }}
  }}

  console.log('✓ 신청인 정보 입력 완료');
  await delay(300);

  // ========== 권리 침해 유형 체크박스 ==========
  const checkOptions = {{
    explicit: {check_explicit},
    subject: {check_subject},
    telecom: {check_telecom}
  }};

  const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
  for (const cb of allCheckboxes) {{
    const fieldText = cb.closest('.field')?.textContent || '';

    if (checkOptions.explicit && (fieldText.includes('선정적 이미지') || fieldText.includes('아동 성적 학대'))) {{
      if (!cb.checked) cb.click();
      console.log('✓ 선정적 이미지/아동 학대 체크');
    }}

    if (checkOptions.subject && (fieldText.includes('피사체') || fieldText.includes('법적 대리인'))) {{
      if (!cb.checked) cb.click();
      console.log('✓ 피사체/법적 대리인 체크');
    }}

    if (checkOptions.telecom && (fieldText.includes('전기통신사업법') || fieldText.includes('Telecommunications Business Act'))) {{
      if (!cb.checked) cb.click();
      console.log('✓ 전기통신사업법 체크');
    }}
  }}
  await delay(500);

  // ========== 콘텐츠 신고 사유 드롭다운 ==========
  const reportReason = `{report_reason}`;
  if (reportReason) {{
    const allSelects = document.querySelectorAll('select');
    for (const sel of allSelects) {{
      const fieldText = sel.closest('.field')?.textContent || '';
      if (fieldText.includes('콘텐츠 신고 사유') || fieldText.includes('신고 사유')) {{
        const options = Array.from(sel.options);
        const targetOption = options.find(opt =>
          opt.text.includes(reportReason) || opt.value.includes(reportReason)
        );
        if (targetOption) {{
          sel.value = targetOption.value;
          sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
          sel.dispatchEvent(new Event('input', {{ bubbles: true }}));
          console.log('✓ 콘텐츠 신고 사유: ' + reportReason);
        }}
        break;
      }}
    }}
  }}
  await delay(300);

  // ========== 피해자 이름 입력 ==========
  const victimName = `{victim_name}`;
  if (victimName) {{
    const allInputs = document.querySelectorAll('input[type="text"]');
    for (const input of allInputs) {{
      const fieldText = input.closest('.field')?.textContent || '';
      if (fieldText.includes('성과 이름') || fieldText.includes('표시되는 사람') || fieldText.includes('피사체')) {{
        input.value = victimName;
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        console.log('✓ 피해자 이름 입력');
        break;
      }}
    }}
  }}
  await delay(200);

  // ========== 검색어 입력 (전기통신사업법) ==========
  if (checkOptions.telecom && `{search_keyword}`) {{
    const keywordInputs = document.querySelectorAll('input[type="text"]');
    for (const input of keywordInputs) {{
      const fieldText = input.closest('.field')?.textContent || '';
      if (fieldText.includes('검색어') || fieldText.includes('search')) {{
        input.value = `{search_keyword}`;
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        console.log('✓ 검색어 입력 완료');
        break;
      }}
    }}
  }}
  await delay(200);

  // ========== 템플릿 내용 ==========
  const allTextareas = document.querySelectorAll('textarea');
  for (const textarea of allTextareas) {{
    const label = textarea.closest('.field')?.querySelector('label')?.textContent || '';
    if (label.includes('불법이라고 생각되는 이유') || textarea.name === 'explanation' || textarea.name === 'dmca_explanation') {{
      textarea.value = `{reason}`;
      textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
      console.log('✓ 불법 이유 입력 완료');
    }}
    if (label.includes('권리를 침해한 것으로 보이는') || label.includes('정확한 텍스트를 인용') || textarea.name === 'infringe_explanation' || textarea.name === 'dmca_infringe_explanation') {{
      textarea.value = `{evidence}`;
      textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
      console.log('✓ 침해 증거 입력 완료');
    }}
  }}
  await delay(300);

  // ========== URL 입력 ==========
  const urls = [
{urls_js}
  ];

  const addButtons = document.querySelectorAll('a.add-additional');
  let targetButton = null;

  for (const btn of addButtons) {{
    const parent = btn.closest('.field');
    if (parent && parent.querySelector('#url_box3')) {{
      targetButton = btn;
      break;
    }}
  }}

  const firstInput = document.querySelector('#url_box3');
  if (firstInput && urls[0]) {{
    firstInput.value = urls[0];
    firstInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    console.log('1/' + urls.length + ': ' + urls[0].substring(0, 50) + '...');
  }}

  for (let i = 1; i < urls.length; i++) {{
    if (targetButton) {{
      targetButton.click();
      await delay(200);

      const allInputs = document.querySelectorAll('input[name="url_box3"]');
      const newInput = allInputs[allInputs.length - 1];

      if (newInput) {{
        newInput.value = urls[i];
        newInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        console.log((i+1) + '/' + urls.length + ': ' + urls[i].substring(0, 50) + '...');
      }}
    }}
    await delay(100);
  }}

  console.log('✓ ' + urls.length + '개 URL 입력 완료');

  // ========== 확인/동의 체크박스 ==========
  const confirmCheckboxes = document.querySelectorAll('input[type="checkbox"]');
  for (const checkbox of confirmCheckboxes) {{
    const fieldText = checkbox.closest('.field')?.textContent || '';
    const isRightsCheckbox =
      fieldText.includes('선정적 이미지') ||
      fieldText.includes('아동 성적 학대') ||
      fieldText.includes('피사체') ||
      fieldText.includes('법적 대리인') ||
      fieldText.includes('전기통신사업법') ||
      fieldText.includes('Telecommunications');

    if (!isRightsCheckbox && !checkbox.checked) {{
      checkbox.click();
    }}
  }}
  console.log('✓ 확인 체크박스 선택 완료');

  // ========== 서명 ==========
  const signatureInput = document.querySelector('input[name="signature"]');
  if (signatureInput && applicant.fullName) {{
    signatureInput.value = applicant.fullName;
    signatureInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    console.log('✓ 서명 입력 완료');
  }}

  console.log('\\n🎉 모든 필드 자동 입력 완료!');
'''

        if auto_submit:
            js_code += '''
  // ========== 자동 제출 ==========
  await delay(1000);
  const submitButton = document.querySelector('input[type="submit"], button[type="submit"], .submit-button, button[name="submit"]');
  if (submitButton) {
    console.log('🚀 제출 버튼 클릭 중...');
    submitButton.click();
    console.log('✓ 제출 완료!');
  } else {
    console.log('⚠ 제출 버튼을 찾지 못했습니다.');
  }
'''

        js_code += '''
  return '완료';
})();
'''
        return js_code

    async def run_automation(
        self,
        urls: list[str],
        applicant: dict,
        template: dict,
        on_progress: Callable[[int, int, str], None] = None,
        on_complete: Callable[[bool, str], None] = None
    ):
        """
        전체 자동화 실행 - JS 코드 직접 실행

        Args:
            urls: 신고할 URL 목록
            applicant: 신청인 정보
            template: 템플릿 정보
            on_progress: 진행 콜백
            on_complete: 완료 콜백
        """
        self._running = True
        self._cancelled = False

        try:
            if not self.browser or not self.page:
                await self.start()

            if on_progress:
                on_progress(0, 1, "신고 페이지로 이동 중...")

            # 페이지 이동
            await self.page.goto(self.REPORT_URL, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(1)

            if self._cancelled:
                if on_complete:
                    on_complete(False, "사용자에 의해 취소됨")
                return

            if on_progress:
                on_progress(0, 1, f"폼 작성 중... ({len(urls)}개 URL)")

            # JS 코드 생성 및 실행
            js_code = self._generate_js_code(urls, applicant, template, auto_submit=True)

            # 콘솔 로그 캡처
            self.page.on("console", lambda msg: print(f"[Browser] {msg.text}"))

            # JS 실행
            result = await self.page.evaluate(js_code)

            if on_progress:
                on_progress(1, 1, "완료!")

            # 제출 후 페이지 로드 대기
            await asyncio.sleep(3)

            if on_complete:
                on_complete(True, f"총 {len(urls)}개 URL 신고 완료")

        except Exception as e:
            if on_complete:
                on_complete(False, f"오류 발생: {str(e)}")
        finally:
            self._running = False
