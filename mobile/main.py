"""
KIS 자동매매 - Android 모바일 앱
지문인식 로그인 + WebView
"""
import json
import os
from pathlib import Path

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.network.urlrequest import UrlRequest
from kivy.utils import platform

# ──────────────── 설정 ────────────────
SERVER_URL = "https://pois2000.duckdns.org:6001"
CRED_FILE = "kis_credentials.json"

# ──────────────── KV 레이아웃 ────────────────
KV = """
#:import Window kivy.core.window.Window

<LoginScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: 0.102, 0.102, 0.18, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Widget:
            size_hint_y: 0.15

        Label:
            text: 'KIS 자동매매'
            font_size: sp(28)
            bold: True
            size_hint_y: None
            height: dp(40)

        Label:
            text: '계정에 로그인하세요'
            font_size: sp(14)
            color: 0.7, 0.7, 0.7, 1
            size_hint_y: None
            height: dp(30)

        Widget:
            size_hint_y: 0.05

        # 지문인식 버튼
        Button:
            id: biometric_btn
            text: '  지문인식 로그인'
            font_size: sp(16)
            bold: True
            size_hint_y: None
            height: dp(55)
            background_color: 0.07, 0.6, 0.55, 1
            on_press: root.biometric_login()
            opacity: 0

        # 자동 로그인 버튼
        Button:
            id: auto_btn
            text: '  자동 로그인'
            font_size: sp(16)
            bold: True
            size_hint_y: None
            height: dp(55)
            background_color: 0.4, 0.49, 0.92, 1
            on_press: root.auto_login()
            opacity: 0

        Widget:
            size_hint_y: 0.03

        Label:
            text: '아이디'
            font_size: sp(13)
            bold: True
            size_hint_y: None
            height: dp(25)
            halign: 'left'
            text_size: self.size

        TextInput:
            id: username
            hint_text: '아이디 입력'
            multiline: False
            size_hint_y: None
            height: dp(45)
            font_size: sp(15)
            padding: [dp(10), dp(12)]

        Label:
            text: '비밀번호'
            font_size: sp(13)
            bold: True
            size_hint_y: None
            height: dp(25)
            halign: 'left'
            text_size: self.size

        TextInput:
            id: password
            hint_text: '비밀번호 입력'
            password: True
            multiline: False
            size_hint_y: None
            height: dp(45)
            font_size: sp(15)
            padding: [dp(10), dp(12)]

        CheckBox:
            id: remember
            active: True
            size_hint: None, None
            size: dp(30), dp(30)
            pos_hint: {'x': 0}

        Label:
            text: '다음에 자동 로그인 / 지문인식 사용'
            font_size: sp(12)
            size_hint_y: None
            height: dp(30)
            halign: 'left'
            text_size: self.size

        Button:
            text: '로그인'
            font_size: sp(16)
            bold: True
            size_hint_y: None
            height: dp(50)
            background_color: 0.42, 0.39, 1, 1
            on_press: root.manual_login()

        Label:
            id: status_label
            text: ''
            font_size: sp(12)
            color: 1, 0.3, 0.3, 1
            size_hint_y: None
            height: dp(30)

        Widget:
            size_hint_y: 0.2


<WebViewScreen>:
    BoxLayout:
        orientation: 'vertical'

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            padding: dp(10)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 0.102, 0.102, 0.18, 1
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                text: 'KIS 자동매매'
                font_size: sp(16)
                bold: True
                halign: 'left'
                text_size: self.size
                valign: 'center'

            Button:
                text: '새로고침'
                size_hint_x: None
                width: dp(80)
                font_size: sp(12)
                on_press: root.reload()

            Button:
                text: '로그아웃'
                size_hint_x: None
                width: dp(80)
                font_size: sp(12)
                background_color: 0.9, 0.3, 0.3, 1
                on_press: root.logout()

        Widget:
            id: webview_container
"""


def get_cred_path():
    if platform == "android":
        from android.storage import app_storage_path
        return os.path.join(app_storage_path(), CRED_FILE)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CRED_FILE)


def save_credentials(username, password, token):
    import base64
    data = {
        "u": username,
        "p": base64.b64encode(password.encode()).decode(),
        "token": token,
    }
    with open(get_cred_path(), "w") as f:
        json.dump(data, f)


def load_credentials():
    path = get_cred_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def clear_credentials():
    path = get_cred_path()
    if os.path.exists(path):
        os.remove(path)


class LoginScreen(Screen):

    def on_enter(self):
        cred = load_credentials()
        if cred:
            self.ids.auto_btn.opacity = 1
            self.ids.auto_btn.disabled = False
            # 지문인식 가능 여부 체크
            if platform == "android":
                self.ids.biometric_btn.opacity = 1
                self.ids.biometric_btn.disabled = False

    def manual_login(self):
        username = self.ids.username.text.strip()
        password = self.ids.password.text
        if not username or not password:
            self.ids.status_label.text = "아이디와 비밀번호를 입력해주세요."
            return
        self.ids.status_label.text = "로그인 중..."
        self.ids.status_label.color = (0.7, 0.7, 0.7, 1)
        self._do_login(username, password)

    def auto_login(self):
        import base64
        cred = load_credentials()
        if not cred:
            self.ids.status_label.text = "저장된 로그인 정보가 없습니다."
            return
        username = cred["u"]
        password = base64.b64decode(cred["p"]).decode()
        self.ids.status_label.text = "자동 로그인 중..."
        self.ids.status_label.color = (0.7, 0.7, 0.7, 1)
        self._do_login(username, password)

    def biometric_login(self):
        if platform == "android":
            self._android_biometric()
        else:
            self.auto_login()

    def _android_biometric(self):
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            BiometricPrompt = autoclass("androidx.biometric.BiometricPrompt")
            PromptInfo = autoclass("androidx.biometric.BiometricPrompt$PromptInfo")
            BiometricManager = autoclass("androidx.biometric.BiometricManager")
            Fragment = autoclass("androidx.fragment.app.FragmentActivity")
            Executor = autoclass("java.util.concurrent.Executors")

            activity = PythonActivity.mActivity
            manager = BiometricManager.from_(activity)
            can_auth = manager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)

            if can_auth != BiometricManager.BIOMETRIC_SUCCESS:
                self.ids.status_label.text = "지문인식을 사용할 수 없습니다."
                self.ids.status_label.color = (1, 0.3, 0.3, 1)
                return

            executor = Executor.newSingleThreadExecutor()

            class AuthCallback(BiometricPrompt.AuthenticationCallback):
                def onAuthenticationSucceeded(self_cb, result):
                    Clock.schedule_once(lambda dt: self.auto_login(), 0)

                def onAuthenticationFailed(self_cb):
                    Clock.schedule_once(
                        lambda dt: setattr(self.ids.status_label, "text", "지문 인식 실패"), 0
                    )

                def onAuthenticationError(self_cb, errorCode, errString):
                    Clock.schedule_once(
                        lambda dt: setattr(self.ids.status_label, "text", str(errString)), 0
                    )

            callback = AuthCallback()
            prompt = BiometricPrompt(activity, executor, callback)

            info = (
                PromptInfo.Builder()
                .setTitle("KIS 자동매매")
                .setSubtitle("지문을 인식해주세요")
                .setNegativeButtonText("취소")
                .build()
            )

            def show_prompt(dt):
                prompt.authenticate(info)

            Clock.schedule_once(show_prompt, 0.1)

        except Exception as e:
            self.ids.status_label.text = f"지문인식 오류: {str(e)[:50]}"
            self.ids.status_label.color = (1, 0.3, 0.3, 1)
            self.auto_login()

    def _do_login(self, username, password):
        import ssl
        import certifi

        def on_success(req, result):
            if result.get("success"):
                token = result["token"]
                if self.ids.remember.active:
                    save_credentials(username, password, token)
                app = App.get_running_app()
                app.auth_token = token
                app.root.current = "webview"
            else:
                self.ids.status_label.text = result.get("msg", "로그인 실패")
                self.ids.status_label.color = (1, 0.3, 0.3, 1)

        def on_error(req, error):
            self.ids.status_label.text = f"서버 연결 실패: {str(error)[:40]}"
            self.ids.status_label.color = (1, 0.3, 0.3, 1)

        def on_failure(req, result):
            self.ids.status_label.text = "아이디 또는 비밀번호가 올바르지 않습니다."
            self.ids.status_label.color = (1, 0.3, 0.3, 1)

        body = json.dumps({"username": username, "password": password})
        UrlRequest(
            f"{SERVER_URL}/api/auth/token",
            req_body=body,
            req_headers={"Content-Type": "application/json"},
            on_success=on_success,
            on_error=on_error,
            on_failure=on_failure,
            verify=False,
        )


class WebViewScreen(Screen):

    def on_enter(self):
        if platform == "android":
            self._load_android_webview()
        else:
            from kivy.uix.label import Label
            self.ids.webview_container.clear_widgets()
            lbl = Label(text=f"WebView는 Android에서만 사용 가능합니다.\n서버: {SERVER_URL}")
            self.ids.webview_container.add_widget(lbl)

    def _load_android_webview(self):
        try:
            from jnius import autoclass, cast
            from android.runnable import run_on_ui_thread

            WebView = autoclass("android.webkit.WebView")
            WebViewClient = autoclass("android.webkit.WebViewClient")
            WebSettings = autoclass("android.webkit.WebSettings")
            CookieManager = autoclass("android.webkit.CookieManager")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            activity = PythonActivity.mActivity
            app = App.get_running_app()
            token = app.auth_token

            @run_on_ui_thread
            def create_webview():
                webview = WebView(activity)
                settings = webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                settings.setBuiltInZoomControls(True)
                settings.setDisplayZoomControls(False)
                settings.setUseWideViewPort(True)
                settings.setLoadWithOverviewMode(True)

                # 쿠키 허용
                cm = CookieManager.getInstance()
                cm.setAcceptCookie(True)
                cm.setAcceptThirdPartyCookies(webview, True)

                webview.setWebViewClient(WebViewClient())

                # 토큰으로 세션 로그인 후 메인 페이지 로드
                js_login = f"""
                    fetch('{SERVER_URL}/api/auth/mobile-login', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{token: '{token}'}}),
                        credentials: 'include'
                    }}).then(function() {{
                        window.location.href = '{SERVER_URL}/';
                    }});
                """
                # 먼저 빈 페이지 로드 후 JS 실행
                webview.loadUrl(SERVER_URL + "/login")
                Clock.schedule_once(
                    lambda dt: webview.evaluateJavascript(js_login, None), 2
                )

                activity.setContentView(webview)

            create_webview()

        except Exception as e:
            from kivy.uix.label import Label
            self.ids.webview_container.clear_widgets()
            self.ids.webview_container.add_widget(
                Label(text=f"WebView 로드 실패:\n{str(e)}")
            )

    def reload(self):
        if platform == "android":
            self._load_android_webview()

    def logout(self):
        clear_credentials()
        app = App.get_running_app()
        app.auth_token = None
        self.manager.current = "login"


class KISTraderApp(App):
    auth_token = None

    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(WebViewScreen(name="webview"))
        return sm


if __name__ == "__main__":
    KISTraderApp().run()
