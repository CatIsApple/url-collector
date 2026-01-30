"""URL Collector - Dashboard Style GUI"""

import os
import sys
import json
import threading
from datetime import datetime
from typing import Optional
from urllib.parse import unquote

import customtkinter as ctk
from tkinter import font as tkfont


def get_font_path():
    """폰트 경로 반환 (PyInstaller 번들 지원)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 번들
        base_path = sys._MEIPASS
    else:
        # 개발 환경
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, 'fonts')


def load_pretendard_font():
    """Pretendard 폰트 로드"""
    font_path = get_font_path()
    regular_path = os.path.join(font_path, 'Pretendard-Regular.otf')
    bold_path = os.path.join(font_path, 'Pretendard-Bold.otf')

    # macOS/Windows에서 폰트 로드
    if sys.platform == 'darwin':
        # macOS: PyObjC를 사용하여 안전하게 폰트 등록
        try:
            from Foundation import NSURL
            from CoreText import CTFontManagerRegisterFontsForURL, kCTFontManagerScopeProcess
            for path in [regular_path, bold_path]:
                if os.path.exists(path):
                    font_url = NSURL.fileURLWithPath_(path)
                    CTFontManagerRegisterFontsForURL(font_url, kCTFontManagerScopeProcess, None)
        except ImportError:
            # PyObjC가 없으면 시스템 폰트 사용
            pass
        except Exception:
            pass
    elif sys.platform == 'win32':
        # Windows: AddFontResourceEx
        try:
            import ctypes
            FR_PRIVATE = 0x10
            for path in [regular_path, bold_path]:
                if os.path.exists(path):
                    ctypes.windll.gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
        except:
            pass

    return 'Pretendard' if os.path.exists(regular_path) else None


# 폰트 로드
FONT_FAMILY = load_pretendard_font() or 'SF Pro Display'


def decode_url(url: str) -> str:
    """URL 디코딩 (퍼센트 인코딩 → 한글)"""
    try:
        return unquote(url)
    except:
        return url


from .serper import SerperClient
from .filter import filter_urls
from .ai_filter import smart_filter_urls, calculate_score
from .brand_search import BrandSearcher, filter_brand_results, calculate_seo_score
from .groq_filter import GroqFilter, filter_urls_with_ai


# 프로페셔널 컬러 팔레트
COLORS = {
    "bg_dark": "#0a0a0a",
    "bg_card": "#151515",
    "bg_card_hover": "#1a1a1a",
    "bg_input": "#1f1f1f",
    "bg_sidebar": "#0f0f0f",
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "accent_subtle": "#1e3a5f",
    "success": "#22c55e",
    "success_subtle": "#14532d",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "text": "#ffffff",
    "text_secondary": "#a1a1aa",
    "text_muted": "#6b7280",
    "border": "#262626",
    "border_subtle": "#1f1f1f",
    "code_bg": "#0d0d0d",
}

# 공통 스타일
STYLES = {
    "card_radius": 16,
    "input_radius": 10,
    "button_radius": 8,
    "spacing_sm": 8,
    "spacing_md": 16,
    "spacing_lg": 24,
}

CONFIG_PATH = os.path.expanduser("~/.url-collector-config.json")

ctk.set_appearance_mode("dark")


class Toast(ctk.CTkFrame):
    """Toast 알림 컴포넌트"""

    def __init__(self, parent, message: str, toast_type: str = "success"):
        super().__init__(parent, corner_radius=8)

        # 타입별 색상
        colors = {
            "success": {"bg": "#166534", "border": "#22c55e"},
            "error": {"bg": "#991b1b", "border": "#ef4444"},
            "warning": {"bg": "#92400e", "border": "#f59e0b"},
            "info": {"bg": "#1e40af", "border": "#3b82f6"},
        }
        color = colors.get(toast_type, colors["info"])

        self.configure(fg_color=color["bg"], border_color=color["border"], border_width=1)

        # 아이콘
        icons = {"success": "✓", "error": "✕", "warning": "!", "info": "i"}
        icon = icons.get(toast_type, "i")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(padx=16, pady=12)

        ctk.CTkLabel(
            content,
            text=icon,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color="#ffffff",
            width=20
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            content,
            text=message,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color="#ffffff"
        ).pack(side="left")


class URLCollectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("URL Collector Pro")
        self.geometry("1200x1300")
        self.configure(fg_color=COLORS["bg_dark"])
        self.minsize(1000, 900)

        # 데이터
        self.results = {}
        self.api_key = ""
        self.config = self._load_config()
        self.toast_queue = []

        # 레이아웃
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_content()

        # 기본 페이지
        self._show_scraper_page()

    def _load_config(self) -> dict:
        """설정 파일 로드"""
        default_config = {
            "api_key": "",
            "applicant": {
                "country": "south_korea",
                "full_name": "",
                "company": "",
                "organization": "",
                "email": ""
            },
            "templates": []
        }

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # 기본값과 병합
                    for key in default_config:
                        if key not in loaded:
                            loaded[key] = default_config[key]
                    return loaded
            except:
                pass
        return default_config

    def _save_config(self):
        """설정 파일 저장"""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"설정 저장 실패: {e}")

    def _show_toast(self, message: str, toast_type: str = "success", duration: int = 3000):
        """Toast 알림 표시"""
        toast = Toast(self, message, toast_type)

        # 화면 하단 중앙에 배치
        toast.place(relx=0.5, rely=0.95, anchor="s")

        # 애니메이션: 위로 슬라이드
        toast.place(relx=0.5, rely=0.92, anchor="s")

        # 일정 시간 후 제거
        def remove_toast():
            try:
                toast.destroy()
            except:
                pass

        self.after(duration, remove_toast)

    # ==================== 사이드바 ====================
    def _create_sidebar(self):
        """사이드바 생성"""
        self.sidebar = ctk.CTkFrame(
            self, width=280,
            fg_color=COLORS["bg_sidebar"],
            corner_radius=0,
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # 로고/타이틀
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=24, pady=(32, 12))

        ctk.CTkLabel(
            logo_frame,
            text="URL Collector",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame,
            text="Google 법적 신고 자동화",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(2, 0))

        # 구분선
        ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color=COLORS["border"]
        ).pack(fill="x", padx=24, pady=(16, 20))

        # 메뉴 라벨
        ctk.CTkLabel(
            self.sidebar,
            text="메뉴",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", padx=24, pady=(0, 8))

        # 네비게이션
        self.nav_buttons = {}

        nav_items = [
            ("scraper", "🔍", "URL 수집", "사이트 URL 자동 수집", self._show_scraper_page),
            ("code", "📋", "신고 코드", "JS 코드 자동 생성", self._show_code_page),
            ("settings", "⚙️", "설정", "신청인 정보 및 템플릿", self._show_settings_page),
        ]

        for key, icon, title, desc, command in nav_items:
            btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            btn_frame.pack(fill="x", padx=16, pady=3)

            btn = ctk.CTkButton(
                btn_frame,
                text=f"{icon}   {title}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=14),
                fg_color="transparent",
                hover_color=COLORS["bg_card"],
                text_color=COLORS["text_secondary"],
                anchor="w",
                height=48,
                corner_radius=10,
                command=command
            )
            btn.pack(fill="x")
            self.nav_buttons[key] = btn

        # 하단 정보
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=24, pady=24)

        # 구분선
        ctk.CTkFrame(
            bottom_frame,
            height=1,
            fg_color=COLORS["border"]
        ).pack(fill="x", pady=(0, 16))

        info_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        info_row.pack(fill="x")

        ctk.CTkLabel(
            info_row,
            text="v1.0.0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_muted"]
        ).pack(side="left")

        ctk.CTkLabel(
            info_row,
            text="by 다아온",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_muted"]
        ).pack(side="right")

    def _set_active_nav(self, active_key: str):
        """활성 네비게이션 표시"""
        for key, btn in self.nav_buttons.items():
            if key == active_key:
                btn.configure(
                    fg_color=COLORS["accent_subtle"],
                    text_color=COLORS["accent"]
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS["text_secondary"]
                )

    # ==================== 메인 컨텐츠 ====================
    def _create_main_content(self):
        """메인 컨텐츠 영역"""
        self.main_content = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

        # 페이지 컨테이너
        self.pages = {}

    def _clear_pages(self):
        """모든 페이지 숨기기"""
        for page in self.pages.values():
            page.grid_forget()

    # ==================== URL 수집 페이지 ====================
    def _show_scraper_page(self):
        self._set_active_nav("scraper")
        self._clear_pages()

        if "scraper" not in self.pages:
            self._create_scraper_page()

        self.pages["scraper"].grid(row=0, column=0, sticky="nsew", padx=30, pady=30)

    def _create_scraper_page(self):
        """URL 수집 페이지 생성"""
        page = ctk.CTkFrame(self.main_content, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        self.pages["scraper"] = page

        # 헤더
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 24))

        header_text = ctk.CTkFrame(header, fg_color="transparent")
        header_text.pack(side="left")

        ctk.CTkLabel(
            header_text,
            text="URL 수집",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_text,
            text="Serper API를 사용하여 사이트의 SEO 페이지를 수집합니다",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(4, 0))

        # 입력 영역
        input_card = ctk.CTkFrame(
            page,
            fg_color=COLORS["bg_card"],
            corner_radius=STYLES["card_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        input_card.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        input_card.grid_columnconfigure(0, weight=1)

        # API Key
        api_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        api_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 16))
        api_frame.grid_columnconfigure(0, weight=1)

        api_label_row = ctk.CTkFrame(api_frame, fg_color="transparent")
        api_label_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            api_label_row,
            text="Serper API Key",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")

        ctk.CTkLabel(
            api_label_row,
            text="serper.dev에서 발급",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLORS["text_muted"]
        ).pack(side="right")

        self.api_entry = ctk.CTkEntry(
            api_frame,
            height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            placeholder_text="API 키를 입력하세요",
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=STYLES["input_radius"],
            show="•"
        )
        self.api_entry.grid(row=1, column=0, sticky="ew")
        if self.config.get("api_key"):
            self.api_entry.insert(0, self.config["api_key"])

        # 도메인 입력
        domain_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        domain_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        domain_frame.grid_columnconfigure(0, weight=1)

        domain_label_row = ctk.CTkFrame(domain_frame, fg_color="transparent")
        domain_label_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            domain_label_row,
            text="도메인",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")

        ctk.CTkLabel(
            domain_label_row,
            text="한 줄에 하나씩",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLORS["text_muted"]
        ).pack(side="right")

        self.domain_textbox = ctk.CTkTextbox(
            domain_frame,
            height=90,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=STYLES["input_radius"]
        )
        self.domain_textbox.grid(row=1, column=0, sticky="ew")

        # 옵션 & 버튼
        options_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        options_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(8, 24))

        mode_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        mode_frame.pack(side="left")

        self.search_mode_var = ctk.StringVar(value="seo")

        ctk.CTkRadioButton(
            mode_frame,
            text="SEO 페이지",
            variable=self.search_mode_var,
            value="seo",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color=COLORS["accent"],
            border_color=COLORS["border"]
        ).pack(side="left", padx=(0, 20))

        ctk.CTkRadioButton(
            mode_frame,
            text="게시글",
            variable=self.search_mode_var,
            value="article",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color=COLORS["accent"],
            border_color=COLORS["border"]
        ).pack(side="left")

        self.search_btn = ctk.CTkButton(
            options_frame,
            text="🔍  수집 시작",
            width=140,
            height=40,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=STYLES["button_radius"],
            command=self._on_search
        )
        self.search_btn.pack(side="right")

        # 결과 영역
        result_frame = ctk.CTkFrame(page, fg_color="transparent")
        result_frame.grid(row=2, column=0, sticky="nsew")
        result_frame.grid_columnconfigure(0, weight=3)
        result_frame.grid_columnconfigure(1, weight=2)
        result_frame.grid_rowconfigure(0, weight=1)

        # 결과 카드
        result_card = ctk.CTkFrame(
            result_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=STYLES["card_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        result_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        result_card.grid_columnconfigure(0, weight=1)
        result_card.grid_rowconfigure(1, weight=1)

        result_header = ctk.CTkFrame(result_card, fg_color="transparent")
        result_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))

        ctk.CTkLabel(
            result_header,
            text="📄  수집 결과",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")

        self.result_count = ctk.CTkLabel(
            result_header,
            text="0개",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLORS["accent"],
            fg_color=COLORS["accent_subtle"],
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.result_count.pack(side="left", padx=(12, 0))

        btn_group = ctk.CTkFrame(result_header, fg_color="transparent")
        btn_group.pack(side="right")

        ctk.CTkButton(
            btn_group, text="📋 복사", width=80, height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLORS["bg_input"], hover_color=COLORS["border"],
            border_width=1, border_color=COLORS["border"],
            corner_radius=STYLES["button_radius"], command=self._on_copy
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_group, text="💾 저장", width=80, height=34,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLORS["bg_input"], hover_color=COLORS["border"],
            border_width=1, border_color=COLORS["border"],
            corner_radius=STYLES["button_radius"], command=self._on_save
        ).pack(side="left")

        self.result_textbox = ctk.CTkTextbox(
            result_card,
            font=ctk.CTkFont(family="SF Mono", size=11),
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border_subtle"],
            corner_radius=STYLES["input_radius"]
        )
        self.result_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        # 로그 카드
        log_card = ctk.CTkFrame(
            result_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=STYLES["card_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        log_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))

        ctk.CTkLabel(
            log_header,
            text="📝  로그",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family="SF Mono", size=11),
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border_subtle"],
            corner_radius=STYLES["input_radius"]
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        # 로그 태그 설정
        self.log_textbox._textbox.tag_config("time", foreground="#6b7280")
        self.log_textbox._textbox.tag_config("info", foreground="#a1a1aa")
        self.log_textbox._textbox.tag_config("success", foreground="#22c55e")
        self.log_textbox._textbox.tag_config("warning", foreground="#f59e0b")
        self.log_textbox._textbox.tag_config("error", foreground="#ef4444")
        self.log_textbox._textbox.tag_config("accent", foreground="#3b82f6")

    # ==================== 신고 코드 페이지 ====================
    def _show_code_page(self):
        self._set_active_nav("code")
        self._clear_pages()

        if "code" not in self.pages:
            self._create_code_page()
        else:
            # 도메인 콤보박스 업데이트
            self._update_domain_combo()

        self.pages["code"].grid(row=0, column=0, sticky="nsew", padx=30, pady=30)

    def _create_code_page(self):
        """신고 코드 페이지 생성"""
        page = ctk.CTkFrame(self.main_content, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        self.pages["code"] = page

        # 헤더
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 24))

        header_text = ctk.CTkFrame(header, fg_color="transparent")
        header_text.pack(side="left")

        ctk.CTkLabel(
            header_text,
            text="신고 코드 생성",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_text,
            text="Google 법적 신고 양식을 자동으로 채우는 JavaScript 코드",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(4, 0))

        # 메인 컨텐츠
        content = ctk.CTkFrame(page, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        # 왼쪽: 옵션
        options_card = ctk.CTkFrame(
            content,
            fg_color=COLORS["bg_card"],
            corner_radius=STYLES["card_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        options_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # 도메인 선택
        domain_section = ctk.CTkFrame(options_card, fg_color="transparent")
        domain_section.pack(fill="x", padx=24, pady=(24, 20))

        ctk.CTkLabel(
            domain_section,
            text="도메인 선택",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", pady=(0, 10))

        self.code_domain_var = ctk.StringVar(value="")
        self.code_domain_combo = ctk.CTkComboBox(
            domain_section,
            values=list(self.results.keys()) if self.results else ["수집된 도메인 없음"],
            variable=self.code_domain_var,
            height=40,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            button_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            corner_radius=STYLES["input_radius"],
            command=self._on_domain_change
        )
        self.code_domain_combo.pack(fill="x")

        # 템플릿 선택
        template_section = ctk.CTkFrame(options_card, fg_color="transparent")
        template_section.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkLabel(
            template_section,
            text="템플릿 선택",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", pady=(0, 10))

        template_names = [t["name"] for t in self.config.get("templates", [])]
        if not template_names:
            template_names = ["템플릿 없음 (설정에서 추가)"]

        self.code_template_var = ctk.StringVar(value=template_names[0] if template_names else "")
        self.code_template_combo = ctk.CTkComboBox(
            template_section,
            values=template_names,
            variable=self.code_template_var,
            height=40,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            button_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            corner_radius=STYLES["input_radius"],
            command=self._on_template_change
        )
        self.code_template_combo.pack(fill="x")

        # 자동 제출 옵션
        auto_submit_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        auto_submit_frame.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkLabel(
            auto_submit_frame,
            text="자동 제출",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")

        self.auto_submit_var = ctk.BooleanVar(value=False)
        self.auto_submit_switch = ctk.CTkSwitch(
            auto_submit_frame,
            text="",
            variable=self.auto_submit_var,
            width=44,
            height=22,
            fg_color=COLORS["border"],
            progress_color=COLORS["accent"],
            button_color=COLORS["text"],
            button_hover_color=COLORS["text_secondary"]
        )
        self.auto_submit_switch.pack(side="right")

        ctk.CTkLabel(
            options_card,
            text="⚠️ 활성화 시 제출 버튼까지 자동 클릭됩니다",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["warning"]
        ).pack(anchor="w", padx=24, pady=(0, 8))

        # 코드 생성 버튼
        ctk.CTkButton(
            options_card,
            text="⚡  코드 생성",
            height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=STYLES["button_radius"],
            command=self._generate_report_code
        ).pack(fill="x", padx=24, pady=(8, 24))

        # 안내 텍스트
        guide_frame = ctk.CTkFrame(
            options_card,
            fg_color=COLORS["bg_input"],
            corner_radius=STYLES["input_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        guide_frame.pack(fill="x", padx=24, pady=(0, 24))

        ctk.CTkLabel(
            guide_frame,
            text="💡  사용법",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=16, pady=(16, 8))

        guide_text = """1. Google 법적 신고 페이지 열기
2. F12 → Console 탭 선택
3. 'allow pasting' 입력 후 Enter
4. 생성된 코드 붙여넣기
5. Enter 키로 실행"""

        ctk.CTkLabel(
            guide_frame,
            text=guide_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLORS["text_muted"],
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 16))

        # 오른쪽: 코드 영역
        code_card = ctk.CTkFrame(
            content,
            fg_color=COLORS["bg_card"],
            corner_radius=STYLES["card_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        code_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        code_card.grid_columnconfigure(0, weight=1)
        code_card.grid_rowconfigure(1, weight=1)

        code_header = ctk.CTkFrame(code_card, fg_color="transparent")
        code_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))

        ctk.CTkLabel(
            code_header,
            text="</> JavaScript 코드",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")

        ctk.CTkButton(
            code_header,
            text="복사",
            width=80,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            corner_radius=6,
            command=self._copy_report_code
        ).pack(side="right")

        self.code_textbox = ctk.CTkTextbox(
            code_card,
            font=ctk.CTkFont(family="SF Mono", size=11),
            fg_color=COLORS["code_bg"],
            text_color="#d4d4d4",
            border_width=0,
            corner_radius=8
        )
        self.code_textbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # 초기 안내 메시지
        self.code_textbox.insert("0.0", "// 도메인을 선택하고 '코드 생성' 버튼을 클릭하세요")

    def _update_domain_combo(self):
        """도메인 콤보박스 업데이트"""
        if hasattr(self, 'code_domain_combo'):
            domains = list(self.results.keys()) if self.results else ["수집된 도메인 없음"]
            self.code_domain_combo.configure(values=domains)
            if domains and domains[0] != "수집된 도메인 없음":
                self.code_domain_var.set(domains[0])

    def _update_template_combo(self):
        """템플릿 콤보박스 업데이트"""
        if hasattr(self, 'code_template_combo'):
            template_names = [t["name"] for t in self.config.get("templates", [])]
            if not template_names:
                template_names = ["템플릿 없음 (설정에서 추가)"]
            self.code_template_combo.configure(values=template_names)
            self.code_template_var.set(template_names[0])

    def _on_domain_change(self, value):
        pass

    def _on_template_change(self, value):
        pass

    def _generate_report_code(self):
        """신고 코드 생성"""
        domain = self.code_domain_var.get()

        if not domain or domain == "수집된 도메인 없음":
            self.code_textbox.delete("0.0", "end")
            self.code_textbox.insert("0.0", "// URL 수집 페이지에서 먼저 도메인을 수집하세요")
            return

        if domain not in self.results:
            return

        urls = [decode_url(item["url"]) for item in self.results[domain]]
        applicant = self.config.get("applicant", {})

        # 선택된 템플릿 가져오기
        template_name = self.code_template_var.get()
        template = None
        for t in self.config.get("templates", []):
            if t["name"] == template_name:
                template = t
                break

        urls_js = ",\n".join([f'  "{url}"' for url in urls])

        # JavaScript 코드 생성
        js_code = f'''// {domain} - {len(urls)}개 URL 자동 신고 코드
// Google 법적 신고 페이지에서 실행하세요

(async function() {{
  const delay = ms => new Promise(r => setTimeout(r, ms));

  // ========== 거주 국가 선택 (한국) ==========
  // 여러 가능한 셀렉터 시도
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
      // 옵션 중에 한국이 있는지 확인
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
        console.log('✓ 거주 국가: 한국 선택 (' + koreaOption.value + ')');
        break;
      }}
    }}
  }}

  if (!countrySelect) {{
    console.log('⚠ 국가 선택 필드를 찾지 못했습니다. 수동으로 선택해주세요.');
  }}
  await delay(300);

  // ========== 신청인 정보 ==========
  const applicant = {{
    fullName: "{applicant.get('full_name', '')}",
    company: "{applicant.get('company', '')}",
    organization: "{applicant.get('organization', '')}",
    email: "{applicant.get('email', '')}"
  }};

  // 실명 입력
  const nameInput = document.querySelector('input[name="full_name"]');
  if (nameInput && applicant.fullName) {{
    nameInput.value = applicant.fullName;
    nameInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  // 회사 이름
  const companyInput = document.querySelector('input[name="companyname"]');
  if (companyInput && applicant.company) {{
    companyInput.value = applicant.company;
    companyInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  // 대표 조직
  const orgInput = document.querySelector('input[name="represented_copyright_holder"]');
  if (orgInput && applicant.organization) {{
    orgInput.value = applicant.organization;
    orgInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  // 이메일
  const emailInput = document.querySelector('input[name="contact_email"]');
  if (emailInput && applicant.email) {{
    emailInput.value = applicant.email;
    emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  console.log('✓ 신청인 정보 입력 완료');
  await delay(300);
'''

        # 템플릿이 있으면 추가
        if template:
            reason = template.get("reason", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            evidence = template.get("evidence", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            check_explicit = "true" if template.get("check_explicit", False) else "false"
            check_subject = "true" if template.get("check_subject", False) else "false"
            check_telecom = "true" if template.get("check_telecom", False) else "false"
            report_reason = template.get("report_reason", "불법 사진 및 동영상").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            victim_name = template.get("victim_name", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            search_keyword = template.get("search_keyword", "").replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

            js_code += f'''
  // ========== 권리 침해 유형 체크박스 ==========
  const checkOptions = {{
    explicit: {check_explicit},   // 선정적 이미지/아동 학대
    subject: {check_subject},     // 피사체/법적 대리인
    telecom: {check_telecom}      // 전기통신사업법
  }};

  // 모든 체크박스 순회하며 해당 항목 선택
  const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
  for (const cb of allCheckboxes) {{
    const fieldText = cb.closest('.field')?.textContent || '';

    // 선정적 이미지/아동 학대 체크박스
    if (checkOptions.explicit && (fieldText.includes('선정적 이미지') || fieldText.includes('아동 성적 학대'))) {{
      if (!cb.checked) cb.click();
      console.log('✓ 선정적 이미지/아동 학대 체크');
    }}

    // 피사체/법적 대리인 체크박스
    if (checkOptions.subject && (fieldText.includes('피사체') || fieldText.includes('법적 대리인'))) {{
      if (!cb.checked) cb.click();
      console.log('✓ 피사체/법적 대리인 체크');
    }}

    // 전기통신사업법 체크박스
    if (checkOptions.telecom && (fieldText.includes('전기통신사업법') || fieldText.includes('Telecommunications Business Act'))) {{
      if (!cb.checked) cb.click();
      console.log('✓ 전기통신사업법 체크');
    }}
  }}
  await delay(500);

  // ========== 콘텐츠 신고 사유 드롭다운 선택 ==========
  const reportReason = `{report_reason}`;
  if (reportReason) {{
    // 드롭다운 찾기 (체크박스 선택 후 나타남)
    const allSelects = document.querySelectorAll('select');
    for (const sel of allSelects) {{
      const fieldText = sel.closest('.field')?.textContent || '';
      if (fieldText.includes('콘텐츠 신고 사유') || fieldText.includes('신고 사유')) {{
        // 옵션 찾기
        const options = Array.from(sel.options);
        const targetOption = options.find(opt =>
          opt.text.includes(reportReason) ||
          opt.value.includes(reportReason)
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
        console.log('✓ 피해자 이름 입력: ' + victimName);
        break;
      }}
    }}
  }}
  await delay(200);

  // ========== 검색어 입력 (전기통신사업법 선택 시) ==========
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
  // 불법 이유 설명 (위 URL의 콘텐츠가 불법이라고 생각되는 이유)
  const allTextareas = document.querySelectorAll('textarea');
  for (const textarea of allTextareas) {{
    const label = textarea.closest('.field')?.querySelector('label')?.textContent || '';
    // 불법 이유 필드
    if (label.includes('불법이라고 생각되는 이유') || textarea.name === 'explanation' || textarea.name === 'dmca_explanation') {{
      textarea.value = `{reason}`;
      textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
      console.log('✓ 불법 이유 입력 완료');
    }}
    // 침해 증거/인용 필드
    if (label.includes('권리를 침해한 것으로 보이는') || label.includes('정확한 텍스트를 인용') || textarea.name === 'infringe_explanation' || textarea.name === 'dmca_infringe_explanation') {{
      textarea.value = `{evidence}`;
      textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
      console.log('✓ 침해 증거 입력 완료');
    }}
  }}
  await delay(300);
'''

        js_code += f'''
  // ========== URL 입력 ==========
  const urls = [
{urls_js}
  ];

  // URL 입력 필드 찾기
  const addButtons = document.querySelectorAll('a.add-additional');
  let targetButton = null;

  for (const btn of addButtons) {{
    const parent = btn.closest('.field');
    if (parent && parent.querySelector('#url_box3')) {{
      targetButton = btn;
      break;
    }}
  }}

  // 첫 번째 URL 입력
  const firstInput = document.querySelector('#url_box3');
  if (firstInput && urls[0]) {{
    firstInput.value = urls[0];
    firstInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    console.log('1/' + urls.length + ': ' + urls[0].substring(0, 50) + '...');
  }}

  // 나머지 URL 추가
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

  // ========== 확인/동의 체크박스 (권리 침해 유형 제외) ==========
  const confirmCheckboxes = document.querySelectorAll('input[type="checkbox"]');
  for (const checkbox of confirmCheckboxes) {{
    const fieldText = checkbox.closest('.field')?.textContent || '';
    // 권리 침해 유형 체크박스는 건너뛰기 (이미 위에서 처리함)
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

        # 자동 제출 옵션이 켜져 있으면 제출 코드 추가
        if self.auto_submit_var.get():
            js_code += '''
  // ========== 자동 제출 ==========
  await delay(1000);
  const submitButton = document.querySelector('input[type="submit"], button[type="submit"], .submit-button, button[name="submit"]');
  if (submitButton) {
    console.log('🚀 제출 버튼 클릭 중...');
    submitButton.click();
    console.log('✓ 제출 완료!');
  } else {
    console.log('⚠ 제출 버튼을 찾지 못했습니다. 수동으로 제출해주세요.');
  }
'''
        else:
            js_code += '''  console.log('제출 전 내용을 확인하세요.');
'''

        js_code += '''})();
'''

        self.code_textbox.delete("0.0", "end")
        self.code_textbox.insert("0.0", js_code)

    def _copy_report_code(self):
        """신고 코드 복사"""
        code = self.code_textbox.get("0.0", "end").strip()
        # 실제 생성된 코드인지 확인 (async function 포함 여부)
        if code and "(async function()" in code:
            self.clipboard_clear()
            self.clipboard_append(code)
            self._show_toast("코드가 클립보드에 복사되었습니다", "success")
        else:
            self._show_toast("먼저 코드를 생성해주세요", "warning")

    # ==================== 설정 페이지 ====================
    def _show_settings_page(self):
        self._set_active_nav("settings")
        self._clear_pages()

        if "settings" not in self.pages:
            self._create_settings_page()

        self.pages["settings"].grid(row=0, column=0, sticky="nsew", padx=30, pady=30)

    def _create_settings_page(self):
        """설정 페이지 생성"""
        page = ctk.CTkFrame(self.main_content, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(1, weight=1)
        self.pages["settings"] = page

        # 헤더
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 24))

        header_text = ctk.CTkFrame(header, fg_color="transparent")
        header_text.pack(side="left")

        ctk.CTkLabel(
            header_text,
            text="설정",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_text,
            text="신청인 정보와 신고 템플릿을 관리합니다",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(4, 0))

        # 왼쪽: 신청인 정보
        applicant_card = ctk.CTkFrame(
            page,
            fg_color=COLORS["bg_card"],
            corner_radius=STYLES["card_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        applicant_card.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

        ctk.CTkLabel(
            applicant_card,
            text="👤  신청인 정보",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=24, pady=(24, 20))

        # 입력 필드들
        applicant = self.config.get("applicant", {})

        fields = [
            ("full_name", "실명", "필수 입력", applicant.get("full_name", "")),
            ("email", "이메일", "필수 입력", applicant.get("email", "")),
            ("company", "회사 이름", "선택 사항", applicant.get("company", "")),
            ("organization", "대표 조직", "선택 사항", applicant.get("organization", "")),
        ]

        self.settings_entries = {}

        for key, label, hint, value in fields:
            frame = ctk.CTkFrame(applicant_card, fg_color="transparent")
            frame.pack(fill="x", padx=24, pady=(0, 16))

            label_row = ctk.CTkFrame(frame, fg_color="transparent")
            label_row.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(
                label_row,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=COLORS["text"]
            ).pack(side="left")

            ctk.CTkLabel(
                label_row,
                text=hint,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=COLORS["text_muted"]
            ).pack(side="right")

            entry = ctk.CTkEntry(
                frame,
                height=40,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                fg_color=COLORS["bg_input"],
                border_color=COLORS["border"],
                border_width=1,
                corner_radius=STYLES["input_radius"]
            )
            entry.pack(fill="x")
            entry.insert(0, value)
            self.settings_entries[key] = entry

        # 저장 버튼
        ctk.CTkButton(
            applicant_card,
            text="💾  저장",
            height=40,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=STYLES["button_radius"],
            command=self._save_applicant_info
        ).pack(fill="x", padx=24, pady=(8, 24))

        # 오른쪽: 템플릿 관리
        template_card = ctk.CTkFrame(
            page,
            fg_color=COLORS["bg_card"],
            corner_radius=STYLES["card_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        template_card.grid(row=1, column=1, sticky="nsew", padx=(12, 0))
        template_card.grid_rowconfigure(2, weight=1)

        template_header = ctk.CTkFrame(template_card, fg_color="transparent")
        template_header.pack(fill="x", padx=24, pady=(24, 20))

        ctk.CTkLabel(
            template_header,
            text="📝  템플릿 관리",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")

        ctk.CTkButton(
            template_header,
            text="+ 새 템플릿",
            width=100,
            height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=STYLES["button_radius"],
            command=self._add_new_template
        ).pack(side="right")

        # 템플릿 리스트 (고정 높이 컨테이너)
        list_container = ctk.CTkFrame(
            template_card,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            height=100
        )
        list_container.pack(fill="x", padx=24, pady=(0, 12))
        list_container.pack_propagate(False)

        self.template_list_frame = ctk.CTkScrollableFrame(
            list_container,
            fg_color="transparent"
        )
        self.template_list_frame.pack(fill="both", expand=True)

        self._refresh_template_list()

        # 템플릿 편집 영역 (컨테이너)
        edit_container = ctk.CTkFrame(
            template_card,
            fg_color=COLORS["bg_input"],
            corner_radius=STYLES["input_radius"],
            border_width=1,
            border_color=COLORS["border_subtle"]
        )
        edit_container.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        # 스크롤 가능한 편집 영역
        edit_frame = ctk.CTkScrollableFrame(
            edit_container,
            fg_color="transparent"
        )
        edit_frame.pack(fill="both", expand=True, padx=4, pady=(8, 0))

        self.template_name_entry = ctk.CTkEntry(
            edit_frame,
            height=40,
            placeholder_text="템플릿 이름을 입력하세요",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=STYLES["input_radius"]
        )
        self.template_name_entry.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            edit_frame,
            text="불법 이유 설명",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", padx=16)

        self.template_reason_textbox = ctk.CTkTextbox(
            edit_frame,
            height=70,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border_subtle"],
            corner_radius=STYLES["input_radius"]
        )
        self.template_reason_textbox.pack(fill="x", padx=16, pady=(6, 12))

        ctk.CTkLabel(
            edit_frame,
            text="침해 증거/인용",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", padx=16)

        self.template_evidence_textbox = ctk.CTkTextbox(
            edit_frame,
            height=60,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border_subtle"],
            corner_radius=STYLES["input_radius"]
        )
        self.template_evidence_textbox.pack(fill="x", padx=16, pady=(6, 10))

        # 체크박스 옵션
        ctk.CTkLabel(
            edit_frame,
            text="권리 침해 유형 (해당 항목 선택)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", padx=16, pady=(4, 6))

        # 체크박스 1: 선정적 이미지/아동 학대 (항상 표시)
        self.template_check1_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            edit_frame,
            text="선정적 이미지 또는 아동 성적 학대 콘텐츠",
            variable=self.template_check1_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            border_color=COLORS["border"],
            hover_color=COLORS["accent_hover"],
            corner_radius=4,
            command=self._on_check1_changed
        ).pack(anchor="w", padx=16, pady=2)

        # === 체크박스1 선택 시 나타나는 영역 ===
        self.check1_dependent_frame = ctk.CTkFrame(edit_frame, fg_color="transparent")

        # 체크박스 2: 피사체/법적 대리인
        self.template_check2_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.check1_dependent_frame,
            text="이미지/동영상의 피사체 또는 법적 대리인",
            variable=self.template_check2_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            border_color=COLORS["border"],
            hover_color=COLORS["accent_hover"],
            corner_radius=4,
            command=self._on_check2_changed
        ).pack(anchor="w", pady=2)

        # === 체크박스2 선택 시 나타나는 영역 ===
        self.check2_dependent_frame = ctk.CTkFrame(self.check1_dependent_frame, fg_color="transparent")

        # 체크박스 3: 전기통신사업법
        self.template_check3_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.check2_dependent_frame,
            text="전기통신사업법에 따른 불법 콘텐츠",
            variable=self.template_check3_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            border_color=COLORS["border"],
            hover_color=COLORS["accent_hover"],
            corner_radius=4,
            command=self._on_check3_changed
        ).pack(anchor="w", pady=2)

        # === 체크박스3 선택 시 나타나는 영역 (콘텐츠 신고 사유) ===
        self.check3_dependent_frame = ctk.CTkFrame(self.check2_dependent_frame, fg_color="transparent")

        ctk.CTkLabel(
            self.check3_dependent_frame,
            text="콘텐츠 신고 사유",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(4, 2))

        self.template_report_reason_var = ctk.StringVar(value="불법 사진 및 동영상")
        self.template_report_reason_combo = ctk.CTkComboBox(
            self.check3_dependent_frame,
            height=32,
            values=["불법 사진 및 동영상", "가짜 이미지 및 동영상", "아동 및 청소년 성적 학대 콘텐츠"],
            variable=self.template_report_reason_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            border_width=1,
            button_color=COLORS["border"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["bg_input"],
            corner_radius=6,
            state="readonly"
        )
        self.template_report_reason_combo.pack(fill="x", pady=(0, 4))

        # 피해자 이름 (체크박스1 선택 시 표시)
        ctk.CTkLabel(
            self.check1_dependent_frame,
            text="피해자 이름 (이미지/동영상에 표시되는 사람)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(6, 2))

        self.template_victim_name_entry = ctk.CTkEntry(
            self.check1_dependent_frame,
            height=32,
            placeholder_text="성과 이름을 입력하세요",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=6
        )
        self.template_victim_name_entry.pack(fill="x", pady=(0, 4))

        # 검색어 입력 (체크박스1 선택 시 표시)
        ctk.CTkLabel(
            self.check1_dependent_frame,
            text="콘텐츠를 찾기 위해 사용한 검색어",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(4, 2))

        self.template_keyword_entry = ctk.CTkEntry(
            self.check1_dependent_frame,
            height=32,
            placeholder_text="검색어 입력",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=6
        )
        self.template_keyword_entry.pack(fill="x", pady=(0, 6))

        # 저장 버튼 (스크롤 영역 밖, 하단 고정)
        ctk.CTkButton(
            edit_container,
            text="💾  템플릿 저장",
            height=38,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=STYLES["button_radius"],
            command=self._save_template
        ).pack(fill="x", padx=12, pady=12)

        self.current_template_index = None

        # 초기 상태에서는 의존 프레임들 숨김
        self.check1_dependent_frame.pack_forget()
        self.check2_dependent_frame.pack_forget()
        self.check3_dependent_frame.pack_forget()

    def _refresh_template_list(self):
        """템플릿 리스트 새로고침"""
        for widget in self.template_list_frame.winfo_children():
            widget.destroy()

        templates = self.config.get("templates", [])

        if not templates:
            empty_frame = ctk.CTkFrame(self.template_list_frame, fg_color="transparent")
            empty_frame.pack(fill="x", pady=24)

            ctk.CTkLabel(
                empty_frame,
                text="📭",
                font=ctk.CTkFont(family=FONT_FAMILY, size=24),
                text_color=COLORS["text_muted"]
            ).pack()

            ctk.CTkLabel(
                empty_frame,
                text="저장된 템플릿이 없습니다",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLORS["text_muted"]
            ).pack(pady=(8, 0))
            return

        for i, template in enumerate(templates):
            item_frame = ctk.CTkFrame(
                self.template_list_frame,
                fg_color=COLORS["bg_input"],
                corner_radius=STYLES["button_radius"],
                border_width=1,
                border_color=COLORS["border_subtle"]
            )
            item_frame.pack(fill="x", pady=3)

            ctk.CTkLabel(
                item_frame,
                text=f"📋  {template['name']}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLORS["text"]
            ).pack(side="left", padx=14, pady=10)

            btn_group = ctk.CTkFrame(item_frame, fg_color="transparent")
            btn_group.pack(side="right", padx=10)

            ctk.CTkButton(
                btn_group,
                text="편집",
                width=56,
                height=28,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                fg_color="transparent",
                hover_color=COLORS["border"],
                border_width=1,
                border_color=COLORS["border"],
                corner_radius=6,
                command=lambda idx=i: self._edit_template(idx)
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                btn_group,
                text="삭제",
                width=56,
                height=28,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                fg_color="transparent",
                hover_color="#3f1515",
                text_color=COLORS["error"],
                border_width=1,
                border_color="#4a2020",
                corner_radius=6,
                command=lambda idx=i: self._delete_template(idx)
            ).pack(side="left")

    def _on_check1_changed(self):
        """체크박스1 상태 변경 시 의존 UI 업데이트"""
        if self.template_check1_var.get():
            self.check1_dependent_frame.pack(fill="x", padx=16, pady=(4, 0))
        else:
            self.check1_dependent_frame.pack_forget()
            # 하위 체크박스들도 해제
            self.template_check2_var.set(False)
            self.template_check3_var.set(False)
            self._on_check2_changed()

    def _on_check2_changed(self):
        """체크박스2 상태 변경 시 의존 UI 업데이트"""
        if self.template_check2_var.get():
            self.check2_dependent_frame.pack(fill="x", pady=(4, 0))
        else:
            self.check2_dependent_frame.pack_forget()
            # 하위 체크박스도 해제
            self.template_check3_var.set(False)
            self._on_check3_changed()

    def _on_check3_changed(self):
        """체크박스3 상태 변경 시 의존 UI 업데이트"""
        if self.template_check3_var.get():
            self.check3_dependent_frame.pack(fill="x", pady=(4, 0))
        else:
            self.check3_dependent_frame.pack_forget()

    def _update_template_checkboxes_visibility(self):
        """체크박스 상태에 따라 UI 가시성 업데이트"""
        # 체크박스1 상태에 따라
        if self.template_check1_var.get():
            self.check1_dependent_frame.pack(fill="x", padx=16, pady=(4, 0))
            # 체크박스2 상태에 따라
            if self.template_check2_var.get():
                self.check2_dependent_frame.pack(fill="x", pady=(4, 0))
                # 체크박스3 상태에 따라
                if self.template_check3_var.get():
                    self.check3_dependent_frame.pack(fill="x", pady=(4, 0))
                else:
                    self.check3_dependent_frame.pack_forget()
            else:
                self.check2_dependent_frame.pack_forget()
                self.check3_dependent_frame.pack_forget()
        else:
            self.check1_dependent_frame.pack_forget()
            self.check2_dependent_frame.pack_forget()
            self.check3_dependent_frame.pack_forget()

    def _add_new_template(self):
        """새 템플릿 추가 준비"""
        self.current_template_index = None
        self.template_name_entry.delete(0, "end")
        self.template_reason_textbox.delete("0.0", "end")
        self.template_evidence_textbox.delete("0.0", "end")
        self.template_check1_var.set(False)
        self.template_check2_var.set(False)
        self.template_check3_var.set(False)
        self.template_report_reason_var.set("불법 사진 및 동영상")
        self.template_victim_name_entry.delete(0, "end")
        self.template_keyword_entry.delete(0, "end")
        self._update_template_checkboxes_visibility()
        self.template_name_entry.focus()

    def _edit_template(self, index: int):
        """템플릿 편집"""
        templates = self.config.get("templates", [])
        if index < len(templates):
            template = templates[index]
            self.current_template_index = index

            self.template_name_entry.delete(0, "end")
            self.template_name_entry.insert(0, template.get("name", ""))

            self.template_reason_textbox.delete("0.0", "end")
            self.template_reason_textbox.insert("0.0", template.get("reason", ""))

            self.template_evidence_textbox.delete("0.0", "end")
            self.template_evidence_textbox.insert("0.0", template.get("evidence", ""))

            # 체크박스 상태 로드
            self.template_check1_var.set(template.get("check_explicit", False))
            self.template_check2_var.set(template.get("check_subject", False))
            self.template_check3_var.set(template.get("check_telecom", False))

            # 콘텐츠 신고 사유 로드
            report_reason = template.get("report_reason", "불법 사진 및 동영상")
            self.template_report_reason_var.set(report_reason)

            # 피해자 이름 로드
            self.template_victim_name_entry.delete(0, "end")
            self.template_victim_name_entry.insert(0, template.get("victim_name", ""))

            # 검색어 로드
            self.template_keyword_entry.delete(0, "end")
            self.template_keyword_entry.insert(0, template.get("search_keyword", ""))

            # 체크박스 상태에 따라 UI 가시성 업데이트
            self._update_template_checkboxes_visibility()

    def _delete_template(self, index: int):
        """템플릿 삭제"""
        templates = self.config.get("templates", [])
        if index < len(templates):
            name = templates[index].get("name", "")
            templates.pop(index)
            self.config["templates"] = templates
            self._save_config()
            self._refresh_template_list()
            self._update_template_combo()
            self._show_toast(f"'{name}' 템플릿이 삭제되었습니다", "info")

    def _save_template(self):
        """템플릿 저장"""
        name = self.template_name_entry.get().strip()
        reason = self.template_reason_textbox.get("0.0", "end").strip()
        evidence = self.template_evidence_textbox.get("0.0", "end").strip()

        if not name:
            self._show_toast("템플릿 이름을 입력해주세요", "warning")
            return

        template = {
            "name": name,
            "reason": reason,
            "evidence": evidence,
            "check_explicit": self.template_check1_var.get(),
            "check_subject": self.template_check2_var.get(),
            "check_telecom": self.template_check3_var.get(),
            "report_reason": self.template_report_reason_var.get(),
            "victim_name": self.template_victim_name_entry.get().strip(),
            "search_keyword": self.template_keyword_entry.get().strip()
        }

        templates = self.config.get("templates", [])

        if self.current_template_index is not None:
            templates[self.current_template_index] = template
            self._show_toast(f"'{name}' 템플릿이 수정되었습니다", "success")
        else:
            templates.append(template)
            self._show_toast(f"'{name}' 템플릿이 추가되었습니다", "success")

        self.config["templates"] = templates
        self._save_config()
        self._refresh_template_list()
        self._update_template_combo()

        # 입력 필드 초기화
        self.current_template_index = None
        self.template_name_entry.delete(0, "end")
        self.template_reason_textbox.delete("0.0", "end")
        self.template_evidence_textbox.delete("0.0", "end")
        self.template_check1_var.set(False)
        self.template_check2_var.set(False)
        self.template_check3_var.set(False)
        self.template_report_reason_var.set("불법 사진 및 동영상")
        self.template_victim_name_entry.delete(0, "end")
        self.template_keyword_entry.delete(0, "end")
        self._update_template_checkboxes_visibility()

    def _save_applicant_info(self):
        """신청인 정보 저장"""
        self.config["applicant"] = {
            "country": "south_korea",
            "full_name": self.settings_entries["full_name"].get(),
            "email": self.settings_entries["email"].get(),
            "company": self.settings_entries["company"].get(),
            "organization": self.settings_entries["organization"].get(),
        }
        self._save_config()
        self._show_toast("신청인 정보가 저장되었습니다", "success")

    # ==================== 검색 기능 ====================
    def _log(self, message: str, level: str = "info"):
        """로그 추가"""
        if not hasattr(self, 'log_textbox'):
            print(f"[{level.upper()}] {message}")
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{timestamp}] ", "time")
        self.log_textbox.insert("end", f"{message}\n", level)
        self.log_textbox.see("end")

    def _on_search(self):
        """검색 시작"""
        api_key = self.api_entry.get().strip()
        if not api_key:
            self._show_toast("API 키를 입력해주세요", "error")
            return

        # API 키 저장
        self.config["api_key"] = api_key
        self._save_config()

        text = self.domain_textbox.get("0.0", "end").strip()
        domains = [d.strip().replace("https://", "").replace("http://", "").rstrip("/")
                   for d in text.split("\n") if d.strip()]

        if not domains:
            self._show_toast("도메인을 입력해주세요", "error")
            return

        self.search_btn.configure(state="disabled", text="수집 중...")
        self.result_textbox.delete("0.0", "end")
        self.results = {}

        search_mode = self.search_mode_var.get()
        thread = threading.Thread(target=self._do_search, args=(api_key, domains, search_mode))
        thread.daemon = True
        thread.start()

    def _do_search(self, api_key: str, domains: list[str], search_mode: str):
        """검색 실행 (백그라운드)"""
        total = 0

        for i, domain in enumerate(domains, 1):
            self.after(0, lambda d=domain: self._log(f"도메인 검색 시작: {d}", "info"))

            try:
                if search_mode == "seo":
                    searcher = BrandSearcher(api_key)
                    self.after(0, lambda: self._log("브랜드명 추출 중...", "info"))
                    raw = searcher.search_domain(domain, num_results=100)
                    self.after(0, lambda r=len(raw): self._log(f"검색 결과: {r}개 URL", "info"))

                    try:
                        self.after(0, lambda: self._log("AI 필터링 중 (Groq)...", "accent"))
                        results = filter_urls_with_ai(raw)
                        self.after(0, lambda r=len(results): self._log(f"AI 필터 완료: {r}개 SEO 페이지", "success"))
                    except Exception as e:
                        self.after(0, lambda e=str(e): self._log(f"AI 필터 실패: {e}", "warning"))
                        results = filter_brand_results(raw, target_domain=domain, min_score=50, max_results=100)
                else:
                    client = SerperClient(api_key)
                    raw = client.site_search(domain, num_results=100)
                    self.after(0, lambda r=len(raw): self._log(f"검색 결과: {r}개 URL", "info"))
                    results = filter_urls(raw, strict=False, max_per_domain=100)

                total += len(results)
                self.after(0, lambda d=domain, r=results, mode=search_mode: self._append_result(d, r, mode=mode))
            except Exception as e:
                self.after(0, lambda d=domain, e=str(e): self._log(f"오류: {e}", "error"))

        self.after(0, lambda t=total: self._search_complete(t))

    def _search_complete(self, total: int):
        """검색 완료"""
        self.search_btn.configure(state="normal", text="수집 시작")
        self.result_count.configure(text=f"{total}개")
        self._log(f"검색 완료 - 총 {total}개 URL 수집", "success")
        self._show_toast(f"수집 완료: {total}개 URL", "success")

    def _append_result(self, domain: str, urls: list[dict], error: Optional[str] = None, mode: str = "seo"):
        """결과 추가"""
        if error:
            self.result_textbox.insert("end", f"\n━━━ {domain} ━━━ 오류: {error}\n")
        else:
            self.results[domain] = urls
            self.result_textbox.insert("end", f"\n━━━ {domain} ({len(urls)}개) ━━━\n")
            for item in urls:
                if mode == "seo":
                    score = calculate_seo_score(item.get("url", ""), item.get("title", ""), item.get("snippet", ""))
                else:
                    score = calculate_score(item.get("url", ""), item.get("title", ""), item.get("snippet", ""))
                decoded_url = decode_url(item['url'])
                self.result_textbox.insert("end", f"[{score:3d}] {decoded_url}\n")

    def _on_copy(self):
        """결과 복사"""
        urls = []
        for domain_urls in self.results.values():
            for item in domain_urls:
                urls.append(decode_url(item.get("url", "")))
        if urls:
            self.clipboard_clear()
            self.clipboard_append("\n".join(urls))
            self._show_toast(f"{len(urls)}개 URL이 복사되었습니다", "success")
        else:
            self._show_toast("복사할 URL이 없습니다", "warning")

    def _on_save(self):
        """결과 저장"""
        if not self.results:
            self._show_toast("저장할 결과가 없습니다", "warning")
            return

        from tkinter import filedialog
        folder = filedialog.askdirectory(title="저장할 폴더 선택")
        if not folder:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        saved_count = 0

        for domain, urls in self.results.items():
            if not urls:
                continue

            safe_domain = domain.replace(".", "_").replace("/", "_")
            filename = f"{safe_domain}_{timestamp}.txt"
            filepath = os.path.join(folder, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                for item in urls:
                    f.write(f"{decode_url(item['url'])}\n")

            saved_count += 1

        self._show_toast(f"{saved_count}개 파일이 저장되었습니다", "success")


def main():
    app = URLCollectorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
