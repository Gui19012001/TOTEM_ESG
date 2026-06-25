"""
Totem ESG — Ibero Group
Visual: Clean branco corporativo, teclado virtual proprio
v4.0 — Sem teclado nativo Android, sem empurrar tela
"""

import os
import json
import re
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
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.network.urlrequest import UrlRequest
from kivy.utils import get_color_from_hex

# ── Config ────────────────────────────────────────────────────
API_URL   = os.environ.get("API_URL", "https://totem-esg.onrender.com")
TABLET_ID = os.environ.get("TABLET_ID", "totem-ibero-01")

# ── Paleta clean branco + azul Ibero ─────────────────────────
C_WHITE      = get_color_from_hex("#FFFFFF")
C_BG         = get_color_from_hex("#F0F2F7")
C_BLUE       = get_color_from_hex("#1565C0")
C_BLUE_LIGHT = get_color_from_hex("#1E88E5")
C_BLUE_PALE  = get_color_from_hex("#EBF1FF")
C_BLUE_MUTED = get_color_from_hex("#C8D8F8")
C_DARK       = get_color_from_hex("#1A2340")
C_GRAY       = get_color_from_hex("#4A5568")
C_GRAY_LIGHT = get_color_from_hex("#A0AABB")
C_BORDER     = get_color_from_hex("#E4E8F0")
C_BORDER_MED = get_color_from_hex("#D0D5E8")
C_KEY_BG     = get_color_from_hex("#EAECF4")
C_GREEN      = get_color_from_hex("#2E7D32")
C_RED        = get_color_from_hex("#E53935")

TOPICS = {
    "ambiental": {"label": "Ambiental", "code": "AMB", "color": get_color_from_hex("#00897B"),
                  "qs": ["Qual e a meta de reducao de CO2?", "Como esta o consumo de agua?",
                         "Quanto residuo reciclamos?"]},
    "seguranca": {"label": "Seguranca",  "code": "SST", "color": get_color_from_hex("#F57C00"),
                  "qs": ["Quantos dias sem acidentes?", "Quais EPIs devo usar?",
                         "O que fazer em emergencia?"]},
    "social":    {"label": "Social",     "code": "SOC", "color": get_color_from_hex("#7B1FA2"),
                  "qs": ["Quais programas sociais temos?", "Como participar de treinamentos?",
                         "Quais sao as metas sociais?"]},
    "politicas": {"label": "Politicas",  "code": "POL", "color": C_BLUE,
                  "qs": ["O que diz a politica integrada?", "Quais sao nossas certificacoes?",
                         "Como reportar um problema?"]},
}

def clean_md(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'#{1,6}\s*',     '',    text)
    text = re.sub(r'^\s*[\*\-]\s+', '- ',  text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ── Helpers canvas ────────────────────────────────────────────
def draw_bg(w, color, radius=0):
    w.canvas.before.clear()
    with w.canvas.before:
        Color(*color)
        if radius:
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(radius)])
        else:
            Rectangle(pos=w.pos, size=w.size)

def bind_bg(w, color, radius=0):
    w.bind(pos=lambda s, v: draw_bg(s, color, radius),
           size=lambda s, v: draw_bg(s, color, radius))
    draw_bg(w, color, radius)

# ── Botão base ────────────────────────────────────────────────
class Btn(Button):
    def __init__(self, bg=None, fg=None, r=8, border_color=None, **kw):
        super().__init__(**kw)
        self._bg     = bg or C_BLUE
        self._fg     = fg or C_WHITE
        self._r      = r
        self._border = border_color
        self.background_color = (0, 0, 0, 0)
        self.color = self._fg
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            if self._border:
                Color(*self._border)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self._r)])
                Color(*self._bg)
                RoundedRectangle(
                    pos=(self.x+dp(1), self.y+dp(1)),
                    size=(max(self.width-dp(2), 1), max(self.height-dp(2), 1)),
                    radius=[dp(max(self._r-1, 1))])
            else:
                Color(*self._bg)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self._r)])

# ── Bolha de mensagem ─────────────────────────────────────────
class Bubble(BoxLayout):
    def __init__(self, text, is_user=False, initials="OP", **kw):
        super().__init__(orientation="vertical",
                         size_hint_y=None, padding=[dp(4), dp(2)], **kw)
        self.is_user = is_user
        row = BoxLayout(size_hint_y=None, spacing=dp(8))

        av_bg  = C_BLUE if is_user else C_BLUE
        av_txt = initials[:2].upper() if is_user else "IB"
        av = Label(text=av_txt, font_size=sp(10), bold=True, color=C_WHITE,
                   size_hint=(None, None), size=(dp(32), dp(32)))
        with av.canvas.before:
            Color(*av_bg)
            Ellipse(pos=av.pos, size=av.size)
        av.bind(pos=lambda w, v, c=av_bg: self._draw_av(w, c),
                size=lambda w, v, c=av_bg: self._draw_av(w, c))

        lbl = Label(
            text=text, font_size=sp(14),
            color=C_WHITE if is_user else C_DARK,
            halign="left", valign="top",
            text_size=(Window.width * 0.55, None),
        )
        lbl.bind(texture_size=lbl.setter("size"))

        bc  = C_BLUE if is_user else C_WHITE
        brd = C_BLUE_MUTED if is_user else C_BORDER
        rad = [dp(12), dp(4), dp(12), dp(12)] if is_user else [dp(4), dp(12), dp(12), dp(12)]

        bubble = BoxLayout(size_hint=(None, None), padding=[dp(12), dp(10)])
        lbl.bind(size=lambda w, v: self._upd(bubble, w))
        bubble.add_widget(lbl)

        with bubble.canvas.before:
            Color(*brd)
            RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=rad)
            Color(*bc)
            RoundedRectangle(
                pos=(bubble.x+dp(1), bubble.y+dp(1)),
                size=(max(bubble.width-dp(2), 1), max(bubble.height-dp(2), 1)),
                radius=rad)
        bubble.bind(
            pos=lambda w, v, b=bc, d=brd, r=rad: self._draw_bubble(w, b, d, r),
            size=lambda w, v, b=bc, d=brd, r=rad: self._draw_bubble(w, b, d, r))

        if is_user:
            row.add_widget(Widget())
            row.add_widget(bubble)
            row.add_widget(av)
        else:
            row.add_widget(av)
            row.add_widget(bubble)
            row.add_widget(Widget())

        row.size_hint_y = None
        row.bind(minimum_height=row.setter("height"))
        self.add_widget(row)
        self._row = row
        self.bind(minimum_height=self.setter("height"))

    def _draw_av(self, w, c):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*c); Ellipse(pos=w.pos, size=w.size)

    def _upd(self, bubble, lbl):
        bubble.width  = min(lbl.width + dp(24), Window.width * 0.62)
        bubble.height = lbl.height + dp(20)
        self._row.height = bubble.height + dp(8)
        self.height = self._row.height + dp(4)

    def _draw_bubble(self, w, bc, brd, rad):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*brd)
            RoundedRectangle(pos=w.pos, size=w.size, radius=rad)
            Color(*bc)
            RoundedRectangle(
                pos=(w.x+dp(1), w.y+dp(1)),
                size=(max(w.width-dp(2), 1), max(w.height-dp(2), 1)),
                radius=rad)


# ════════════════════════════════════════════════════════════
#  TELA 1 — BOAS-VINDAS
# ════════════════════════════════════════════════════════════
class WelcomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._typed = ""
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        bind_bg(root, C_BG)

        # Header azul
        hdr = BoxLayout(size_hint_y=None, height=dp(52),
                        padding=[dp(18), 0], spacing=dp(12))
        bind_bg(hdr, C_BLUE)

        logo_box = BoxLayout(size_hint=(None, None), size=(dp(34), dp(34)))
        with logo_box.canvas:
            Color(*C_WHITE)
            RoundedRectangle(pos=logo_box.pos, size=logo_box.size, radius=[dp(8)])
        logo_box.bind(pos=lambda w, v: self._redraw_logo(w),
                      size=lambda w, v: self._redraw_logo(w))
        logo_box.add_widget(Label(text="IB", font_size=sp(12), bold=True,
                                  color=C_BLUE,
                                  size_hint=(None, None), size=(dp(34), dp(34))))

        hdr_titles = BoxLayout(orientation="vertical", spacing=dp(1))
        hdr_titles.add_widget(Label(text="Ibero Group", font_size=sp(13), bold=True,
                                    color=C_WHITE, halign="left",
                                    size_hint_y=None, height=dp(22)))
        hdr_titles.add_widget(Label(text="Totem ESG", font_size=sp(10),
                                    color=get_color_from_hex("#BBDEFB"),
                                    halign="left", size_hint_y=None, height=dp(16)))
        hdr.add_widget(logo_box)
        hdr.add_widget(hdr_titles)
        hdr.add_widget(Widget())

        status_row = BoxLayout(size_hint=(None, None), size=(dp(80), dp(24)),
                               spacing=dp(4), padding=[dp(8), dp(4)])
        bind_bg(status_row, get_color_from_hex("#1976D2"), radius=12)
        st_dot = Widget(size_hint=(None, None), size=(dp(7), dp(7)))
        with st_dot.canvas:
            Color(*C_GREEN)
            Ellipse(pos=st_dot.pos, size=st_dot.size)
        st_dot.bind(pos=lambda w, v: self._redraw_dot(w),
                    size=lambda w, v: self._redraw_dot(w))
        status_row.add_widget(st_dot)
        status_row.add_widget(Label(text="Online", font_size=sp(11),
                                    color=C_WHITE))
        hdr.add_widget(status_row)
        root.add_widget(hdr)

        # Centro — card de boas-vindas
        center = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(16))
        bind_bg(center, C_BG)

        center.add_widget(Widget())

        # Card principal
        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(28), dp(22)], spacing=dp(14))
        with card.canvas.before:
            Color(*C_WHITE)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(18)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(18)),
                 width=dp(1))
        card.bind(pos=lambda w, v: self._redraw_card(w),
                  size=lambda w, v: self._redraw_card(w))

        # Ícone IB
        icon_row = BoxLayout(size_hint_y=None, height=dp(60))
        icon_box = BoxLayout(size_hint=(None, None), size=(dp(56), dp(56)))
        with icon_box.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=icon_box.pos, size=icon_box.size, radius=[dp(14)])
        icon_box.bind(pos=lambda w, v: self._redraw_icon(w),
                      size=lambda w, v: self._redraw_icon(w))
        icon_box.add_widget(Label(text="IB", font_size=sp(20), bold=True,
                                  color=C_WHITE,
                                  size_hint=(None, None), size=(dp(56), dp(56))))
        icon_row.add_widget(Widget())
        icon_row.add_widget(icon_box)
        icon_row.add_widget(Widget())
        card.add_widget(icon_row)

        card.add_widget(Label(
            text="Ola! Sou o Agente ESG",
            font_size=sp(20), bold=True, color=C_DARK,
            halign="center", size_hint_y=None, height=dp(32)))
        card.add_widget(Label(
            text="da Ibero Group",
            font_size=sp(14), color=C_BLUE,
            halign="center", size_hint_y=None, height=dp(22)))
        card.add_widget(Label(
            text="Como voce se chama?",
            font_size=sp(14), color=C_GRAY,
            halign="center", size_hint_y=None, height=dp(22)))

        # Display do nome
        self.name_disp = Label(
            text="Digite seu nome...",
            font_size=sp(16),
            color=C_GRAY_LIGHT,
            halign="left", valign="middle",
            size_hint_y=None, height=dp(46),
        )
        name_box = BoxLayout(size_hint_y=None, height=dp(46),
                             padding=[dp(14), dp(8)])
        with name_box.canvas.before:
            Color(*C_BLUE_PALE)
            RoundedRectangle(pos=name_box.pos, size=name_box.size, radius=[dp(10)])
            Color(*C_BLUE_MUTED)
            Line(rounded_rectangle=(name_box.x, name_box.y,
                                    name_box.width, name_box.height, dp(10)),
                 width=dp(1.5))
        name_box.bind(pos=lambda w, v: self._redraw_name_box(w),
                      size=lambda w, v: self._redraw_name_box(w))
        name_box.add_widget(self.name_disp)
        card.add_widget(name_box)

        # Botão entrar
        enter_btn = Btn(
            text="Entrar no Agente ESG",
            bg=C_BLUE, fg=C_WHITE,
            font_size=sp(15), bold=True,
            size_hint_y=None, height=dp(48), r=10,
        )
        enter_btn.bind(on_press=self._confirm)
        card.add_widget(enter_btn)
        card.bind(minimum_height=card.setter("height"))
        center.add_widget(card)

        # Teclado virtual
        kb = self._build_keyboard()
        center.add_widget(kb)
        center.add_widget(Widget())
        root.add_widget(center)
        self.add_widget(root)

    def _redraw_logo(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_WHITE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(8)])

    def _redraw_dot(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_GREEN); Ellipse(pos=w.pos, size=w.size)

    def _redraw_card(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_WHITE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(18)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(18)),
                 width=dp(1))

    def _redraw_icon(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(14)])

    def _redraw_name_box(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_BLUE_PALE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])
            Color(*C_BLUE_MUTED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(10)),
                 width=dp(1.5))

    def _build_keyboard(self):
        rows = [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
        ]
        kb = BoxLayout(orientation="vertical",
                       size_hint_y=None, height=dp(178), spacing=dp(4))
        for row in rows:
            rbox = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
            for k in row:
                btn = Btn(text=k, bg=C_KEY_BG, fg=C_DARK,
                          font_size=sp(14), bold=True, r=7,
                          border_color=C_BORDER_MED)
                btn.bind(on_press=lambda b, k=k: self._type(k))
                rbox.add_widget(btn)
            kb.add_widget(rbox)

        # Linha especial
        spec = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
        del_btn = Btn(text="< Del", bg=C_KEY_BG, fg=C_RED,
                      font_size=sp(13), bold=True, r=7,
                      border_color=C_BORDER_MED)
        del_btn.bind(on_press=lambda b: self._type("DEL"))

        spc_btn = Btn(text="Espaco", bg=C_KEY_BG, fg=C_GRAY,
                      font_size=sp(13), r=7,
                      border_color=C_BORDER_MED)
        spc_btn.bind(on_press=lambda b: self._type(" "))

        ok_btn = Btn(text="OK  >", bg=C_BLUE, fg=C_WHITE,
                     font_size=sp(14), bold=True, r=7)
        ok_btn.bind(on_press=self._confirm)

        spec.add_widget(del_btn)
        spec.add_widget(spc_btn)
        spec.add_widget(ok_btn)
        kb.add_widget(spec)
        return kb

    def _type(self, k):
        if k == "DEL":
            self._typed = self._typed[:-1]
        else:
            if len(self._typed) < 18:
                self._typed += k
        self._update_display()

    def _update_display(self):
        if self._typed:
            self.name_disp.text  = self._typed
            self.name_disp.color = C_DARK
        else:
            self.name_disp.text  = "Digite seu nome..."
            self.name_disp.color = C_GRAY_LIGHT

    def _confirm(self, *_):
        name = self._typed.strip().title() or "Operador"
        App.get_running_app().operator_name = name
        self.manager.current = "chat"


# ════════════════════════════════════════════════════════════
#  TELA 2 — CHAT
# ════════════════════════════════════════════════════════════
class ChatScreen(Screen):
    topic      = StringProperty("ambiental")
    is_loading = BooleanProperty(False)
    history    = ListProperty([])
    quick_list = ListProperty([])

    def __init__(self, **kw):
        super().__init__(**kw)
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        else:
            self._restart()
        self._load_quick()

    def _build(self):
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")

        root = BoxLayout(orientation="horizontal")
        bind_bg(root, C_BG)

        # ── Sidebar ──────────────────────────────────────────
        sidebar = BoxLayout(orientation="vertical",
                            size_hint_x=None, width=dp(185),
                            padding=[dp(12), dp(14), dp(12), dp(12)],
                            spacing=dp(4))
        bind_bg(sidebar, C_WHITE)

        # Borda direita da sidebar
        with sidebar.canvas.after:
            Color(*C_BORDER)
            self._sb_line = Rectangle(
                pos=(sidebar.right-dp(1), sidebar.y),
                size=(dp(1), sidebar.height))
        sidebar.bind(
            pos=lambda w, v: setattr(self._sb_line, "pos",
                                     (w.right-dp(1), w.y)),
            size=lambda w, v: setattr(self._sb_line, "size",
                                      (dp(1), v[1])))

        # Logo
        logo_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        logo_b = BoxLayout(size_hint=(None, None), size=(dp(36), dp(36)))
        with logo_b.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=logo_b.pos, size=logo_b.size, radius=[dp(9)])
        logo_b.bind(pos=lambda w, v: self._redraw_lb(w),
                    size=lambda w, v: self._redraw_lb(w))
        logo_b.add_widget(Label(text="IB", font_size=sp(13), bold=True,
                                color=C_WHITE,
                                size_hint=(None, None), size=(dp(36), dp(36))))
        tc = BoxLayout(orientation="vertical", spacing=dp(1))
        tc.add_widget(Label(text="Ibero Group", font_size=sp(12), bold=True,
                            color=C_DARK, halign="left",
                            size_hint_y=None, height=dp(20)))
        tc.add_widget(Label(text="Totem ESG", font_size=sp(10),
                            color=C_BLUE, halign="left",
                            size_hint_y=None, height=dp(16)))
        logo_row.add_widget(logo_b)
        logo_row.add_widget(tc)
        sidebar.add_widget(logo_row)

        # Divisor
        div = Widget(size_hint_y=None, height=dp(1))
        bind_bg(div, C_BORDER)
        sidebar.add_widget(div)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(4)))

        # Saudação
        self.greet_lbl = Label(
            text=f"Ola, {name}!",
            font_size=sp(12), bold=True, color=C_BLUE,
            halign="left", size_hint_y=None, height=dp(22))
        sidebar.add_widget(self.greet_lbl)

        sidebar.add_widget(Label(
            text="TEMAS", font_size=sp(9), bold=True,
            color=C_GRAY_LIGHT, halign="left",
            size_hint_y=None, height=dp(18)))

        self.topic_btns = {}
        for key, meta in TOPICS.items():
            btn = self._make_topic_btn(key, meta)
            sidebar.add_widget(btn)
            self.topic_btns[key] = btn

        sidebar.add_widget(Widget())

        div2 = Widget(size_hint_y=None, height=dp(1))
        bind_bg(div2, C_BORDER)
        sidebar.add_widget(div2)

        exit_btn = Btn(
            text="Sair",
            bg=C_BG, fg=C_GRAY_LIGHT,
            font_size=sp(12), r=8,
            border_color=C_BORDER,
            size_hint_y=None, height=dp(38))
        exit_btn.bind(on_press=self._exit)
        sidebar.add_widget(exit_btn)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(6)))
        root.add_widget(sidebar)

        # ── Área de chat ──────────────────────────────────────
        right = BoxLayout(orientation="vertical")
        bind_bg(right, C_BG)

        # Sub-header
        sub = BoxLayout(size_hint_y=None, height=dp(48),
                        padding=[dp(16), 0], spacing=dp(10))
        bind_bg(sub, C_WHITE)

        # Barra azul acento
        acc = Widget(size_hint=(None, None), size=(dp(3), dp(32)))
        bind_bg(acc, C_BLUE, radius=2)

        self.header_lbl = Label(
            text="Agente ESG  —  Ambiental",
            font_size=sp(14), bold=True,
            color=C_DARK, halign="left")
        sub.add_widget(acc)
        sub.add_widget(self.header_lbl)

        # Status
        st_box = BoxLayout(size_hint=(None, None), size=(dp(72), dp(24)),
                           spacing=dp(4), padding=[dp(8), dp(4)])
        bind_bg(st_box, C_BG, radius=12)
        self.st_dot = Widget(size_hint=(None, None), size=(dp(7), dp(7)))
        with self.st_dot.canvas:
            Color(*C_GREEN); Ellipse(pos=self.st_dot.pos, size=self.st_dot.size)
        self.st_dot.bind(
            pos=lambda w, v: self._draw_dot(w, C_GREEN),
            size=lambda w, v: self._draw_dot(w, C_GREEN))
        self.st_lbl = Label(text="Online", font_size=sp(11), color=C_GREEN)
        st_box.add_widget(self.st_dot)
        st_box.add_widget(self.st_lbl)
        sub.add_widget(st_box)
        right.add_widget(sub)

        # Linha separadora
        sep = Widget(size_hint_y=None, height=dp(1))
        bind_bg(sep, C_BORDER)
        right.add_widget(sep)

        # Scroll chat
        self.scroll = ScrollView(do_scroll_x=False)
        self.msg_box = BoxLayout(
            orientation="vertical", size_hint_y=None,
            spacing=dp(10), padding=[dp(14), dp(14)])
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        self.scroll.add_widget(self.msg_box)
        right.add_widget(self.scroll)

        # Linha input
        inp_sep = Widget(size_hint_y=None, height=dp(1))
        bind_bg(inp_sep, C_BORDER)
        right.add_widget(inp_sep)

        # Barra de input
        inp_bar = BoxLayout(size_hint_y=None, height=dp(62),
                            padding=[dp(12), dp(10)], spacing=dp(10))
        bind_bg(inp_bar, C_WHITE)

        from kivy.uix.textinput import TextInput
        self.txt = TextInput(
            hint_text=f"Ola {name}, o que deseja saber?",
            font_size=sp(14), multiline=False,
            background_color=C_BG,
            foreground_color=C_DARK,
            cursor_color=C_BLUE,
            hint_text_color=C_GRAY_LIGHT,
            padding=[dp(14), dp(12)],
            keyboard_mode='managed',  # impede teclado nativo Android
        )
        self.txt.bind(on_text_validate=self.send_msg)
        self.txt.bind(focus=self._on_input_focus)

        self.send_btn = Btn(
            text=">",
            bg=C_BLUE, fg=C_WHITE,
            font_size=sp(20), bold=True,
            size_hint_x=None, width=dp(50), r=10)
        self.send_btn.bind(on_press=self.send_msg)

        inp_bar.add_widget(self.txt)
        inp_bar.add_widget(self.send_btn)
        right.add_widget(inp_bar)

        root.add_widget(right)
        self.add_widget(root)
        self._show_welcome()

    def _redraw_lb(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(9)])

    def _draw_dot(self, w, color):
        w.canvas.clear()
        with w.canvas:
            Color(*color); Ellipse(pos=w.pos, size=w.size)

    def _restart(self):
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")
        if hasattr(self, "greet_lbl"):
            self.greet_lbl.text = f"Ola, {name}!"
        if hasattr(self, "txt"):
            self.txt.hint_text = f"Ola {name}, o que deseja saber?"
        self.history.clear()
        self._show_welcome()

    def _make_topic_btn(self, key, meta):
        is_act = (key == "ambiental")
        row = BoxLayout(orientation="horizontal",
                        size_hint_y=None, height=dp(44),
                        spacing=dp(8), padding=[dp(6), dp(6)])

        bg  = C_BLUE_PALE if is_act else C_BG
        brd = C_BLUE      if is_act else C_BORDER

        with row.canvas.before:
            Color(*brd)
            RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(8)])
            Color(*bg)
            RoundedRectangle(
                pos=(row.x+dp(1), row.y+dp(1)),
                size=(max(row.width-dp(2), 1), max(row.height-dp(2), 1)),
                radius=[dp(7)])
        row._bg  = bg
        row._brd = brd

        def _rd(w, v, r=row):
            r.canvas.before.clear()
            with r.canvas.before:
                Color(*r._brd)
                RoundedRectangle(pos=r.pos, size=r.size, radius=[dp(8)])
                Color(*r._bg)
                RoundedRectangle(
                    pos=(r.x+dp(1), r.y+dp(1)),
                    size=(max(r.width-dp(2), 1), max(r.height-dp(2), 1)),
                    radius=[dp(7)])
        row.bind(pos=_rd, size=_rd)

        bd = BoxLayout(size_hint=(None, None), size=(dp(26), dp(26)))
        with bd.canvas.before:
            Color(*meta["color"])
            RoundedRectangle(pos=bd.pos, size=bd.size, radius=[dp(6)])
        bd.bind(pos=lambda w, v, c=meta["color"]: self._rd_badge(w, c),
                size=lambda w, v, c=meta["color"]: self._rd_badge(w, c))
        bd.add_widget(Label(text=meta["code"], font_size=sp(9), bold=True,
                            color=C_WHITE,
                            size_hint=(None, None), size=(dp(26), dp(26))))

        lbl = Label(text=meta["label"], font_size=sp(12),
                    bold=is_act,
                    color=C_BLUE if is_act else C_GRAY,
                    halign="left")
        row.add_widget(bd)
        row.add_widget(lbl)
        row._lbl = lbl
        row.bind(on_touch_down=lambda w, t, k=key: self._touch_topic(w, t, k))
        return row

    def _rd_badge(self, w, c):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*c)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(6)])

    def _touch_topic(self, row, touch, key):
        if row.collide_point(*touch.pos):
            self.set_topic(key)

    def set_topic(self, key):
        self.topic = key
        self.header_lbl.text = f"Agente ESG  —  {TOPICS[key]['label']}"
        for k, r in self.topic_btns.items():
            act = (k == key)
            r._bg  = C_BLUE_PALE if act else C_BG
            r._brd = C_BLUE      if act else C_BORDER
            r._lbl.bold  = act
            r._lbl.color = C_BLUE if act else C_GRAY
            r.canvas.before.clear()
            with r.canvas.before:
                Color(*r._brd)
                RoundedRectangle(pos=r.pos, size=r.size, radius=[dp(8)])
                Color(*r._bg)
                RoundedRectangle(
                    pos=(r.x+dp(1), r.y+dp(1)),
                    size=(max(r.width-dp(2), 1), max(r.height-dp(2), 1)),
                    radius=[dp(7)])
        self._load_quick()

    def _show_welcome(self):
        self.msg_box.clear_widgets()
        self.history.clear()
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")

        wrap = BoxLayout(orientation="vertical", size_hint_y=None,
                         spacing=dp(10), padding=[dp(4), dp(4)])

        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(18), dp(16)], spacing=dp(8))
        with card.canvas.before:
            Color(*C_WHITE)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(14)])
            Color(*C_BORDER)
            Line(rounded_rectangle=(card.x, card.y,
                                    card.width, card.height, dp(14)),
                 width=dp(1))
        card.bind(pos=lambda w, v: self._redraw_wcard(w),
                  size=lambda w, v: self._redraw_wcard(w))

        card.add_widget(Label(
            text=f"Bem-vindo, {name}!",
            font_size=sp(16), bold=True, color=C_BLUE,
            halign="center", size_hint_y=None, height=dp(28)))
        card.add_widget(Label(
            text="Escolha um tema ou faca sua pergunta.",
            font_size=sp(13), color=C_GRAY,
            halign="center", size_hint_y=None, height=dp(22)))
        card.bind(minimum_height=card.setter("height"))
        wrap.add_widget(card)

        self.quick_grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(8))
        self.quick_grid.bind(minimum_height=self.quick_grid.setter("height"))
        wrap.add_widget(self.quick_grid)
        wrap.bind(minimum_height=wrap.setter("height"))
        self.msg_box.add_widget(wrap)
        self._welcome_wrap = wrap
        self._render_quick()

    def _redraw_wcard(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_WHITE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(14)])
            Color(*C_BORDER)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(14)),
                 width=dp(1))

    def _render_quick(self):
        self.quick_grid.clear_widgets()
        qs = self.quick_list if self.quick_list else TOPICS[self.topic]["qs"]
        for q in qs[:6]:
            text = q["question"] if isinstance(q, dict) else q
            btn = Btn(text=text, bg=C_BG, fg=C_DARK,
                      font_size=sp(12),
                      size_hint_y=None, height=dp(50),
                      r=8, border_color=C_BORDER_MED)
            btn.bind(on_press=lambda b, q=text: self._prefill(q))
            self.quick_grid.add_widget(btn)

    def _prefill(self, q):
        self.txt.text = q
        self.send_msg()

    def send_msg(self, *_):
        text = self.txt.text.strip()
        if not text or self.is_loading:
            return
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")

        if hasattr(self, "_welcome_wrap") and self._welcome_wrap.parent:
            self.msg_box.remove_widget(self._welcome_wrap)

        self.txt.text = ""
        self.is_loading = True
        self.send_btn.disabled = True

        self._add_bubble(text, is_user=True, initials=name[:2])
        self._typing = self._add_typing()
        self.history.append({"role": "user", "content": text})

        payload = json.dumps({
            "question":  text,
            "topic":     self.topic,
            "tablet_id": f"{TABLET_ID}-{name.lower()[:8]}",
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
            timeout=45,
        )

    def _on_answer(self, res):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        raw    = res.get("answer", "Nao consegui processar. Tente novamente.")
        answer = clean_md(raw)
        self._add_bubble(answer, is_user=False)
        self.history.append({"role": "assistant", "content": answer})
        self.is_loading = False
        self.send_btn.disabled = False
        self._set_status("Online", C_GREEN)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.15)

    def _on_input_focus(self, instance, value):
        if value:
            instance.focus = False

    def _ping_server(self):
        UrlRequest(
            f"{API_URL}/ping",
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_reconnect(), 0),
            on_failure=lambda req, res: Clock.schedule_once(
                lambda dt: self._ping_server_retry(), 0),
            on_error=lambda req, err: Clock.schedule_once(
                lambda dt: self._ping_server_retry(), 0),
            timeout=10,
        )

    def _on_reconnect(self):
        self._set_status("Online", C_GREEN)

    def _ping_server_retry(self):
        Clock.schedule_once(lambda dt: self._ping_server(), 15)

    def _on_error(self):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        self._add_bubble(
            "Sem conexao com o servidor. Reconectando automaticamente...",
            is_user=False)
        self.is_loading = False
        self.send_btn.disabled = False
        self._set_status("Offline", C_RED)
        Clock.schedule_once(lambda dt: self._ping_server(), 10)

    def _set_status(self, text, color):
        self.st_lbl.text  = text
        self.st_lbl.color = color
        self._draw_dot(self.st_dot, color)

    def _add_bubble(self, text, is_user=False, initials="IB"):
        b = Bubble(text=text, is_user=is_user, initials=initials)
        self.msg_box.add_widget(b)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return b

    def _add_typing(self):
        lbl = Label(
            text="Agente digitando...",
            font_size=sp(13), color=C_BLUE,
            size_hint_y=None, height=dp(30), halign="left")
        self.msg_box.add_widget(lbl)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return lbl

    def _scroll_end(self):
        self.scroll.scroll_y = 0

    def _exit(self, *_):
        self.manager.current = "welcome"

    def _load_quick(self):
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
                self._render_quick()


# ════════════════════════════════════════════════════════════
#  APP
# ════════════════════════════════════════════════════════════
class TotemESGApp(App):
    operator_name = "Operador"

    def build(self):
        Window.clearcolor = get_color_from_hex("#F0F2F7")
        sm = ScreenManager(transition=FadeTransition(duration=0.25))
        sm.add_widget(WelcomeScreen(name="welcome"))
        sm.add_widget(ChatScreen(name="chat"))
        return sm


if __name__ == "__main__":
    TotemESGApp().run()
