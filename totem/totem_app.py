"""
Totem ESG — Ibero Group
v3.0 — Tela de boas-vindas com nome, teclado virtual touch, fix tokens/timeout
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
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.network.urlrequest import UrlRequest
from kivy.utils import get_color_from_hex

# ── Config ────────────────────────────────────────────────────
API_URL   = os.environ.get("API_URL", "https://totem-esg.onrender.com")
TABLET_ID = os.environ.get("TABLET_ID", "totem-ibero-01")

# ── Paleta Ibero Group ────────────────────────────────────────
C_NAVY       = get_color_from_hex("#0A1628")
C_NAVY_MID   = get_color_from_hex("#0D2144")
C_NAVY_LIGHT = get_color_from_hex("#1A3A6B")
C_BLUE       = get_color_from_hex("#1565C0")
C_BLUE_LIGHT = get_color_from_hex("#1E88E5")
C_NEON       = get_color_from_hex("#00E5FF")
C_GLOW       = get_color_from_hex("#90CAF9")
C_WHITE      = get_color_from_hex("#FFFFFF")
C_WHITE_70   = get_color_from_hex("#B0C4DE")
C_WHITE_40   = get_color_from_hex("#607D9E")
C_GREEN      = get_color_from_hex("#00C853")
C_RED        = get_color_from_hex("#FF5252")
C_BORDER     = get_color_from_hex("#1E3A5F")

TOPICS = {
    "ambiental": {"label": "Ambiental", "code": "AMB",
                  "color": get_color_from_hex("#00BFA5"),
                  "qs": ["Qual e a meta de reducao de CO2?",
                         "Como esta o consumo de agua?",
                         "Quanto residuo reciclamos?"]},
    "seguranca": {"label": "Seguranca", "code": "SST",
                  "color": get_color_from_hex("#FF6F00"),
                  "qs": ["Quantos dias sem acidentes?",
                         "Quais EPIs devo usar?",
                         "O que fazer em emergencia?"]},
    "social":    {"label": "Social",    "code": "SOC",
                  "color": get_color_from_hex("#7B1FA2"),
                  "qs": ["Quais programas sociais temos?",
                         "Como participar de treinamentos?",
                         "Quais sao as metas sociais?"]},
    "politicas": {"label": "Politicas", "code": "POL",
                  "color": C_BLUE_LIGHT,
                  "qs": ["O que diz a politica integrada?",
                         "Quais sao nossas certificacoes?",
                         "Como reportar um problema?"]},
}

# ── Limpa markdown ────────────────────────────────────────────
def clean_md(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'^\s*[\*\-]\s+', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ── Helpers ───────────────────────────────────────────────────
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

# ── Botão corporativo ─────────────────────────────────────────
class CBtn(Button):
    def __init__(self, bg=None, fg=None, r=10, border=None, **kw):
        super().__init__(**kw)
        self._bg = bg or C_BLUE
        self._fg = fg or C_WHITE
        self._r  = r
        self._border = border
        self.background_color = (0, 0, 0, 0)
        self.color = self._fg
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            if self._border:
                Color(*self._border)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[dp(self._r)])
                Color(*self._bg)
                RoundedRectangle(
                    pos=(self.x+dp(1), self.y+dp(1)),
                    size=(max(self.width-dp(2),1), max(self.height-dp(2),1)),
                    radius=[dp(max(self._r-1,1))])
            else:
                Color(*self._bg)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[dp(self._r)])

# ── Bolha de mensagem ─────────────────────────────────────────
class Bubble(BoxLayout):
    def __init__(self, text, is_user=False, name="OP", **kw):
        super().__init__(orientation="vertical",
                         size_hint_y=None, padding=[dp(4), dp(2)], **kw)
        self.is_user = is_user
        row = BoxLayout(size_hint_y=None, spacing=dp(10))

        av_color = C_BLUE if is_user else C_NEON
        av_text  = name[:2].upper() if is_user else "IB"
        av = Label(text=av_text, font_size=sp(10), bold=True,
                   color=C_NAVY if not is_user else C_WHITE,
                   size_hint=(None, None), size=(dp(34), dp(34)))
        with av.canvas.before:
            Color(*av_color)
            Ellipse(pos=av.pos, size=av.size)
        av.bind(pos=lambda w, v, c=av_color: self._draw_av(w, c),
                size=lambda w, v, c=av_color: self._draw_av(w, c))

        lbl = Label(text=text, font_size=sp(14),
                    color=C_WHITE,
                    halign="left", valign="top",
                    text_size=(Window.width * 0.56, None))
        lbl.bind(texture_size=lbl.setter("size"))

        bc = C_BLUE if is_user else C_NAVY_LIGHT
        brd = C_NEON if is_user else C_BORDER
        r_u = [dp(14), dp(4), dp(14), dp(14)]
        r_b = [dp(4), dp(14), dp(14), dp(14)]
        radius = r_u if is_user else r_b

        bubble = BoxLayout(size_hint=(None, None), padding=[dp(14), dp(10)])
        lbl.bind(size=lambda w, v: self._upd(bubble, w))
        bubble.add_widget(lbl)

        with bubble.canvas.before:
            Color(*brd)
            RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=radius)
            Color(*bc)
            RoundedRectangle(
                pos=(bubble.x+dp(1), bubble.y+dp(1)),
                size=(max(bubble.width-dp(2),1), max(bubble.height-dp(2),1)),
                radius=radius)
        bubble.bind(
            pos=lambda w, v, b=bc, d=brd, rad=radius:
                self._draw_bubble(w, b, d, rad),
            size=lambda w, v, b=bc, d=brd, rad=radius:
                self._draw_bubble(w, b, d, rad))

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
        bubble.width  = min(lbl.width+dp(28), Window.width*0.62)
        bubble.height = lbl.height+dp(20)
        self._row.height = bubble.height+dp(8)
        self.height = self._row.height+dp(4)

    def _draw_bubble(self, w, bc, brd, radius):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*brd)
            RoundedRectangle(pos=w.pos, size=w.size, radius=radius)
            Color(*bc)
            RoundedRectangle(
                pos=(w.x+dp(1), w.y+dp(1)),
                size=(max(w.width-dp(2),1), max(w.height-dp(2),1)),
                radius=radius)


# ════════════════════════════════════════════════════════════
#  TELA 1 — BOAS-VINDAS (pede o nome)
# ════════════════════════════════════════════════════════════
class WelcomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        bind_bg(root, C_NAVY)

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(52),
                           padding=[dp(20), 0])
        bind_bg(header, C_NAVY_MID)
        header.add_widget(Label(
            text="Ibero Group  |  Totem ESG",
            font_size=sp(15), bold=True, color=C_WHITE, halign="left"))
        status = Label(text="● Agente Online", font_size=sp(12),
                       color=C_GREEN, size_hint_x=None, width=dp(120))
        header.add_widget(status)
        root.add_widget(header)

        # Linha neon
        line = Widget(size_hint_y=None, height=dp(2))
        bind_bg(line, C_NEON)
        root.add_widget(line)

        # Centro
        center = BoxLayout(orientation="vertical", padding=dp(30),
                           spacing=dp(20))
        bind_bg(center, C_NAVY)

        center.add_widget(Widget())

        # Card principal
        card = BoxLayout(orientation="vertical",
                         size_hint_y=None, height=dp(380),
                         padding=[dp(32), dp(28)], spacing=dp(16))
        with card.canvas.before:
            Color(*C_NAVY_LIGHT)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(20)])
            Color(*C_NEON)
            Line(rounded_rectangle=(card.x, card.y,
                                    card.width, card.height, dp(20)),
                 width=dp(1.2))
        card.bind(pos=lambda w, v: self._draw_card(w),
                  size=lambda w, v: self._draw_card(w))

        # Ícone IB
        icon_row = BoxLayout(size_hint_y=None, height=dp(72))
        icon_box = BoxLayout(size_hint=(None, None), size=(dp(72), dp(72)))
        with icon_box.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=icon_box.pos, size=icon_box.size,
                             radius=[dp(18)])
        icon_box.bind(pos=lambda w, v: self._draw_icon(w),
                      size=lambda w, v: self._draw_icon(w))
        icon_lbl = Label(text="IB", font_size=sp(24), bold=True,
                         color=C_NEON,
                         size_hint=(None, None), size=(dp(72), dp(72)))
        icon_box.add_widget(icon_lbl)
        icon_row.add_widget(Widget())
        icon_row.add_widget(icon_box)
        icon_row.add_widget(Widget())
        card.add_widget(icon_row)

        card.add_widget(Label(
            text="Ola! Sou o Agente ESG",
            font_size=sp(22), bold=True, color=C_WHITE,
            halign="center", size_hint_y=None, height=dp(36)))
        card.add_widget(Label(
            text="da Ibero Group",
            font_size=sp(16), color=C_NEON,
            halign="center", size_hint_y=None, height=dp(26)))
        card.add_widget(Label(
            text="Como voce se chama?",
            font_size=sp(14), color=C_WHITE_70,
            halign="center", size_hint_y=None, height=dp(24)))

        # Campo nome
        self.name_input = TextInput(
            hint_text="Digite seu nome aqui...",
            font_size=sp(16),
            multiline=False,
            background_color=C_NAVY_MID,
            foreground_color=C_WHITE,
            cursor_color=C_NEON,
            hint_text_color=C_WHITE_40,
            padding=[dp(16), dp(14)],
            size_hint_y=None, height=dp(50),
        )
        self.name_input.bind(on_text_validate=self._confirm)
        card.add_widget(self.name_input)

        # Botão confirmar
        btn = CBtn(
            text="Entrar no Agente ESG",
            bg=C_BLUE, fg=C_WHITE,
            font_size=sp(15), bold=True,
            size_hint_y=None, height=dp(50), r=12,
            border=C_NEON,
        )
        btn.bind(on_press=self._confirm)
        card.add_widget(btn)

        center.add_widget(card)
        center.add_widget(Widget())

        # Teclado virtual
        kb = self._build_keyboard()
        center.add_widget(kb)

        root.add_widget(center)
        self.add_widget(root)

    def _draw_card(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_NAVY_LIGHT)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(20)])
            Color(*C_NEON)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(20)),
                 width=dp(1.2))

    def _draw_icon(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(18)])

    def _build_keyboard(self):
        rows = [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
            ["APAGAR", "ESPACO", "CONFIRMAR"],
        ]
        kb = BoxLayout(orientation="vertical",
                       size_hint_y=None, height=dp(180), spacing=dp(4))
        for row in rows:
            rbox = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
            for key in row:
                if key == "APAGAR":
                    btn = CBtn(text="<", bg=C_NAVY_MID, fg=C_WHITE_70,
                               font_size=sp(14), r=7, border=C_BORDER)
                    btn.bind(on_press=lambda b: self._kb("APAGAR"))
                elif key == "ESPACO":
                    btn = CBtn(text="_", bg=C_NAVY_MID, fg=C_WHITE_70,
                               font_size=sp(14), r=7, border=C_BORDER)
                    btn.bind(on_press=lambda b: self._kb(" "))
                elif key == "CONFIRMAR":
                    btn = CBtn(text="OK", bg=C_BLUE, fg=C_WHITE,
                               font_size=sp(14), bold=True, r=7, border=C_NEON)
                    btn.bind(on_press=self._confirm)
                else:
                    btn = CBtn(text=key, bg=C_NAVY_LIGHT, fg=C_WHITE,
                               font_size=sp(14), r=7, border=C_BORDER)
                    btn.bind(on_press=lambda b, k=key: self._kb(k))
                rbox.add_widget(btn)
            kb.add_widget(rbox)
        return kb

    def _kb(self, key):
        if key == "APAGAR":
            self.name_input.text = self.name_input.text[:-1]
        else:
            if len(self.name_input.text) < 20:
                self.name_input.text += key

    def _confirm(self, *_):
        name = self.name_input.text.strip().title()
        if not name:
            name = "Operador"
        app = App.get_running_app()
        app.operator_name = name
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
        bind_bg(root, C_NAVY)

        # ── Sidebar ──────────────────────────────────────────
        sidebar = BoxLayout(
            orientation="vertical",
            size_hint_x=None, width=dp(195),
            padding=[dp(12), dp(16), dp(12), dp(12)],
            spacing=dp(6),
        )
        bind_bg(sidebar, C_NAVY_MID)

        logo_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        badge = BoxLayout(size_hint=(None, None), size=(dp(40), dp(40)))
        with badge.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=badge.pos, size=badge.size, radius=[dp(10)])
        badge.bind(pos=lambda w, v: self._draw_badge(w),
                   size=lambda w, v: self._draw_badge(w))
        badge.add_widget(Label(text="IB", font_size=sp(14), bold=True,
                               color=C_NEON,
                               size_hint=(None, None), size=(dp(40), dp(40))))
        title_col = BoxLayout(orientation="vertical", spacing=dp(1))
        title_col.add_widget(Label(
            text="Ibero Group", font_size=sp(12), bold=True,
            color=C_WHITE, halign="left", size_hint_y=None, height=dp(20)))
        title_col.add_widget(Label(
            text="Totem ESG", font_size=sp(10),
            color=C_NEON, halign="left", size_hint_y=None, height=dp(16)))
        logo_row.add_widget(badge)
        logo_row.add_widget(title_col)
        sidebar.add_widget(logo_row)

        div = Widget(size_hint_y=None, height=dp(1))
        bind_bg(div, C_NEON)
        sidebar.add_widget(div)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(4)))

        # Saudação personalizada
        self.greet_lbl = Label(
            text=f"Ola, {name}!",
            font_size=sp(13), bold=True, color=C_NEON,
            halign="left", size_hint_y=None, height=dp(24))
        sidebar.add_widget(self.greet_lbl)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(4)))

        sidebar.add_widget(Label(
            text="TEMAS", font_size=sp(9), bold=True,
            color=C_WHITE_40, halign="left",
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

        exit_btn = CBtn(
            text="Sair / Trocar",
            bg=C_NAVY_LIGHT, fg=C_WHITE_40,
            font_size=sp(11), r=8, border=C_BORDER,
            size_hint_y=None, height=dp(38),
        )
        exit_btn.bind(on_press=self._exit)
        sidebar.add_widget(exit_btn)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(6)))

        root.add_widget(sidebar)

        # ── Chat ─────────────────────────────────────────────
        right = BoxLayout(orientation="vertical")
        bind_bg(right, C_NAVY)

        header = BoxLayout(size_hint_y=None, height=dp(52),
                           padding=[dp(18), 0], spacing=dp(10))
        bind_bg(header, C_NAVY_MID)
        self.header_lbl = Label(
            text="Agente ESG  —  Ambiental",
            font_size=sp(15), bold=True, color=C_WHITE, halign="left")
        header.add_widget(self.header_lbl)
        st_box = BoxLayout(size_hint=(None, None), size=(dp(88), dp(26)),
                           padding=[dp(8), dp(4)])
        bind_bg(st_box, C_NAVY_LIGHT, radius=13)
        self.st_dot = Label(text="●", font_size=sp(10), color=C_GREEN,
                            size_hint=(None, None), size=(dp(16), dp(26)))
        self.st_lbl = Label(text="Online", font_size=sp(11), color=C_GREEN)
        st_box.add_widget(self.st_dot)
        st_box.add_widget(self.st_lbl)
        header.add_widget(st_box)
        right.add_widget(header)

        neon = Widget(size_hint_y=None, height=dp(2))
        bind_bg(neon, C_NEON)
        right.add_widget(neon)

        self.scroll = ScrollView(do_scroll_x=False)
        self.msg_box = BoxLayout(
            orientation="vertical", size_hint_y=None,
            spacing=dp(10), padding=[dp(14), dp(14)])
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        self.scroll.add_widget(self.msg_box)
        right.add_widget(self.scroll)

        neon2 = Widget(size_hint_y=None, height=dp(1))
        bind_bg(neon2, C_BORDER)
        right.add_widget(neon2)

        inp_bar = BoxLayout(size_hint_y=None, height=dp(64),
                            padding=[dp(12), dp(10)], spacing=dp(10))
        bind_bg(inp_bar, C_NAVY_MID)
        self.txt = TextInput(
            hint_text=f"Olá {name}, o que deseja saber?",
            font_size=sp(14), multiline=False,
            background_color=C_NAVY_LIGHT,
            foreground_color=C_WHITE,
            cursor_color=C_NEON,
            hint_text_color=C_WHITE_40,
            padding=[dp(14), dp(12)],
        )
        self.txt.bind(on_text_validate=self.send_msg)
        self.send_btn = CBtn(
            text=">", bg=C_BLUE, fg=C_WHITE,
            font_size=sp(20), bold=True,
            size_hint_x=None, width=dp(52), r=10, border=C_NEON)
        self.send_btn.bind(on_press=self.send_msg)
        inp_bar.add_widget(self.txt)
        inp_bar.add_widget(self.send_btn)
        right.add_widget(inp_bar)

        root.add_widget(right)
        self.add_widget(root)
        self._show_welcome()

    def _draw_badge(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])

    def _restart(self):
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")
        if hasattr(self, "greet_lbl"):
            self.greet_lbl.text = f"Ola, {name}!"
        if hasattr(self, "txt"):
            self.txt.hint_text = f"Olá {name}, o que deseja saber?"
        self.history.clear()
        self._show_welcome()

    def _make_topic_btn(self, key, meta):
        is_act = (key == "ambiental")
        row = BoxLayout(orientation="horizontal",
                        size_hint_y=None, height=dp(46),
                        spacing=dp(8), padding=[dp(8), dp(6)])
        bg  = C_BLUE if is_act else C_NAVY_LIGHT
        brd = C_NEON if is_act else C_BORDER

        with row.canvas.before:
            Color(*brd)
            RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(9)])
            Color(*bg)
            RoundedRectangle(
                pos=(row.x+dp(1), row.y+dp(1)),
                size=(max(row.width-dp(2),1), max(row.height-dp(2),1)),
                radius=[dp(8)])
        row._bg  = bg
        row._brd = brd

        def _rd(w, v, r=row):
            r.canvas.before.clear()
            with r.canvas.before:
                Color(*r._brd)
                RoundedRectangle(pos=r.pos, size=r.size, radius=[dp(9)])
                Color(*r._bg)
                RoundedRectangle(
                    pos=(r.x+dp(1), r.y+dp(1)),
                    size=(max(r.width-dp(2),1), max(r.height-dp(2),1)),
                    radius=[dp(8)])
        row.bind(pos=_rd, size=_rd)

        bd = BoxLayout(size_hint=(None, None), size=(dp(28), dp(28)))
        with bd.canvas.before:
            Color(*meta["color"])
            RoundedRectangle(pos=bd.pos, size=bd.size, radius=[dp(6)])
        bd.bind(pos=lambda w, v, c=meta["color"]: self._rd_sm(w, c),
                size=lambda w, v, c=meta["color"]: self._rd_sm(w, c))
        bd.add_widget(Label(text=meta["code"], font_size=sp(9),
                            bold=True, color=C_WHITE,
                            size_hint=(None, None), size=(dp(28), dp(28))))

        lbl = Label(text=meta["label"], font_size=sp(12),
                    bold=is_act,
                    color=C_WHITE if is_act else C_WHITE_70,
                    halign="left")
        row.add_widget(bd)
        row.add_widget(lbl)
        row._lbl = lbl
        row._key = key
        row.bind(on_touch_down=lambda w, t, k=key: self._touch_topic(w, t, k))
        return row

    def _rd_sm(self, w, c):
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
            r._bg  = C_BLUE if act else C_NAVY_LIGHT
            r._brd = C_NEON if act else C_BORDER
            r._lbl.bold  = act
            r._lbl.color = C_WHITE if act else C_WHITE_70
            r.canvas.before.clear()
            with r.canvas.before:
                Color(*r._brd)
                RoundedRectangle(pos=r.pos, size=r.size, radius=[dp(9)])
                Color(*r._bg)
                RoundedRectangle(
                    pos=(r.x+dp(1), r.y+dp(1)),
                    size=(max(r.width-dp(2),1), max(r.height-dp(2),1)),
                    radius=[dp(8)])
        self._load_quick()

    def _show_welcome(self):
        self.msg_box.clear_widgets()
        self.history.clear()
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")

        wrap = BoxLayout(orientation="vertical", size_hint_y=None,
                         spacing=dp(12), padding=[dp(8), dp(8)])
        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(22), dp(18)], spacing=dp(10))
        with card.canvas.before:
            Color(*C_NAVY_LIGHT)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(16)])
            Color(*C_NEON)
            Line(rounded_rectangle=(card.x, card.y,
                                    card.width, card.height, dp(16)),
                 width=dp(1))
        card.bind(pos=lambda w, v: self._draw_wcard(w),
                  size=lambda w, v: self._draw_wcard(w))

        card.add_widget(Label(
            text=f"Bem-vindo, {name}!",
            font_size=sp(18), bold=True, color=C_NEON,
            halign="center", size_hint_y=None, height=dp(30)))
        card.add_widget(Label(
            text="Escolha um tema ou faça sua pergunta.",
            font_size=sp(13), color=C_WHITE_70,
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

    def _draw_wcard(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_NAVY_LIGHT)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(16)])
            Color(*C_NEON)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(16)),
                 width=dp(1))

    def _render_quick(self):
        self.quick_grid.clear_widgets()
        qs = self.quick_list if self.quick_list else TOPICS[self.topic]["qs"]
        for q in qs[:6]:
            text = q["question"] if isinstance(q, dict) else q
            btn = CBtn(text=text, bg=C_NAVY_MID, fg=C_WHITE_70,
                       font_size=sp(12), size_hint_y=None, height=dp(48),
                       r=9, border=C_BORDER)
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

        self._add_bubble(text, is_user=True, name=name)
        self._typing = self._add_typing()
        self.history.append({"role": "user", "content": text})

        payload = json.dumps({
            "question":  text,
            "topic":     self.topic,
            "tablet_id": f"{TABLET_ID}-{name.lower()}",
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
        app    = App.get_running_app()
        name   = getattr(app, "operator_name", "Operador")
        self._add_bubble(answer, is_user=False, name=name)
        self.history.append({"role": "assistant", "content": answer})
        self.is_loading = False
        self.send_btn.disabled = False
        self._set_status("Online", C_GREEN)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.15)

    def _on_error(self):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        self._add_bubble(
            "Erro de conexao. Verifique a rede e tente novamente.",
            is_user=False)
        self.is_loading = False
        self.send_btn.disabled = False
        self._set_status("Offline", C_RED)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.15)

    def _set_status(self, text, color):
        self.st_lbl.text  = text
        self.st_lbl.color = color
        self.st_dot.color = color

    def _add_bubble(self, text, is_user=False, name="OP"):
        b = Bubble(text=text, is_user=is_user, name=name)
        self.msg_box.add_widget(b)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return b

    def _add_typing(self):
        lbl = Label(text="Agente digitando...",
                    font_size=sp(13), color=C_NEON,
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
        Window.clearcolor = get_color_from_hex("#0A1628")
        sm = ScreenManager(transition=FadeTransition(duration=0.3))
        sm.add_widget(WelcomeScreen(name="welcome"))
        sm.add_widget(ChatScreen(name="chat"))
        return sm


if __name__ == "__main__":
    TotemESGApp().run()
