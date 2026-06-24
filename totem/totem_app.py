"""
Totem ESG — App Kivy (APK Android)
Interface do operador: chat com agente ESG via FastAPI backend.
Build: buildozer android debug  (ou via GitHub Actions)
"""

import os
import json
import threading
from datetime import datetime

import kivy
kivy.require("2.3.0")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, ListProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.network.urlrequest import UrlRequest
from kivy.utils import get_color_from_hex

# ── Constantes ────────────────────────────────────────────────
# Em produção: troque para a URL do Railway
API_URL   = os.environ.get("API_URL", "https://totem-esg.up.railway.app")
TABLET_ID = os.environ.get("TABLET_ID", "totem-01")

GREEN       = get_color_from_hex("#1D9E75")
GREEN_DARK  = get_color_from_hex("#0F6E56")
GREEN_LIGHT = get_color_from_hex("#E1F5EE")
WHITE       = get_color_from_hex("#FFFFFF")
GRAY_BG     = get_color_from_hex("#F0F4F2")
GRAY_TEXT   = get_color_from_hex("#5a6a64")
DARK        = get_color_from_hex("#1a1a1a")

TOPICS = {
    "ambiental": {"label": "Ambiental",   "icon": "🌿"},
    "seguranca": {"label": "Segurança",   "icon": "🦺"},
    "social":    {"label": "Social",      "icon": "👥"},
    "politicas": {"label": "Políticas",   "icon": "📋"},
}

# ── Widgets auxiliares ────────────────────────────────────────
class RoundedButton(Button):
    def __init__(self, bg_color=None, text_color=None, radius=12, **kwargs):
        super().__init__(**kwargs)
        self.bg_color   = bg_color or GREEN
        self.text_color = text_color or WHITE
        self.radius     = radius
        self.background_color = (0, 0, 0, 0)
        self.color = self.text_color
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[dp(self.radius)])

class BubbleLabel(BoxLayout):
    """Bolha de mensagem com fundo arredondado."""
    def __init__(self, text, is_user=False, **kwargs):
        super().__init__(orientation="vertical",
                         size_hint_y=None, **kwargs)
        self.is_user = is_user
        self.padding = [dp(8), dp(4)]

        lbl = Label(
            text=text,
            markup=True,
            halign="left",
            valign="top",
            text_size=(Window.width * 0.72, None),
            font_size=sp(15),
            color=WHITE if is_user else DARK,
        )
        lbl.bind(texture_size=lbl.setter("size"))
        lbl.bind(size=self._update_height)
        self.lbl = lbl

        inner = BoxLayout(
            size_hint_y=None,
            orientation="horizontal",
        )
        if is_user:
            inner.add_widget(Widget())
        inner.add_widget(lbl)
        if not is_user:
            inner.add_widget(Widget())

        self.add_widget(inner)
        self.inner = inner
        self.bind(pos=self._draw, size=self._draw)

    def _update_height(self, lbl, size):
        self.inner.height = size[1] + dp(20)
        self.height = self.inner.height + dp(8)
        self._draw()

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.is_user:
                Color(*GREEN)
            else:
                Color(*WHITE)
            RoundedRectangle(
                pos=(self.lbl.x - dp(12), self.lbl.y - dp(10)),
                size=(self.lbl.width + dp(24), self.lbl.height + dp(20)),
                radius=[dp(14), dp(4), dp(14), dp(14)] if self.is_user
                       else [dp(4), dp(14), dp(14), dp(14)],
            )


# ── Tela principal ────────────────────────────────────────────
class TotemLayout(BoxLayout):
    topic        = StringProperty("ambiental")
    is_loading   = BooleanProperty(False)
    quick_list   = ListProperty([])
    history      = ListProperty([])  # [{role, content}]

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)
        self._build_ui()
        self._load_quick_questions()

    # ─ Build UI ──────────────────────────────────────────────
    def _build_ui(self):
        # Sidebar
        sidebar = BoxLayout(
            orientation="vertical",
            size_hint_x=None, width=dp(180),
            padding=dp(12), spacing=dp(6),
        )
        with sidebar.canvas.before:
            Color(*WHITE)
            self.sidebar_rect = Rectangle(pos=sidebar.pos, size=sidebar.size)
        sidebar.bind(pos=lambda s, v: setattr(self.sidebar_rect, "pos", v),
                     size=lambda s, v: setattr(self.sidebar_rect, "size", v))

        hdr = Label(
            text="[b]Temas[/b]", markup=True,
            font_size=sp(11), color=GRAY_TEXT,
            size_hint_y=None, height=dp(28),
        )
        sidebar.add_widget(hdr)

        self.topic_btns = {}
        for key, meta in TOPICS.items():
            btn = RoundedButton(
                text=f"{meta['icon']}  {meta['label']}",
                bg_color=GREEN_LIGHT if key == "ambiental" else GRAY_BG,
                text_color=GREEN_DARK if key == "ambiental" else DARK,
                font_size=sp(13), size_hint_y=None, height=dp(52),
            )
            btn.bind(on_press=lambda b, k=key: self.set_topic(k))
            sidebar.add_widget(btn)
            self.topic_btns[key] = btn

        sidebar.add_widget(Widget())  # spacer

        clear_btn = RoundedButton(
            text="↺  Nova conversa",
            bg_color=GRAY_BG, text_color=GRAY_TEXT,
            font_size=sp(13), size_hint_y=None, height=dp(44),
        )
        clear_btn.bind(on_press=self.clear_chat)
        sidebar.add_widget(clear_btn)

        self.add_widget(sidebar)

        # Área direita (chat)
        right = BoxLayout(orientation="vertical")

        # Header
        header = BoxLayout(
            size_hint_y=None, height=dp(54),
            padding=[dp(16), 0],
        )
        with header.canvas.before:
            Color(*WHITE)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, v: self._redraw_rect(w),
                    size=lambda w, v: self._redraw_rect(w))

        title_lbl = Label(
            text="[b]Agente ESG[/b]", markup=True,
            font_size=sp(17), color=DARK, halign="left",
        )
        header.add_widget(title_lbl)
        right.add_widget(header)

        # Separador verde
        sep = Widget(size_hint_y=None, height=dp(3))
        with sep.canvas:
            Color(*GREEN)
            self.sep_rect = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, v: setattr(self.sep_rect, "pos", v),
                 size=lambda w, v: setattr(self.sep_rect, "size", v))
        right.add_widget(sep)

        # Área de mensagens
        self.scroll = ScrollView(do_scroll_x=False)
        self.msg_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None, spacing=dp(10),
            padding=[dp(16), dp(16)],
        )
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        self.scroll.add_widget(self.msg_box)
        right.add_widget(self.scroll)

        # Welcome
        self._show_welcome()

        # Barra de input
        input_bar = BoxLayout(
            size_hint_y=None, height=dp(70),
            padding=[dp(12), dp(10)],
            spacing=dp(10),
        )
        with input_bar.canvas.before:
            Color(*WHITE)
            Rectangle(pos=input_bar.pos, size=input_bar.size)

        self.text_input = TextInput(
            hint_text="Digite sua pergunta aqui...",
            font_size=sp(15),
            multiline=False,
            size_hint_x=1,
        )
        self.text_input.bind(on_text_validate=self.send_message)

        send_btn = RoundedButton(
            text="➤",
            font_size=sp(20),
            size_hint_x=None, width=dp(50),
        )
        send_btn.bind(on_press=self.send_message)
        self.send_btn = send_btn

        input_bar.add_widget(self.text_input)
        input_bar.add_widget(send_btn)
        right.add_widget(input_bar)

        self.add_widget(right)

    def _redraw_rect(self, widget):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*WHITE)
            Rectangle(pos=widget.pos, size=widget.size)

    # ─ Welcome + Quick questions ──────────────────────────────
    def _show_welcome(self):
        self.msg_box.clear_widgets()
        self.history.clear()

        welcome = BoxLayout(
            orientation="vertical",
            size_hint_y=None, height=dp(260),
            padding=dp(20), spacing=dp(12),
        )
        welcome.add_widget(Label(
            text="[b]Olá! Sou o Agente ESG[/b]", markup=True,
            font_size=sp(20), color=DARK, size_hint_y=None, height=dp(36),
        ))
        welcome.add_widget(Label(
            text="Tire suas dúvidas sobre sustentabilidade,\nsegurança, metas e políticas da empresa.",
            font_size=sp(14), color=GRAY_TEXT,
            size_hint_y=None, height=dp(48), halign="center",
        ))
        self.quick_grid = BoxLayout(
            orientation="vertical",
            size_hint_y=None, spacing=dp(8),
        )
        self.quick_grid.bind(minimum_height=self.quick_grid.setter("height"))
        welcome.add_widget(self.quick_grid)
        self.msg_box.add_widget(welcome)
        self._render_quick_buttons()

    def _render_quick_buttons(self):
        self.quick_grid.clear_widgets()
        for q in self.quick_list[:6]:
            btn = RoundedButton(
                text=q["question"],
                bg_color=WHITE,
                text_color=DARK,
                font_size=sp(13),
                size_hint_y=None, height=dp(44),
                radius=22,
            )
            btn.bind(on_press=lambda b, q=q["question"]: self._prefill(q))
            self.quick_grid.add_widget(btn)

    def _prefill(self, question):
        self.text_input.text = question
        self.send_message()

    # ─ Tópicos ────────────────────────────────────────────────
    def set_topic(self, topic):
        self.topic = topic
        for key, btn in self.topic_btns.items():
            if key == topic:
                btn.bg_color   = GREEN_LIGHT
                btn.text_color = GREEN_DARK
            else:
                btn.bg_color   = GRAY_BG
                btn.text_color = DARK
            btn._update()
        self._load_quick_questions()

    # ─ Chat ───────────────────────────────────────────────────
    def send_message(self, *_):
        text = self.text_input.text.strip()
        if not text or self.is_loading:
            return

        # Remove welcome se ainda visível
        if self.msg_box.children and hasattr(self.msg_box.children[-1], "quick_grid"):
            self.msg_box.clear_widgets()

        self.text_input.text = ""
        self.is_loading = True
        self.send_btn.disabled = True

        self._add_bubble(text, is_user=True)
        typing = self._add_typing()

        self.history.append({"role": "user", "content": text})

        payload = json.dumps({
            "question":  text,
            "topic":     self.topic,
            "tablet_id": TABLET_ID,
            "history":   list(self.history[-8:]),
        }).encode("utf-8")

        UrlRequest(
            f"{API_URL}/api/chat",
            req_body=payload,
            req_headers={"Content-Type": "application/json"},
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_answer(res, typing), 0),
            on_failure=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_error(typing), 0),
            on_error=lambda req, err: Clock.schedule_once(
                lambda dt: self._on_error(typing), 0),
        )

    def _on_answer(self, res, typing):
        self.msg_box.remove_widget(typing)
        answer = res.get("answer", "Não consegui processar. Tente novamente.")
        self._add_bubble(answer, is_user=False)
        self.history.append({"role": "assistant", "content": answer})
        self.is_loading = False
        self.send_btn.disabled = False
        Clock.schedule_once(lambda dt: self._scroll_bottom(), 0.1)

    def _on_error(self, typing):
        self.msg_box.remove_widget(typing)
        self._add_bubble("⚠️ Erro de conexão. Verifique a rede e tente novamente.", is_user=False)
        self.is_loading = False
        self.send_btn.disabled = False

    def _add_bubble(self, text, is_user):
        bubble = BubbleLabel(text=text, is_user=is_user)
        self.msg_box.add_widget(bubble)
        Clock.schedule_once(lambda dt: self._scroll_bottom(), 0.1)
        return bubble

    def _add_typing(self):
        lbl = Label(
            text="[i]Digitando...[/i]", markup=True,
            font_size=sp(14), color=GRAY_TEXT,
            size_hint_y=None, height=dp(36),
            halign="left",
        )
        self.msg_box.add_widget(lbl)
        return lbl

    def _scroll_bottom(self):
        self.scroll.scroll_y = 0

    def clear_chat(self, *_):
        self._show_welcome()
        self.is_loading = False
        self.send_btn.disabled = False

    # ─ Quick questions via API ────────────────────────────────
    def _load_quick_questions(self):
        UrlRequest(
            f"{API_URL}/api/quick-questions?topic={self.topic}",
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._set_quick(res), 0),
        )

    def _set_quick(self, data):
        self.quick_list = data or []
        if hasattr(self, "quick_grid"):
            self._render_quick_buttons()


# ── App ───────────────────────────────────────────────────────
class TotemESGApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex("#F0F4F2")
        # Simular tela de tablet em desktop
        if os.environ.get("KIVY_WINDOW"):
            Window.size = (1024, 768)
        return TotemLayout()


if __name__ == "__main__":
    TotemESGApp().run()
