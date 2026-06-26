"""
Totem ESG — Ibero Group v5.0
Arquitetura serverless: APK chama Gemini + Supabase diretamente
Zero backend intermediario — zero quedas
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

# ── Configuração — chaves diretas (sem backend) ───────────────
GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "SUA_CHAVE_GEMINI_AQUI")
SUPABASE_URL = os.environ.get("SUPABASE_URL",   "SUA_URL_SUPABASE_AQUI")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY",   "SUA_KEY_SUPABASE_AQUI")
TABLET_ID    = os.environ.get("TABLET_ID",      "totem-ibero-01")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
)

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
    "ambiental": {"label": "Ambiental", "code": "AMB",
                  "color": get_color_from_hex("#00897B"),
                  "qs": ["Qual e a meta de reducao de CO2?",
                         "Como esta o consumo de agua?",
                         "Quanto residuo reciclamos?"]},
    "seguranca": {"label": "Seguranca",  "code": "SST",
                  "color": get_color_from_hex("#F57C00"),
                  "qs": ["Quantos dias sem acidentes?",
                         "Quais EPIs devo usar?",
                         "O que fazer em emergencia?"]},
    "social":    {"label": "Social",     "code": "SOC",
                  "color": get_color_from_hex("#7B1FA2"),
                  "qs": ["Quais programas sociais temos?",
                         "Como participar de treinamentos?",
                         "Quais sao as metas sociais?"]},
    "politicas": {"label": "Politicas",  "code": "POL",
                  "color": C_BLUE,
                  "qs": ["O que diz a politica integrada?",
                         "Quais sao nossas certificacoes?",
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
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[dp(self._r)])
                Color(*self._bg)
                RoundedRectangle(
                    pos=(self.x+dp(1), self.y+dp(1)),
                    size=(max(self.width-dp(2), 1), max(self.height-dp(2), 1)),
                    radius=[dp(max(self._r-1, 1))])
            else:
                Color(*self._bg)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[dp(self._r)])

# ── Bolha de mensagem ─────────────────────────────────────────
class Bubble(BoxLayout):
    def __init__(self, text, is_user=False, initials="IB", **kw):
        super().__init__(orientation="vertical",
                         size_hint_y=None, padding=[dp(4), dp(2)], **kw)
        self.is_user = is_user
        row = BoxLayout(size_hint_y=None, spacing=dp(8))

        av_bg  = C_BLUE
        av_txt = initials[:2].upper() if is_user else "IB"
        av = Label(text=av_txt, font_size=sp(10), bold=True, color=C_WHITE,
                   size_hint=(None, None), size=(dp(32), dp(32)))
        with av.canvas.before:
            Color(*av_bg)
            Ellipse(pos=av.pos, size=av.size)
        av.bind(pos=lambda w, v: self._draw_av(w),
                size=lambda w, v: self._draw_av(w))

        lbl = Label(
            text=text, font_size=sp(14),
            color=C_WHITE if is_user else C_DARK,
            halign="left", valign="top",
            text_size=(Window.width * 0.55, None),
        )
        lbl.bind(texture_size=lbl.setter("size"))

        bc  = C_BLUE if is_user else C_WHITE
        brd = C_BLUE_MUTED if is_user else C_BORDER
        rad = [dp(12), dp(4), dp(12), dp(12)] if is_user \
              else [dp(4), dp(12), dp(12), dp(12)]

        bubble = BoxLayout(size_hint=(None, None), padding=[dp(12), dp(10)])
        lbl.bind(size=lambda w, v: self._upd(bubble, w))
        bubble.add_widget(lbl)

        with bubble.canvas.before:
            Color(*brd)
            RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=rad)
            Color(*bc)
            RoundedRectangle(
                pos=(bubble.x+dp(1), bubble.y+dp(1)),
                size=(max(bubble.width-dp(2), 1),
                      max(bubble.height-dp(2), 1)),
                radius=rad)
        bubble.bind(
            pos=lambda w, v, b=bc, d=brd, r=rad:
                self._draw_bubble(w, b, d, r),
            size=lambda w, v, b=bc, d=brd, r=rad:
                self._draw_bubble(w, b, d, r))

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

    def _draw_av(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_BLUE); Ellipse(pos=w.pos, size=w.size)

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
                size=(max(w.width-dp(2), 1),
                      max(w.height-dp(2), 1)),
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
            RoundedRectangle(pos=logo_box.pos, size=logo_box.size,
                             radius=[dp(8)])
        logo_box.bind(pos=lambda w, v: self._rdraw_logo(w),
                      size=lambda w, v: self._rdraw_logo(w))
        logo_box.add_widget(Label(text="IB", font_size=sp(12), bold=True,
                                  color=C_BLUE,
                                  size_hint=(None, None),
                                  size=(dp(34), dp(34))))
        hdr_t = BoxLayout(orientation="vertical", spacing=dp(1))
        hdr_t.add_widget(Label(text="Ibero Group", font_size=sp(13),
                               bold=True, color=C_WHITE, halign="left",
                               size_hint_y=None, height=dp(22)))
        hdr_t.add_widget(Label(text="Totem ESG", font_size=sp(10),
                               color=get_color_from_hex("#BBDEFB"),
                               halign="left", size_hint_y=None, height=dp(16)))
        hdr.add_widget(logo_box)
        hdr.add_widget(hdr_t)
        hdr.add_widget(Widget())
        st_row = BoxLayout(size_hint=(None, None), size=(dp(80), dp(24)),
                           spacing=dp(4), padding=[dp(8), dp(4)])
        bind_bg(st_row, get_color_from_hex("#1976D2"), radius=12)
        st_dot = Widget(size_hint=(None, None), size=(dp(7), dp(7)))
        with st_dot.canvas:
            Color(*C_GREEN); Ellipse(pos=st_dot.pos, size=st_dot.size)
        st_dot.bind(pos=lambda w, v: self._rdot(w),
                    size=lambda w, v: self._rdot(w))
        st_row.add_widget(st_dot)
        st_row.add_widget(Label(text="Online", font_size=sp(11), color=C_WHITE))
        hdr.add_widget(st_row)
        root.add_widget(hdr)

        # Centro
        center = BoxLayout(orientation="vertical",
                           padding=dp(24), spacing=dp(16))
        bind_bg(center, C_BG)
        center.add_widget(Widget())

        # Card
        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(28), dp(22)], spacing=dp(14))
        with card.canvas.before:
            Color(*C_WHITE)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(18)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(card.x, card.y,
                                    card.width, card.height, dp(18)),
                 width=dp(1))
        card.bind(pos=lambda w, v: self._rdraw_card(w),
                  size=lambda w, v: self._rdraw_card(w))

        icon_row = BoxLayout(size_hint_y=None, height=dp(60))
        icon_box = BoxLayout(size_hint=(None, None), size=(dp(56), dp(56)))
        with icon_box.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=icon_box.pos, size=icon_box.size,
                             radius=[dp(14)])
        icon_box.bind(pos=lambda w, v: self._rdraw_icon(w),
                      size=lambda w, v: self._rdraw_icon(w))
        icon_box.add_widget(Label(text="IB", font_size=sp(20), bold=True,
                                  color=C_WHITE,
                                  size_hint=(None, None),
                                  size=(dp(56), dp(56))))
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

        self.name_disp = Label(
            text="Digite seu nome...",
            font_size=sp(16), color=C_GRAY_LIGHT,
            halign="left", valign="middle",
            size_hint_y=None, height=dp(46))
        name_box = BoxLayout(size_hint_y=None, height=dp(46),
                             padding=[dp(14), dp(8)])
        with name_box.canvas.before:
            Color(*C_BLUE_PALE)
            RoundedRectangle(pos=name_box.pos, size=name_box.size,
                             radius=[dp(10)])
            Color(*C_BLUE_MUTED)
            Line(rounded_rectangle=(name_box.x, name_box.y,
                                    name_box.width, name_box.height, dp(10)),
                 width=dp(1.5))
        name_box.bind(pos=lambda w, v: self._rdraw_nb(w),
                      size=lambda w, v: self._rdraw_nb(w))
        name_box.add_widget(self.name_disp)
        card.add_widget(name_box)

        enter_btn = Btn(
            text="Entrar no Agente ESG",
            bg=C_BLUE, fg=C_WHITE,
            font_size=sp(15), bold=True,
            size_hint_y=None, height=dp(48), r=10)
        enter_btn.bind(on_press=self._confirm)
        card.add_widget(enter_btn)
        card.bind(minimum_height=card.setter("height"))
        center.add_widget(card)

        kb = self._build_keyboard()
        center.add_widget(kb)
        center.add_widget(Widget())
        root.add_widget(center)
        self.add_widget(root)

    def _rdraw_logo(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_WHITE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(8)])

    def _rdot(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_GREEN); Ellipse(pos=w.pos, size=w.size)

    def _rdraw_card(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_WHITE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(18)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(18)),
                 width=dp(1))

    def _rdraw_icon(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(14)])

    def _rdraw_nb(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_BLUE_PALE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])
            Color(*C_BLUE_MUTED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(10)),
                 width=dp(1.5))

    def _build_keyboard(self):
        rows = [list("QWERTYUIOP"),
                list("ASDFGHJKL"),
                list("ZXCVBNM")]
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
        spec = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
        Btn_del = Btn(text="< Del", bg=C_KEY_BG, fg=C_RED,
                      font_size=sp(13), bold=True, r=7,
                      border_color=C_BORDER_MED)
        Btn_del.bind(on_press=lambda b: self._type("DEL"))
        Btn_spc = Btn(text="Espaco", bg=C_KEY_BG, fg=C_GRAY,
                      font_size=sp(13), r=7, border_color=C_BORDER_MED)
        Btn_spc.bind(on_press=lambda b: self._type(" "))
        Btn_ok = Btn(text="OK  >", bg=C_BLUE, fg=C_WHITE,
                     font_size=sp(14), bold=True, r=7)
        Btn_ok.bind(on_press=self._confirm)
        spec.add_widget(Btn_del)
        spec.add_widget(Btn_spc)
        spec.add_widget(Btn_ok)
        kb.add_widget(spec)
        return kb

    def _type(self, k):
        if k == "DEL":
            self._typed = self._typed[:-1]
        else:
            if len(self._typed) < 18:
                self._typed += k
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
#  TELA 2 — CHAT (Gemini + Supabase direto)
# ════════════════════════════════════════════════════════════
class ChatScreen(Screen):
    topic      = StringProperty("ambiental")
    is_loading = BooleanProperty(False)
    history    = ListProperty([])
    quick_list = ListProperty([])
    _knowledge = ""   # cache da base ESG

    def __init__(self, **kw):
        super().__init__(**kw)
        self._built       = False
        self._chat_typed  = ""

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        else:
            self._restart()
        self._load_quick()
        self._load_knowledge()   # carrega base ESG do Supabase

    # ── Carrega base ESG do Supabase ──────────────────────────
    def _load_knowledge(self):
        if not SUPABASE_URL or "SUA_URL" in SUPABASE_URL:
            return
        headers = json.dumps({
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        })
        UrlRequest(
            f"{SUPABASE_URL}/rest/v1/knowledge?select=category,title,content",
            req_headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._set_knowledge(res), 0),
            on_failure=lambda req, res: None,
            on_error=lambda req, err: None,
            timeout=15,
        )

    def _set_knowledge(self, rows):
        if rows:
            kt = ""
            for r in rows:
                kt += f"[{r.get('category','').upper()}] {r.get('title','')}:\n{r.get('content','')}\n\n"
            ChatScreen._knowledge = kt

    # ── Carrega perguntas rápidas do Supabase ─────────────────
    def _load_quick(self):
        if not SUPABASE_URL or "SUA_URL" in SUPABASE_URL:
            self.quick_list = []
            if hasattr(self, "quick_grid"):
                self._render_quick()
            return
        UrlRequest(
            f"{SUPABASE_URL}/rest/v1/quick_questions"
            f"?topic=eq.{self.topic}&select=question&order=id.asc",
            req_headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._set_quick(res), 0),
            on_failure=lambda req, res: None,
            on_error=lambda req, err: None,
            timeout=10,
        )

    def _set_quick(self, data):
        if data:
            self.quick_list = data
            if hasattr(self, "quick_grid"):
                self._render_quick()

    # ── Salva log no Supabase (fire-and-forget) ───────────────
    def _save_log(self, question, answer):
        if not SUPABASE_URL or "SUA_URL" in SUPABASE_URL:
            return
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "operador")
        payload = json.dumps({
            "tablet_id": f"{TABLET_ID}-{name.lower()[:8]}",
            "topic":     self.topic,
            "question":  question,
            "answer":    answer,
        }).encode("utf-8")
        UrlRequest(
            f"{SUPABASE_URL}/rest/v1/logs",
            req_body=payload,
            req_headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "return=minimal",
            },
            on_success=lambda req, res: None,
            on_failure=lambda req, res: None,
            on_error=lambda req, err: None,
            timeout=10,
        )

    # ── Envia mensagem direto para o Gemini ───────────────────
    def send_msg(self, *_):
        text = self._chat_typed.strip()
        if not text or self.is_loading:
            return
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")

        if hasattr(self, "_welcome_wrap") and self._welcome_wrap.parent:
            self.msg_box.remove_widget(self._welcome_wrap)

        self._chat_typed = ""
        self._update_chat_display()
        self.is_loading = True
        self.send_btn.disabled = True

        self._add_bubble(text, is_user=True, initials=name[:2])
        self._typing = self._add_typing()
        self.history.append({"role": "user", "content": text})

        # Monta prompt
        topic_labels = {
            "ambiental": "Indicadores Ambientais",
            "seguranca": "Seguranca e Saude do Trabalho",
            "social":    "Programas Sociais",
            "politicas": "Politicas e Certificacoes",
        }
        topic_label = topic_labels.get(self.topic, self.topic)
        knowledge   = ChatScreen._knowledge

        system_text = (
            f"Voce e o Agente ESG da Ibero Group, simpatico e acolhedor.\n"
            f"Voce esta conversando com {name}, um colaborador da Ibero Group.\n"
            "Responda SEMPRE em portugues brasileiro com linguagem simples e calorosa.\n"
            "Use o nome do colaborador nas respostas.\n"
            "Seja positivo e encorajador. NUNCA use markdown, asteriscos ou hashtags.\n"
            "Escreva em paragrafos simples como se conversasse pessoalmente.\n"
            f"Foco atual: {topic_label}.\n\n"
        )
        if knowledge:
            system_text += f"BASE DE CONHECIMENTO DA EMPRESA:\n{knowledge}\n"
        else:
            system_text += "Use boas praticas gerais de ESG.\n"
        system_text += f"\nSe nao souber, seja honesto e indique o responsavel ESG."

        # Monta conteúdo para Gemini
        contents = []
        for msg in self.history[-8:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role,
                              "parts": [{"text": msg["content"]}]})

        payload = json.dumps({
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 2048,
                "temperature":     0.7,
            },
        }).encode("utf-8")

        UrlRequest(
            GEMINI_URL,
            req_body=payload,
            req_headers={"Content-Type": "application/json"},
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_answer(res, text), 0),
            on_failure=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_error(res), 0),
            on_error=lambda req, err: Clock.schedule_once(
                lambda dt: self._on_error(str(err)), 0),
            timeout=60,
        )

    def _on_answer(self, res, question):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        try:
            raw    = res["candidates"][0]["content"]["parts"][0]["text"]
            answer = clean_md(raw)
        except Exception:
            answer = "Desculpe, nao consegui processar. Tente novamente."
        self._add_bubble(answer, is_user=False)
        self.history.append({"role": "assistant", "content": answer})
        self.is_loading = False
        self.send_btn.disabled = False
        self._set_status("Online", C_GREEN)
        self._save_log(question, answer)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.15)

    def _on_error(self, err=None):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        # Verifica se é erro de rate limit
        err_str = str(err) if err else ""
        if "429" in err_str:
            msg = "Muitas perguntas em pouco tempo. Aguarde 1 minuto e tente novamente."
        else:
            msg = "Sem conexao. Verifique o Wi-Fi e tente novamente."
        self._add_bubble(msg, is_user=False)
        self.is_loading = False
        self.send_btn.disabled = False
        self._set_status("Offline", C_RED)
        # Tenta reconectar em 15s
        Clock.schedule_once(lambda dt: self._ping(), 15)

    def _ping(self):
        UrlRequest(
            "https://generativelanguage.googleapis.com/v1beta/models",
            req_headers={"x-goog-api-key": GEMINI_KEY},
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._set_status("Online", C_GREEN), 0),
            on_failure=lambda req, res: Clock.schedule_once(
                lambda dt: self._ping_retry(), 0),
            on_error=lambda req, err: Clock.schedule_once(
                lambda dt: self._ping_retry(), 0),
            timeout=10,
        )

    def _ping_retry(self):
        Clock.schedule_once(lambda dt: self._ping(), 20)

    # ── Build UI ──────────────────────────────────────────────
    def _build(self):
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")

        root = BoxLayout(orientation="horizontal")
        bind_bg(root, C_BG)

        # Sidebar
        sidebar = BoxLayout(orientation="vertical",
                            size_hint_x=None, width=dp(185),
                            padding=[dp(12), dp(16), dp(12), dp(12)],
                            spacing=dp(4))
        bind_bg(sidebar, C_WHITE)

        logo_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        logo_b = BoxLayout(size_hint=(None, None), size=(dp(36), dp(36)))
        with logo_b.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=logo_b.pos, size=logo_b.size, radius=[dp(9)])
        logo_b.bind(pos=lambda w, v: self._rdraw_lb(w),
                    size=lambda w, v: self._rdraw_lb(w))
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

        div = Widget(size_hint_y=None, height=dp(1))
        bind_bg(div, C_BORDER)
        sidebar.add_widget(div)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(4)))

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
        exit_btn = Btn(text="Sair", bg=C_BG, fg=C_GRAY_LIGHT,
                       font_size=sp(12), r=8, border_color=C_BORDER,
                       size_hint_y=None, height=dp(38))
        exit_btn.bind(on_press=self._exit)
        sidebar.add_widget(exit_btn)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(6)))
        root.add_widget(sidebar)

        # Chat
        right = BoxLayout(orientation="vertical")
        bind_bg(right, C_BG)

        sub = BoxLayout(size_hint_y=None, height=dp(48),
                        padding=[dp(16), 0], spacing=dp(10))
        bind_bg(sub, C_WHITE)
        acc = Widget(size_hint=(None, None), size=(dp(3), dp(32)))
        bind_bg(acc, C_BLUE, radius=2)
        self.header_lbl = Label(
            text="Agente ESG  —  Ambiental",
            font_size=sp(14), bold=True, color=C_DARK, halign="left")
        sub.add_widget(acc)
        sub.add_widget(self.header_lbl)
        st_box = BoxLayout(size_hint=(None, None), size=(dp(80), dp(26)),
                           spacing=dp(4), padding=[dp(8), dp(4)])
        bind_bg(st_box, C_BG, radius=13)
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

        sep = Widget(size_hint_y=None, height=dp(1))
        bind_bg(sep, C_BORDER)
        right.add_widget(sep)

        self.scroll = ScrollView(do_scroll_x=False)
        self.msg_box = BoxLayout(
            orientation="vertical", size_hint_y=None,
            spacing=dp(10), padding=[dp(14), dp(14)])
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        self.scroll.add_widget(self.msg_box)
        right.add_widget(self.scroll)

        # Barra de input (sem TextInput nativo)
        inp_sep = Widget(size_hint_y=None, height=dp(1))
        bind_bg(inp_sep, C_BORDER)
        right.add_widget(inp_sep)

        inp_bar = BoxLayout(size_hint_y=None, height=dp(54),
                            padding=[dp(12), dp(8)], spacing=dp(10))
        bind_bg(inp_bar, C_WHITE)

        self.chat_display = Label(
            text=f"Ola {name}, o que deseja saber?",
            font_size=sp(13), color=C_GRAY_LIGHT,
            halign="left", valign="middle", size_hint_x=1)
        disp_box = BoxLayout(padding=[dp(12), dp(6)])
        with disp_box.canvas.before:
            Color(*C_BG)
            RoundedRectangle(pos=disp_box.pos, size=disp_box.size,
                             radius=[dp(10)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(disp_box.x, disp_box.y,
                                    disp_box.width, disp_box.height, dp(10)),
                 width=dp(1.5))
        disp_box.bind(pos=lambda w, v: self._rdraw_disp(w),
                      size=lambda w, v: self._rdraw_disp(w))
        disp_box.add_widget(self.chat_display)

        self.send_btn = Btn(text=">", bg=C_BLUE, fg=C_WHITE,
                            font_size=sp(20), bold=True,
                            size_hint_x=None, width=dp(50), r=10)
        self.send_btn.bind(on_press=self.send_msg)

        inp_bar.add_widget(disp_box)
        inp_bar.add_widget(self.send_btn)
        right.add_widget(inp_bar)

        # Teclado virtual proprio
        chat_kb = self._build_chat_keyboard(name)
        right.add_widget(chat_kb)
        root.add_widget(right)
        self.add_widget(root)
        self._show_welcome()

    def _rdraw_lb(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(9)])

    def _rdraw_disp(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_BG)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(10)),
                 width=dp(1.5))

    def _draw_dot(self, w, color):
        w.canvas.clear()
        with w.canvas:
            Color(*color); Ellipse(pos=w.pos, size=w.size)

    def _build_chat_keyboard(self, name):
        rows = [list("QWERTYUIOP"),
                list("ASDFGHJKL"),
                list("ZXCVBNM")]
        kb = BoxLayout(orientation="vertical",
                       size_hint_y=None, height=dp(162), spacing=dp(3),
                       padding=[dp(8), dp(4)])
        bind_bg(kb, C_WHITE)
        for row in rows:
            rbox = BoxLayout(spacing=dp(3), size_hint_y=None, height=dp(38))
            for k in row:
                btn = Btn(text=k, bg=C_KEY_BG, fg=C_DARK,
                          font_size=sp(13), bold=True, r=6,
                          border_color=C_BORDER_MED)
                btn.bind(on_press=lambda b, k=k: self._chat_type(k))
                rbox.add_widget(btn)
            kb.add_widget(rbox)
        spec = BoxLayout(spacing=dp(3), size_hint_y=None, height=dp(38),
                         padding=[dp(4), 0])
        Btn_del = Btn(text="< Del", bg=C_KEY_BG, fg=C_RED,
                      font_size=sp(12), bold=True, r=6,
                      border_color=C_BORDER_MED)
        Btn_del.bind(on_press=lambda b: self._chat_type("DEL"))
        Btn_spc = Btn(text="Espaco", bg=C_KEY_BG, fg=C_GRAY,
                      font_size=sp(12), r=6, border_color=C_BORDER_MED)
        Btn_spc.bind(on_press=lambda b: self._chat_type(" "))
        Btn_env = Btn(text="Enviar >", bg=C_BLUE, fg=C_WHITE,
                      font_size=sp(13), bold=True, r=6)
        Btn_env.bind(on_press=self.send_msg)
        spec.add_widget(Btn_del)
        spec.add_widget(Btn_spc)
        spec.add_widget(Btn_env)
        kb.add_widget(spec)
        return kb

    def _chat_type(self, k):
        if k == "DEL":
            self._chat_typed = self._chat_typed[:-1]
        else:
            if len(self._chat_typed) < 120:
                self._chat_typed += k
        self._update_chat_display()

    def _update_chat_display(self):
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")
        if self._chat_typed:
            self.chat_display.text  = self._chat_typed
            self.chat_display.color = C_DARK
        else:
            self.chat_display.text  = f"Ola {name}, o que deseja saber?"
            self.chat_display.color = C_GRAY_LIGHT

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
        bd.bind(pos=lambda w, v, c=meta["color"]: self._rdraw_badge(w, c),
                size=lambda w, v, c=meta["color"]: self._rdraw_badge(w, c))
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

    def _rdraw_badge(self, w, c):
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
        card.bind(pos=lambda w, v: self._rdraw_wcard(w),
                  size=lambda w, v: self._rdraw_wcard(w))
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

    def _rdraw_wcard(self, w):
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
                      font_size=sp(12), size_hint_y=None, height=dp(50),
                      r=8, border_color=C_BORDER_MED)
            btn.bind(on_press=lambda b, q=text: self._prefill(q))
            self.quick_grid.add_widget(btn)

    def _prefill(self, q):
        self._chat_typed = q
        self._update_chat_display()
        self.send_msg()

    def _add_bubble(self, text, is_user=False, initials="IB"):
        b = Bubble(text=text, is_user=is_user, initials=initials)
        self.msg_box.add_widget(b)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return b

    def _add_typing(self):
        lbl = Label(text="Agente digitando...",
                    font_size=sp(13), color=C_BLUE,
                    size_hint_y=None, height=dp(30), halign="left")
        self.msg_box.add_widget(lbl)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return lbl

    def _scroll_end(self):
        self.scroll.scroll_y = 0

    def _set_status(self, text, color):
        self.st_lbl.text  = text
        self.st_lbl.color = color
        self._draw_dot(self.st_dot, color)

    def _exit(self, *_):
        self.manager.current = "welcome"

    def _restart(self):
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")
        if hasattr(self, "greet_lbl"):
            self.greet_lbl.text = f"Ola, {name}!"
        self._chat_typed = ""
        self._update_chat_display()
        self.history.clear()
        self._show_welcome()
        self._load_quick()
        self._load_knowledge()


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
