# URL Collector - EXE 빌드 가이드

## Windows에서 EXE 만들기

### 방법 1: 자동 빌드 스크립트 (권장)

1. `build_windows.bat` 더블클릭
2. 완료 후 `dist\URLCollector.exe` 생성됨

### 방법 2: 수동 빌드

```cmd
# 1. 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate

# 2. 의존성 설치
pip install requests customtkinter pyinstaller

# 3. EXE 빌드
pyinstaller url_collector.spec --clean

# 4. 결과물
# dist\URLCollector.exe
```

## 배포

`dist\URLCollector.exe` 파일 하나만 배포하면 됩니다.
- Python 설치 불필요
- 추가 프로그램 불필요
- 더블클릭으로 바로 실행

## 사용법

1. `URLCollector.exe` 실행
2. Serper API 키 입력 (serper.dev에서 무료 발급)
3. 도메인 입력
4. SEO 페이지 / 게시글 모드 선택
5. URL 수집 클릭
6. 결과 저장

## 문제 해결

### "Windows에서 보호된 앱" 경고
- "추가 정보" → "실행" 클릭

### 백신이 차단하는 경우
- PyInstaller로 만든 exe는 가끔 오진될 수 있음
- 예외 등록 필요
