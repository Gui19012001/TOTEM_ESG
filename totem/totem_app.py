"""
Totem ESG — App Kivy (APK Android)
Visual aprimorado: sem emojis, ícones em texto, welcome screen completa.
"""

import os
import json
from datetime import datetime

import kivy
kivy.require("2.3.0")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, ListProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse
from kivy.network.urlrequest import UrlRequest
from kivy.utils import get_color_from_hex

# ── Configuração ──────────────────────────────────────────────
API_URL   = os.environ.get("API_URL", "https://totem-esg.up.railway.app")
TABLET_ID = os.environ.get("TABLET_ID", "totem-01")

# ── Paleta de cores ───────────────────────────────────────────
C_GREEN       = get_color_from_hex("#1D9E75")
C_GREEN_DARK  = get_color_from_hex("#0F6E56")
C_GREEN_LIGHT = get_color_from_hex("#DCF5EC")
C_GREEN_MID   = get_color_from_hex("#5DCAA5")
C_WHITE       = get_color_from_hex("#FFFFFF")
C_BG          = get_color_from_hex("#F0F4F2")
C_SIDEBAR     = get_color_from_hex("#FFFFFF")
C_DARK        = get_color_from_hex("#1A2E28")
C_GRAY        = get_color_from_hex("#5A6A64")
C_GRAY_LIGHT  = get_color_from_hex("#E8EFEC")
C_BORDER      = get_color_from_hex("#D0DDD8")
C_AMBER       = get_color_from_hex("#F59E0B")
C_AMBER_LIGHT = get_color_from_hex("#FEF3C7")

TOPICS = {
    "ambiental": {"label": "Ambiental",  "icon": "AMB", "color": C_GREEN,
                  "questions": ["Qual e a meta de reducao de CO2?",
                                "Como esta o consumo de agua?",
                                "Quanto residuo reciclamos?"]},
    "seguranca": {"label": "Seguranca",  "icon": "SST", "color": C_AMBER,
                  "questions": ["Quantos dias sem acidentes?",
                                "Quais EPIs devo usar?",
                                "O que fazer em emergencia?"]},
    "social":    {"label": "Social",     "icon": "SOC", "color": get_color_from_hex("#3B82F6"),
                  "questions": ["Quais programas sociais temos?",
                                "Como participar de treinamentos?",
                                "Quais sao as metas sociais?"]},
    "politicas": {"label": "Politicas",  "icon": "POL", "color": get_color_from_hex("#8B5CF6"),
                  "questions": ["Quais sao nossas certificacoes?",
                                "O que diz a politica ambiental?",
                                "Como reportar um problema?"]},
}

# ── Helpers de canvas ─────────────────────────────────────────
def draw_rect(widget, color, radius=0):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*color)
        if radius:
            RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
        else:
            Rectangle(pos=widget.pos, size=widget.size)

def bind_bg(widget, color, radius=0):
    widget.bind(pos=lambda w, v: draw_rect(w, color, radius),
                size=lambda w, v: draw_rect(w, color, radius))
    draw_rect(widget, color, radius)

# ── Widget: Botão arredondado ─────────────────────────────────
class RndBtn(Button):
    def __init__(self, bg=None, fg=None, r=10, **kw):
        super().__init__(**kw)
        self._bg = bg or C_GREEN
        self._fg = fg or C_WHITE
        self._r  = r
        self.background_color = (0, 0, 0, 0)
        self.color = self._fg
        self.bold  = True
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self._r)])

    def set_bg(self, color):
        self._bg = color
        self._draw()

# ── Widget: Bolha de mensagem ─────────────────────────────────
class MsgBubble(BoxLayout):
    def __init__(self, text, is_user=False, **kw):
        super().__init__(orientation="vertical",
                         size_hint_y=None, padding=[dp(4), dp(2)], **kw)
        self.is_user = is_user

        row = BoxLayout(size_hint_y=None, spacing=dp(8))

        # Avatar
        av = Label(
            text="OP" if is_user else "ESG",
            font_size=sp(11), bold=True,
            color=C_WHITE if not is_user else C_GRAY,
            size_hint=(None, None), size=(dp(36), dp(36)),
        )
        with av.canvas.before:
            Color(*(C_GREEN if not is_user else C_GRAY_LIGHT))
            Ellipse(pos=av.pos, size=av.size)
        av.bind(pos=lambda w, v: self._redraw_av(w, is_user),
                size=lambda w, v: self._redraw_av(w, is_user))

        # Bolha de texto
        bubble_color = C_GREEN if is_user else C_WHITE
        text_color   = C_WHITE if is_user else C_DARK

        lbl = Label(
            text=text,
            font_size=sp(15),
            color=text_color,
            halign="left",
            valign="top",
            text_size=(Window.width * 0.60, None),
            markup=True,
        )
        lbl.bind(texture_size=lbl.setter("size"))

        bubble = BoxLayout(
            size_hint=(None, None),
            padding=[dp(14), dp(10)],
        )
        lbl.bind(size=lambda w, v: self._update_bubble(bubble, w, is_user))
        bubble.add_widget(lbl)

        with bubble.canvas.before:
            Color(*bubble_color)
            self._b_rect = RoundedRectangle(
                pos=bubble.pos, size=bubble.size,
                radius=[dp(4), dp(14), dp(14), dp(14)] if not is_user
                       else [dp(14), dp(4), dp(14), dp(14)]
            )
        bubble.bind(pos=lambda w, v: setattr(self._b_rect, "pos", v),
                    size=lambda w, v: setattr(self._b_rect, "size", v))

        if is_user:
            row.add_widget(Widget())
            row.add_widget(bubble)
            row.add_widget(av)
        else:
            row.add_widget(av)
            row.add_widget(bubble)
            row.add_widget(Widget())

        row.bind(minimum_height=row.setter("height"))
        row.size_hint_y = None
        self.add_widget(row)
        self.bind(minimum_height=self.setter("height"))
        self._row = row

    def _redraw_av(self, w, is_user):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*(C_GREEN if not is_user else C_GRAY_LIGHT))
            Ellipse(pos=w.pos, size=w.size)

    def _update_bubble(self, bubble, lbl, is_user):
        bubble.width  = lbl.width  + dp(28)
        bubble.height = lbl.height + dp(20)
        self._row.height = bubble.height + dp(8)
        self.height = self._row.height + dp(4)


# ── Tela principal ────────────────────────────────────────────
class TotemLayout(BoxLayout):
    topic      = StringProperty("ambiental")
    is_loading = BooleanProperty(False)
    history    = ListProperty([])
    quick_list = ListProperty([])

    def __init__(self, **kw):
        super().__init__(orientation="horizontal", **kw)
        self._build()
        self._load_quick_questions()

    # ─ Build ─────────────────────────────────────────────────
    def _build(self):
        # SIDEBAR
        sidebar = BoxLayout(
            orientation="vertical",
            size_hint_x=None, width=dp(190),
            padding=[dp(12), dp(16)], spacing=dp(6),
        )
        bind_bg(sidebar, C_SIDEBAR)

        # Logo header
        logo_row = BoxLayout(size_hint_y=None, height=dp(56),
                             spacing=dp(10), padding=[dp(4), 0])
        logo_box = BoxLayout(size_hint=(None, None), size=(dp(40), dp(40)))
        with logo_box.canvas:
            Color(*C_GREEN)
            RoundedRectangle(pos=logo_box.pos, size=logo_box.size, radius=[dp(10)])
        logo_box.bind(pos=lambda w, v: self._redraw_logo(w),
                      size=lambda w, v: self._redraw_logo(w))
        logo_lbl = Label(text="ESG", font_size=sp(13), bold=True, color=C_WHITE,
                         size_hint=(None, None), size=(dp(40), dp(40)))
        logo_box.add_widget(logo_lbl)

        name_col = BoxLayout(orientation="vertical", spacing=dp(2))
        name_col.add_widget(Label(text="Totem ESG", font_size=sp(14), bold=True,
                                  color=C_DARK, halign="left", size_hint_y=None, height=dp(22)))
        name_col.add_widget(Label(text="Fabrica", font_size=sp(11),
                                  color=C_GRAY, halign="left", size_hint_y=None, height=dp(18)))
        logo_row.add_widget(logo_box)
        logo_row.add_widget(name_col)
        sidebar.add_widget(logo_row)

        # Divisor
        div = Widget(size_hint_y=None, height=dp(1))
        bind_bg(div, C_BORDER)
        sidebar.add_widget(div)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(8)))

        # Label temas
        sidebar.add_widget(Label(
            text="TEMAS", font_size=sp(10), bold=True,
            color=C_GRAY, halign="left",
            size_hint_y=None, height=dp(24),
        ))

        # Botões de tema
        self.topic_btns = {}
        for key, meta in TOPICS.items():
            btn = self._make_topic_btn(key, meta)
            sidebar.add_widget(btn)
            self.topic_btns[key] = btn

        sidebar.add_widget(Widget())  # spacer

        # Botão nova conversa
        new_btn = RndBtn(
            text="+ Nova Conversa",
            bg=C_GRAY_LIGHT, fg=C_GRAY,
            font_size=sp(13),
            size_hint_y=None, height=dp(44), r=10,
        )
        new_btn.bind(on_press=self.clear_chat)
        sidebar.add_widget(new_btn)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(8)))

        self.add_widget(sidebar)

        # ÁREA DE CHAT
        right = BoxLayout(orientation="vertical")

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(52),
                           padding=[dp(20), 0], spacing=dp(10))
        bind_bg(header, C_WHITE)

        self.header_title = Label(
            text="[b]Agente ESG[/b]  —  Ambiental",
            markup=True, font_size=sp(16),
            color=C_DARK, halign="left",
        )
        header.add_widget(self.header_title)

        # Status dot
        self.status_lbl = Label(
            text="● Online",
            font_size=sp(12), color=C_GREEN,
            size_hint_x=None, width=dp(80), halign="right",
        )
        header.add_widget(self.status_lbl)
        right.add_widget(header)

        # Linha verde
        line = Widget(size_hint_y=None, height=dp(3))
        bind_bg(line, C_GREEN)
        right.add_widget(line)

        # Scroll chat
        self.scroll = ScrollView(do_scroll_x=False)
        self.msg_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(16), dp(16)],
        )
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        self.scroll.add_widget(self.msg_box)
        right.add_widget(self.scroll)

        # Barra de input
        input_bar = BoxLayout(
            size_hint_y=None, height=dp(68),
            padding=[dp(14), dp(10)], spacing=dp(10),
        )
        bind_bg(input_bar, C_WHITE)

        self.txt_input = TextInput(
            hint_text="Digite sua pergunta aqui...",
            font_size=sp(15),
            multiline=False,
            background_color=C_BG,
            foreground_color=C_DARK,
            cursor_color=C_GREEN,
            hint_text_color=C_GRAY,
            padding=[dp(14), dp(12)],
        )
        self.txt_input.bind(on_text_validate=self.send_msg)

        self.send_btn = RndBtn(
            text=">",
            font_size=sp(20), bold=True,
            size_hint_x=None, width=dp(50), r=12,
        )
        self.send_btn.bind(on_press=self.send_msg)

        input_bar.add_widget(self.txt_input)
        input_bar.add_widget(self.send_btn)
        right.add_widget(input_bar)

        self.add_widget(right)
        self._show_welcome()

    def _redraw_logo(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_GREEN)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])

    def _make_topic_btn(self, key, meta):
        is_active = (key == "ambiental")
        bg = C_GREEN_LIGHT if is_active else C_BG
        fg = C_GREEN_DARK  if is_active else C_DARK

        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(50),
            spacing=dp(10), padding=[dp(8), dp(6)],
        )
        bind_bg(row, bg, radius=10)

        # Ícone badge
        badge = Label(
            text=meta["icon"],
            font_size=sp(10), bold=True,
            color=C_WHITE if is_active else C_GRAY,
            size_hint=(None, None), size=(dp(32), dp(32)),
        )
        badge_color = meta["color"] if is_active else C_GRAY_LIGHT
        with badge.canvas.before:
            Color(*badge_color)
            RoundedRectangle(pos=badge.pos, size=badge.size, radius=[dp(8)])
        badge.bind(
            pos=lambda w, v, c=badge_color: self._redraw_badge(w, c),
            size=lambda w, v, c=badge_color: self._redraw_badge(w, c),
        )

        lbl = Label(
            text=meta["label"],
            font_size=sp(14), bold=is_active,
            color=fg, halign="left",
        )

        row.add_widget(badge)
        row.add_widget(lbl)
        row._badge = badge
        row._lbl   = lbl
        row._key   = key

        # Touch handler
        row.bind(on_touch_down=lambda w, t: self._topic_touch(w, t, key))
        return row

    def _redraw_badge(self, w, color):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*color)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(8)])

    def _topic_touch(self, row, touch, key):
        if row.collide_point(*touch.pos):
            self.set_topic(key)

    # ─ Tópicos ────────────────────────────────────────────────
    def set_topic(self, key):
        self.topic = key
        meta = TOPICS[key]
        self.header_title.text = f"[b]Agente ESG[/b]  —  {meta['label']}"

        for k, row in self.topic_btns.items():
            is_active = (k == key)
            bg = C_GREEN_LIGHT if is_active else C_BG
            fg = C_GREEN_DARK  if is_active else C_DARK
            bind_bg(row, bg, radius=10)
            row._lbl.color = fg
            row._lbl.bold  = is_active
            badge_color = TOPICS[k]["color"] if is_active else C_GRAY_LIGHT
            self._redraw_badge(row._badge, badge_color)
            row._badge.color = C_WHITE if is_active else C_GRAY

        self._load_quick_questions()

    # ─ Welcome ────────────────────────────────────────────────
    def _show_welcome(self):
        self.msg_box.clear_widgets()
        self.history.clear()

        wrap = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(16),
            padding=[dp(20), dp(20)],
        )

        # Card de boas-vindas
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(24), dp(20)],
            spacing=dp(12),
        )
        bind_bg(card, C_WHITE, radius=16)

        # Ícone grande
        icon_wrap = BoxLayout(size_hint_y=None, height=dp(72))
        icon_box  = BoxLayout(size_hint=(None, None), size=(dp(72), dp(72)))
        with icon_box.canvas:
            Color(*C_GREEN_LIGHT)
            RoundedRectangle(pos=icon_box.pos, size=icon_box.size, radius=[dp(18)])
        icon_box.bind(pos=lambda w, v: self._redraw_icon(w),
                      size=lambda w, v: self._redraw_icon(w))
        icon_lbl = Label(text="ESG", font_size=sp(22), bold=True, color=C_GREEN,
                         size_hint=(None, None), size=(dp(72), dp(72)))
        icon_box.add_widget(icon_lbl)
        icon_wrap.add_widget(Widget())
        icon_wrap.add_widget(icon_box)
        icon_wrap.add_widget(Widget())
        card.add_widget(icon_wrap)

        card.add_widget(Label(
            text="[b]Ola! Sou o Agente ESG[/b]",
            markup=True, font_size=sp(20),
            color=C_DARK, size_hint_y=None, height=dp(34),
            halign="center",
        ))
        card.add_widget(Label(
            text="Tire suas duvidas sobre sustentabilidade,\nseguranca do trabalho, metas e politicas da empresa.",
            font_size=sp(14), color=C_GRAY,
            size_hint_y=None, height=dp(50),
            halign="center",
        ))

        card.bind(minimum_height=card.setter("height"))
        wrap.add_widget(card)

        # Grid de perguntas rápidas
        self.quick_grid = GridLayout(
            cols=2,
            size_hint_y=None,
            spacing=dp(8),
        )
        self.quick_grid.bind(minimum_height=self.quick_grid.setter("height"))
        wrap.add_widget(self.quick_grid)

        wrap.bind(minimum_height=wrap.setter("height"))
        self.msg_box.add_widget(wrap)
        self._welcome_wrap = wrap
        self._render_quick_btns()

    def _redraw_icon(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_GREEN_LIGHT)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(18)])

    def _render_quick_btns(self):
        self.quick_grid.clear_widgets()
        questions = self.quick_list if self.quick_list else TOPICS[self.topic]["questions"]
        for q in questions[:6]:
            text = q["question"] if isinstance(q, dict) else q
            btn = RndBtn(
                text=text,
                bg=C_WHITE, fg=C_DARK,
                font_size=sp(13),
                size_hint_y=None, height=dp(52),
                r=10, bold=False,
            )
            # Borda verde sutil
            with btn.canvas.after:
                Color(*C_BORDER)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(10)])
            btn.bind(on_press=lambda b, q=text: self._prefill(q))
            self.quick_grid.add_widget(btn)

    def _prefill(self, q):
        self.txt_input.text = q
        self.send_msg()

    # ─ Chat ───────────────────────────────────────────────────
    def send_msg(self, *_):
        text = self.txt_input.text.strip()
        if not text or self.is_loading:
            return

        # Remove welcome
        if hasattr(self, "_welcome_wrap") and self._welcome_wrap.parent:
            self.msg_box.remove_widget(self._welcome_wrap)

        self.txt_input.text = ""
        self.is_loading = True
        self.send_btn.disabled = True

        self._add_bubble(text, is_user=True)
        self._typing = self._add_typing()
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
                lambda dt: self._on_answer(res), 0),
            on_failure=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_error(), 0),
            on_error=lambda req, err: Clock.schedule_once(
                lambda dt: self._on_error(), 0),
            timeout=30,
        )

    def _on_answer(self, res):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        answer = res.get("answer", "Nao consegui processar. Tente novamente.")
        self._add_bubble(answer, is_user=False)
        self.history.append({"role": "assistant", "content": answer})
        self.is_loading = False
        self.send_btn.disabled = False
        self.status_lbl.text  = "● Online"
        self.status_lbl.color = C_GREEN
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.15)

    def _on_error(self):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        self._add_bubble(
            "Erro de conexao com o servidor.\nVerifique a rede e tente novamente.",
            is_user=False,
        )
        self.is_loading = False
        self.send_btn.disabled = False
        self.status_lbl.text  = "● Offline"
        self.status_lbl.color = get_color_from_hex("#EF4444")
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.15)

    def _add_bubble(self, text, is_user):
        b = MsgBubble(text=text, is_user=is_user)
        self.msg_box.add_widget(b)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return b

    def _add_typing(self):
        lbl = Label(
            text="[i]Agente digitando...[/i]",
            markup=True, font_size=sp(14),
            color=C_GRAY,
            size_hint_y=None, height=dp(36),
            halign="left",
        )
        self.msg_box.add_widget(lbl)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return lbl

    def _scroll_end(self):
        self.scroll.scroll_y = 0

    def clear_chat(self, *_):
        self._show_welcome()
        self.history.clear()
        self.is_loading = False
        self.send_btn.disabled = False
        self.status_lbl.text  = "● Online"
        self.status_lbl.color = C_GREEN

    # ─ Quick questions via API ────────────────────────────────
    def _load_quick_questions(self):
        UrlRequest(
            f"{API_URL}/api/quick-questions?topic={self.topic}",
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._set_quick(res), 0),
            on_failure=lambda req, res: None,
            on_error=lambda req, err: None,
            timeout=5,
        )

    def _set_quick(self, data):
        if data:
            self.quick_list = data
            if hasattr(self, "quick_grid"):
                self._render_quick_btns()


# ── App ───────────────────────────────────────────────────────
class TotemESGApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex("#F0F4F2")
        return TotemLayout()


if __name__ == "__main__":
    TotemESGApp().run()
