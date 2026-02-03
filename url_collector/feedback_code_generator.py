"""
Google Search Feedback Automation Code Generator

사용법:
1. Google 검색 결과에서 신고할 사이트의 "..." 버튼 클릭
2. 오른쪽에 상세 패널이 열리면 F12 → Console 탭
3. 'allow pasting' 입력 후 Enter
4. 생성된 코드 붙여넣기 후 Enter
"""

def generate_feedback_code(template: dict, feedback_type: str = "스팸 콘텐츠", custom_opinion: str = None) -> str:
    """
    Google 피드백 자동화 JS 코드 생성

    Args:
        template: 템플릿 딕셔너리 (opinion 키 포함)
        feedback_type: 피드백 타입 ("스팸 콘텐츠", "부정확한 콘텐츠", "관련성 없는 콘텐츠" 등)
        custom_opinion: 직접 입력한 의견 (있으면 template의 opinion 대신 사용)
    """
    opinion_text = custom_opinion if custom_opinion else template.get('opinion', '')
    opinion = opinion_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
    feedback_type_escaped = feedback_type.replace('\\', '\\\\').replace('`', '\\`').replace("'", "\\'")

    js_code = f"""
(async function() {{
  const delay = ms => new Promise(r => setTimeout(r, ms));

  // 컨테이너 태그 제외
  const isContainer = (el) => {{
    const tag = el.tagName.toUpperCase();
    return ['BODY', 'HTML', 'HEAD', 'SCRIPT', 'STYLE', 'NOSCRIPT'].includes(tag);
  }};

  // 요소가 클릭 가능한 크기인지 확인 (너무 큰 요소 제외)
  const isClickableSize = (el) => {{
    const rect = el.getBoundingClientRect();
    // 버튼은 보통 500px 이하
    return rect.width < 500 && rect.height < 200 && rect.width > 10 && rect.height > 10;
  }};

  const isVisible = (el) => {{
    if (!el || isContainer(el)) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 &&
           style.display !== 'none' && style.visibility !== 'hidden' &&
           style.opacity !== '0';
  }};

  // 강제 클릭 (여러 방법 시도)
  const forceClick = (el) => {{
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    console.log('클릭:', el.tagName, rect.width.toFixed(0)+'x'+rect.height.toFixed(0), el.textContent.trim().substring(0, 15));

    // 중앙 좌표
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    // 포커스
    el.focus();

    // 마우스 이벤트 시퀀스
    ['mouseover', 'mouseenter', 'mousedown', 'mouseup', 'click'].forEach(type => {{
      el.dispatchEvent(new MouseEvent(type, {{
        view: window, bubbles: true, cancelable: true,
        clientX: x, clientY: y, button: 0, buttons: 1
      }}));
    }});

    // 포인터 이벤트
    ['pointerover', 'pointerenter', 'pointerdown', 'pointerup'].forEach(type => {{
      el.dispatchEvent(new PointerEvent(type, {{
        view: window, bubbles: true, cancelable: true,
        clientX: x, clientY: y, button: 0, isPrimary: true, pointerType: 'mouse'
      }}));
    }});

    return true;
  }};

  // category-label에서 텍스트로 버튼 찾기 (메인 카테고리용)
  const findCategoryLabel = (text) => {{
    // category-label 내의 span.RES9jf에서 정확한 텍스트 찾기
    const labels = document.querySelectorAll('category-label span.RES9jf, category-label span.wHYlTd');
    for (const span of labels) {{
      if (span.textContent.trim() === text) {{
        // 부모 div[jsaction][role="button"] 찾기
        let parent = span.parentElement;
        for (let i = 0; i < 5; i++) {{
          if (!parent) break;
          if (parent.hasAttribute('jsaction') && parent.getAttribute('role') === 'button') {{
            if (isVisible(parent)) return parent;
          }}
          parent = parent.parentElement;
        }}
      }}
    }}
    return null;
  }};

  // category-chip에서 텍스트로 버튼 찾기 (서브 카테고리용)
  // 반드시 보이는 category-chips-container 안에서만 검색
  const findCategoryChip = (text) => {{
    // 보이는 category-chips-container 찾기
    const containers = document.querySelectorAll('category-chips-container');
    for (const container of containers) {{
      // display:none이 아닌 컨테이너만
      const style = container.getAttribute('style') || '';
      if (style.includes('display: none') || style.includes('display:none')) continue;
      if (!isVisible(container)) continue;

      // 이 컨테이너 안의 chip만 검색
      const chips = container.querySelectorAll('category-chip span.pAn7ne');
      for (const span of chips) {{
        if (span.textContent.trim() === text) {{
          // 부모 div[role="radio"] 찾기
          let parent = span.parentElement;
          for (let i = 0; i < 5; i++) {{
            if (!parent) break;
            if (parent.getAttribute('role') === 'radio' || parent.hasAttribute('jsaction')) {{
              if (isVisible(parent)) {{
                console.log('chip 찾음 in visible container:', text);
                return parent;
              }}
            }}
            parent = parent.parentElement;
          }}
        }}
      }}
    }}
    return null;
  }};

  // jsaction을 가진 가장 가까운 부모 찾기
  const findClickableParent = (el) => {{
    let current = el;
    for (let i = 0; i < 5; i++) {{
      if (!current || isContainer(current)) return null;
      if (current.hasAttribute('jsaction') && current.getAttribute('role') === 'button') {{
        return current;
      }}
      if (current.hasAttribute('jsaction') && current.style.cursor === 'pointer') {{
        return current;
      }}
      current = current.parentElement;
    }}
    return null;
  }};

  // 텍스트로 클릭 가능한 버튼 찾기 (일반용)
  const findButtonByText = (text) => {{
    // 1. span/div 중 텍스트가 정확히 일치하는 요소 찾기
    const textElements = document.querySelectorAll('span, div');
    for (const el of textElements) {{
      if (isContainer(el)) continue;

      const directText = Array.from(el.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent.trim())
        .join('');

      if (directText === text && isVisible(el)) {{
        const clickable = findClickableParent(el);
        if (clickable && isClickableSize(clickable)) {{
          return clickable;
        }}
        if (isClickableSize(el)) {{
          return el;
        }}
      }}
    }}

    // 2. role="button/radio" 또는 jsaction이 있는 요소
    const buttons = document.querySelectorAll('[role="button"], [role="radio"], [jsaction], button');
    for (const btn of buttons) {{
      if (isContainer(btn)) continue;
      if (btn.textContent.trim() === text && isVisible(btn) && isClickableSize(btn)) {{
        return btn;
      }}
    }}

    return null;
  }};

  // 클릭 가능 요소 찾기 (우선순위: category-label > category-chip > 일반)
  const findClickable = (text) => {{
    let el = findCategoryLabel(text);
    if (el) return el;

    el = findCategoryChip(text);
    if (el) return el;

    return findButtonByText(text);
  }};

  try {{
    console.log('=== Google 피드백 자동화 시작 ===');
    console.log('[1/5] Feedback 버튼 찾는 중...');

    let feedbackBtn = findClickable('Feedback') || findClickable('의견');
    if (!feedbackBtn) {{
      console.error('❌ Feedback 버튼을 찾을 수 없습니다.');
      return;
    }}

    forceClick(feedbackBtn);
    console.log('✓ Feedback 버튼 클릭 완료');
    await delay(2000);

    // 서브 카테고리 설정 (기타 하위 옵션)
    const subCategory = '{feedback_type_escaped}';

    // Step 2: "기타" 클릭 (category-label에서 찾기)
    console.log('[2/5] 기타 옵션 찾는 중...');

    let otherBtn = null;
    for (let retry = 0; retry < 30; retry++) {{
      // category-label 전용 검색
      otherBtn = findCategoryLabel('기타');
      if (otherBtn) {{
        console.log('category-label에서 기타 찾음');
        break;
      }}
      // 일반 검색 (fallback)
      otherBtn = findClickable('기타');
      if (otherBtn) {{
        console.log('일반 검색에서 기타 찾음');
        break;
      }}
      await delay(300);
    }}

    if (!otherBtn) {{
      console.error('❌ "기타" 옵션을 찾을 수 없습니다');
      const labels = document.querySelectorAll('category-label');
      console.log('category-label 수:', labels.length);
      labels.forEach((l, i) => console.log(i, l.textContent.trim().substring(0, 20)));
      return;
    }}

    // 여러 번 클릭 시도
    for (let clickTry = 0; clickTry < 3; clickTry++) {{
      forceClick(otherBtn);
      await delay(800);

      // category-chips-container가 보이는지 확인
      const chipsContainer = document.querySelector('category-chips-container:not([style*="display: none"])');
      if (chipsContainer) {{
        console.log('✓ 기타 클릭 성공 - chips 컨테이너 열림');
        break;
      }}
      console.log('클릭 재시도...', clickTry + 1);
    }}

    await delay(1500);

    // chips 컨테이너가 나타날 때까지 대기
    console.log('[3/5] chips 컨테이너 대기 중...');
    let chipsVisible = false;
    for (let wait = 0; wait < 30; wait++) {{
      const containers = document.querySelectorAll('category-chips-container');
      for (const c of containers) {{
        const style = c.getAttribute('style') || '';
        if (!style.includes('display: none') && !style.includes('display:none') && isVisible(c)) {{
          chipsVisible = true;
          console.log('✓ chips 컨테이너 발견');
          break;
        }}
      }}
      if (chipsVisible) break;
      await delay(200);
    }}

    if (!chipsVisible) {{
      console.error('❌ chips 컨테이너가 나타나지 않음');
      return;
    }}

    await delay(500);

    // Step 3b: 서브 카테고리 클릭 (보이는 category-chips-container 안에서만)
    console.log('[3/5] ' + subCategory + ' 찾는 중 (chips 안에서)...');

    let subBtn = null;
    for (let retry = 0; retry < 20; retry++) {{
      // category-chip 전용 검색 (보이는 컨테이너 안에서만)
      subBtn = findCategoryChip(subCategory);
      if (subBtn) {{
        console.log('✓ category-chip에서 찾음:', subCategory);
        break;
      }}
      await delay(300);
    }}

    if (!subBtn) {{
      console.error('❌ "' + subCategory + '" 버튼을 찾을 수 없습니다');
      // 보이는 컨테이너의 chips 출력
      const containers = document.querySelectorAll('category-chips-container');
      containers.forEach((c, ci) => {{
        const style = c.getAttribute('style') || '';
        if (!style.includes('display: none')) {{
          console.log('Container', ci, '의 chips:');
          c.querySelectorAll('category-chip span.pAn7ne').forEach((s, si) => {{
            console.log('  ', si, s.textContent.trim());
          }});
        }}
      }});
      return;
    }}

    // 클릭
    forceClick(subBtn);
    console.log('✓ ' + subCategory + ' 클릭 완료');

    // textarea가 나타날 때까지 대기
    for (let wait = 0; wait < 20; wait++) {{
      const textareaContainer = document.querySelector('div[jsname="Lxdjob"]');
      if (textareaContainer) {{
        const style = textareaContainer.getAttribute('style') || '';
        if (!style.includes('display: none') && !style.includes('display:none')) {{
          console.log('✓ textarea 영역 열림');
          break;
        }}
      }}
      await delay(300);
    }}

    await delay(800);

    // Step 4: 의견 입력
    console.log('[4/5] 의견 입력 중...');

    let textarea = null;
    for (let retry = 0; retry < 20; retry++) {{
      // Google 피드백 textarea 셀렉터들
      textarea = document.querySelector('textarea[jsname="B7I4Od"]') ||
                 document.querySelector('textarea[aria-label*="설명"]') ||
                 document.querySelector('textarea[placeholder="선택사항"]') ||
                 document.querySelector('textarea.S9imif') ||
                 document.querySelector('textarea:not([hidden])');
      if (textarea && isVisible(textarea)) break;
      textarea = null;
      await delay(300);
    }}

    if (!textarea) {{
      console.error('❌ 입력 영역을 찾을 수 없습니다');
      // 디버깅
      const textareas = document.querySelectorAll('textarea');
      console.log('찾은 textarea 수:', textareas.length);
      textareas.forEach((t, i) => console.log(i, t.className, t.placeholder));
      return;
    }}

    console.log('textarea 찾음:', textarea.className, textarea.placeholder);

    // 포커스 및 클릭
    textarea.focus();
    textarea.click();
    await delay(200);

    // 값 설정 (여러 방법 시도)
    const opinionText = `{opinion}`;

    // 방법 1: 직접 value 설정
    textarea.value = opinionText;

    // 방법 2: Native setter 사용 (React/Angular 호환)
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    nativeInputValueSetter.call(textarea, opinionText);

    // 이벤트 발생 시퀀스
    textarea.dispatchEvent(new Event('focus', {{ bubbles: true }}));
    textarea.dispatchEvent(new InputEvent('input', {{
      bubbles: true,
      cancelable: true,
      inputType: 'insertText',
      data: opinionText
    }}));
    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
    textarea.dispatchEvent(new Event('blur', {{ bubbles: true }}));

    // 키보드 이벤트 (jsaction 트리거용)
    textarea.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, key: 'a' }}));
    textarea.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, key: 'a' }}));

    console.log('✓ 의견 입력 완료:', opinionText.substring(0, 30) + '...');
    await delay(1000);

    // Step 5: 제출
    console.log('[5/5] 제출 버튼 찾는 중...');

    let submitBtn = null;
    for (let retry = 0; retry < 20; retry++) {{
      submitBtn = findClickable('제출') || findClickable('Submit');
      if (submitBtn) break;
      await delay(300);
    }}

    if (!submitBtn) {{
      console.log('💡 의견이 입력되었습니다. 수동으로 제출해주세요.');
      return;
    }}

    forceClick(submitBtn);
    console.log('✓ 제출 버튼 클릭 완료');
    await delay(2000);

    // Step 6: 닫기 버튼 클릭
    console.log('[6/6] 닫기 버튼 찾는 중...');

    let closeBtn = null;
    for (let retry = 0; retry < 20; retry++) {{
      // g-raised-button 안의 닫기 버튼
      const raisedButtons = document.querySelectorAll('g-raised-button[role="button"]');
      for (const btn of raisedButtons) {{
        if (btn.textContent.trim() === '닫기' && isVisible(btn)) {{
          closeBtn = btn;
          break;
        }}
      }}
      if (closeBtn) break;

      // 일반 검색
      closeBtn = findClickable('닫기') || findClickable('Close');
      if (closeBtn) break;

      await delay(300);
    }}

    if (closeBtn) {{
      forceClick(closeBtn);
      console.log('✅ 피드백 제출 및 닫기 완료!');
    }} else {{
      console.log('✅ 피드백 제출 완료! (닫기 버튼은 수동으로 클릭해주세요)');
    }}

  }} catch (error) {{
    console.error('오류:', error);
  }}
}})();
""".strip()

    return js_code


def generate_feedback_code_with_validation(template: dict) -> tuple[str, bool]:
    if not template.get('opinion'):
        return "", False
    try:
        return generate_feedback_code(template), True
    except Exception as e:
        return "", False
