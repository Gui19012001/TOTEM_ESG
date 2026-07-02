"""
Totem ESG — Ibero Group v6.0
Novidades: +2 temas, Quiz colorido, inatividade, perguntas rapidas por tema,
           reconhecimento de voz via Android SpeechRecognizer
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

# ── Configuração ──────────────────────────────────────────────
GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "SUA_CHAVE_GEMINI_AQUI").strip()
SUPABASE_URL = os.environ.get("SUPABASE_URL",   "SUA_URL_SUPABASE_AQUI").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY",   "SUA_KEY_SUPABASE_AQUI").strip()
TABLET_ID    = os.environ.get("TABLET_ID",      "totem-ibero-01").strip()

GEMINI_MODELS       = ("gemini-1.5-flash", "gemini-2.5-flash")
GEMINI_RETRY_DELAYS = (2, 5)
INACTIVITY_TIMEOUT  = 120   # segundos sem interação → volta ao inicio

def gemini_url(model):
    return (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )

# ── Paleta ────────────────────────────────────────────────────
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

# ── Temas (6) ────────────────────────────────────────────────
TOPICS = {
    "ambiental": {
        "label": "Ambiental", "code": "AMB",
        "color":      get_color_from_hex("#0F6E56"),
        "color_pale": get_color_from_hex("#E1F5EE"),
        "qs": ["Qual e a meta de reducao de CO2?",
               "Como esta o consumo de agua?",
               "Quanto residuo reciclamos?"],
    },
    "seguranca": {
        "label": "Seguranca", "code": "SST",
        "color":      get_color_from_hex("#854F0B"),
        "color_pale": get_color_from_hex("#FAEEDA"),
        "qs": ["Quantos dias sem acidentes?",
               "Quais EPIs devo usar?",
               "O que fazer em emergencia?"],
    },
    "social": {
        "label": "Social", "code": "SOC",
        "color":      get_color_from_hex("#3C3489"),
        "color_pale": get_color_from_hex("#EEEDFE"),
        "qs": ["Quais programas sociais temos?",
               "Como participar de treinamentos?",
               "Quais sao as metas sociais?"],
    },
    "politicas": {
        "label": "Politicas", "code": "POL",
        "color":      get_color_from_hex("#185FA5"),
        "color_pale": get_color_from_hex("#E6F1FB"),
        "qs": ["O que diz a politica integrada?",
               "Quais sao nossas certificacoes?",
               "Como reportar um problema?"],
    },
    "pessoas": {
        "label": "Pessoas", "code": "DP",
        "color":      get_color_from_hex("#993556"),
        "color_pale": get_color_from_hex("#FBEAF0"),
        "qs": ["Quais beneficios temos?",
               "Como funciona a avaliacao de desempenho?",
               "Como acesso o plano de saude?"],
    },
    "processos": {
        "label": "Eng. Processos", "code": "EP",
        "color":      get_color_from_hex("#444441"),
        "color_pale": get_color_from_hex("#F1EFE8"),
        "qs": ["Quais processos estao certificados?",
               "Como reportar melhoria de processo?",
               "Quais sao os indicadores de qualidade?"],
    },
}

# ── Banco de perguntas do Quiz ────────────────────────────────
QUIZ_DATA = {
    "ambiental": [
        {"q": "O que a Ibero Group se compromete a reduzir?",
         "a": ["Consumo de agua, energia e residuos", "Apenas emissoes de CO2", "Numero de fornecedores"], "correct": "Consumo de agua, energia e residuos"},
        {"q": "Qual norma rege a gestao ambiental na Ibero Group?",
         "a": ["ISO 9001", "ISO 45001", "ISO 14001"], "correct": "ISO 14001"},
        {"q": "Proteger o meio ambiente e prevenir a poluicao sao compromissos:",
         "a": ["Apenas da lideranca", "Da Politica Integrada Ibero", "Do governo federal"], "correct": "Da Politica Integrada Ibero"},
        {"q": "Crescimento com sustentabilidade e um:",
         "a": ["Custo operacional elevado", "Valor da Ibero Group", "Projeto de longo prazo"], "correct": "Valor da Ibero Group"},
        {"q": "Reduzir residuos solidos contribui para:",
         "a": ["Protecao ambiental e sustentabilidade", "Apenas reducao de custos", "Aumento da producao"], "correct": "Protecao ambiental e sustentabilidade"},
        {"q": "A Ibero Group monitora indicadores ambientais para:",
         "a": ["Cumprir exigencias legais apenas", "Melhorar continuamente e reduzir impactos", "Apresentar relatorios externos"], "correct": "Melhorar continuamente e reduzir impactos"},
        {"q": "Economizar energia eletrica na fabrica ajuda a:",
         "a": ["Reduzir impacto ambiental e custos", "Aumentar a producao", "Diminuir a qualidade"], "correct": "Reduzir impacto ambiental e custos"},
        {"q": "Reciclar materiais na industria significa:",
         "a": ["Descartar tudo no lixo comum", "Reaproveitar e reduzir residuos", "Queimar os residuos"], "correct": "Reaproveitar e reduzir residuos"},
    ],
    "seguranca": [
        {"q": "EPI significa:",
         "a": ["Equipamento de Protecao Industrial", "Equipamento de Protecao Individual", "Exame Periodico Interno"], "correct": "Equipamento de Protecao Individual"},
        {"q": "A ISO 45001 trata de:",
         "a": ["Qualidade do produto", "Saude e seguranca no trabalho", "Gestao ambiental"], "correct": "Saude e seguranca no trabalho"},
        {"q": "Ao identificar um risco de acidente, voce deve:",
         "a": ["Ignorar e continuar trabalhando", "Aguardar alguem reportar", "Comunicar ao responsavel imediatamente"], "correct": "Comunicar ao responsavel imediatamente"},
        {"q": "Dias sem acidente e conquista:",
         "a": ["Apenas da lideranca", "De toda a equipe", "Do departamento de seguranca"], "correct": "De toda a equipe"},
        {"q": "Ao ver um colega sem EPI, o correto e:",
         "a": ["Ignorar, nao e sua responsabilidade", "Orientar e reportar ao responsavel", "Esperar a supervisao agir"], "correct": "Orientar e reportar ao responsavel"},
        {"q": "Uma analise de risco serve para:",
         "a": ["Punir trabalhadores", "Identificar e prevenir acidentes", "Aumentar a produtividade"], "correct": "Identificar e prevenir acidentes"},
        {"q": "Em caso de acidente, o primeiro passo e:",
         "a": ["Continuar a atividade", "Prestar socorro e acionar a emergencia", "Aguardar o turno terminar"], "correct": "Prestar socorro e acionar a emergencia"},
        {"q": "Usar o EPI corretamente e responsabilidade:",
         "a": ["Somente da empresa", "De cada colaborador", "Apenas do setor de seguranca"], "correct": "De cada colaborador"},
    ],
    "social": [
        {"q": "O primeiro valor da Ibero Group e:",
         "a": ["Crescimento com sustentabilidade", "Nossa gente e nossa forca", "Todos pelo cliente"], "correct": "Nossa gente e nossa forca"},
        {"q": "Capacitar colaboradores contribui para:",
         "a": ["Apenas reducao de custos", "Melhoria continua e desenvolvimento", "Aumento das horas extras"], "correct": "Melhoria continua e desenvolvimento"},
        {"q": "Confianca nas relacoes e:",
         "a": ["Um valor da Ibero Group", "Uma meta de vendas", "Uma diretriz de RH"], "correct": "Um valor da Ibero Group"},
        {"q": "Um bom programa social comeca com:",
         "a": ["Beneficios financeiros", "Respeito e valorizacao das pessoas", "Plano de carreira"], "correct": "Respeito e valorizacao das pessoas"},
        {"q": "Comprometimento com o resultado significa:",
         "a": ["Trabalhar mais horas", "Entregar com qualidade e responsabilidade", "Aumentar metas sozinho"], "correct": "Entregar com qualidade e responsabilidade"},
        {"q": "Diversidade e inclusao no trabalho:",
         "a": ["Nao afetam resultados", "Fortalecem a equipe e a inovacao", "Sao obrigacoes legais apenas"], "correct": "Fortalecem a equipe e a inovacao"},
        {"q": "O valor 'Todos pelo cliente' significa:",
         "a": ["Focar apenas em vendas", "Toda a equipe unida pela satisfacao do cliente", "Somente o comercial atende clientes"], "correct": "Toda a equipe unida pela satisfacao do cliente"},
    ],
    "politicas": [
        {"q": "A missao da Ibero Group e fornecer:",
         "a": ["Alimentos industriais", "Sistemas de suspensoes, eixos e acoplamentos", "Software de gestao"], "correct": "Sistemas de suspensoes, eixos e acoplamentos"},
        {"q": "A Politica Integrada busca:",
         "a": ["Resultado sustentavel para o negocio", "Crescimento a qualquer custo", "Reducao do portfolio"], "correct": "Resultado sustentavel para o negocio"},
        {"q": "Atender requisitos legais e:",
         "a": ["Opcional para empresas privadas", "Compromisso da Politica Integrada", "Responsabilidade so da diretoria"], "correct": "Compromisso da Politica Integrada"},
        {"q": "A visao da Ibero Group e ser reconhecida como:",
         "a": ["Maior empresa do Brasil", "Referencia global em produtos e relacoes duraveis", "Lider em exportacoes"], "correct": "Referencia global em produtos e relacoes duraveis"},
        {"q": "Melhorar a satisfacao do cliente e objetivo:",
         "a": ["Apenas do comercial", "Do sistema de gestao da qualidade", "Somente da assistencia tecnica"], "correct": "Do sistema de gestao da qualidade"},
        {"q": "Reduzir o retrabalho contribui para:",
         "a": ["Apenas corte de custos", "Eficiencia dos processos e qualidade", "Reducao da equipe"], "correct": "Eficiencia dos processos e qualidade"},
        {"q": "As certificacoes ISO da Ibero garantem:",
         "a": ["Apenas marketing", "Qualidade, seguranca e gestao ambiental", "Aumento de precos"], "correct": "Qualidade, seguranca e gestao ambiental"},
    ],
    "pessoas": [
        {"q": "O Departamento de Pessoas e responsavel por:",
         "a": ["Controle de qualidade", "Gestao de beneficios e desenvolvimento", "Manutencao de equipamentos"], "correct": "Gestao de beneficios e desenvolvimento"},
        {"q": "A avaliacao de desempenho serve para:",
         "a": ["Punir colaboradores", "Mapear crescimento e desenvolvimento", "Reduzir salarios"], "correct": "Mapear crescimento e desenvolvimento"},
        {"q": "Um ambiente de trabalho saudavel depende:",
         "a": ["Somente da lideranca", "De todos os colaboradores", "Apenas do RH"], "correct": "De todos os colaboradores"},
        {"q": "A integracao de novos colaboradores ajuda a:",
         "a": ["Aumentar a burocracia", "Acelerar a adaptacao e produtividade", "Reduzir responsabilidades"], "correct": "Acelerar a adaptacao e produtividade"},
        {"q": "O feedback no trabalho serve para:",
         "a": ["Criticar o desempenho", "Orientar e desenvolver colaboradores", "Justificar demissoes"], "correct": "Orientar e desenvolver colaboradores"},
        {"q": "Um plano de carreira estruturado beneficia:",
         "a": ["Apenas a empresa", "O colaborador e a empresa", "Somente o RH"], "correct": "O colaborador e a empresa"},
        {"q": "Investir em treinamento dos colaboradores:",
         "a": ["E gasto desnecessario", "Melhora resultados e engajamento", "So beneficia a lideranca"], "correct": "Melhora resultados e engajamento"},
    ],
    "processos": [
        {"q": "A Engenharia de Processos busca principalmente:",
         "a": ["Aumentar o numero de etapas", "Melhorar eficiencia e reduzir retrabalho", "Manter processos iguais"], "correct": "Melhorar eficiencia e reduzir retrabalho"},
        {"q": "Indicadores de qualidade servem para:",
         "a": ["Cumprir normas apenas", "Monitorar e melhorar continuamente", "Aumentar a burocracia"], "correct": "Monitorar e melhorar continuamente"},
        {"q": "Uma melhoria de processo deve ser:",
         "a": ["Implementada sem aviso previo", "Comunicada ao responsavel pela area", "Mantida em sigilo"], "correct": "Comunicada ao responsavel pela area"},
        {"q": "Kaizen significa:",
         "a": ["Parar e reiniciar processos", "Melhoria continua e gradual", "Aumentar a velocidade"], "correct": "Melhoria continua e gradual"},
        {"q": "O mapeamento de processos serve para:",
         "a": ["Aumentar reunioes", "Visualizar e identificar ineficiencias", "Reduzir funcionarios"], "correct": "Visualizar e identificar ineficiencias"},
        {"q": "A padronizacao de processos garante:",
         "a": ["Menos autonomia", "Consistencia e qualidade nos resultados", "Aumento de custo"], "correct": "Consistencia e qualidade nos resultados"},
        {"q": "Reduzir desperdicios no processo produtivo:",
         "a": ["Diminui a qualidade", "Aumenta eficiencia e sustentabilidade", "Atrasa a producao"], "correct": "Aumenta eficiencia e sustentabilidade"},
    ],
}

# ── Helpers ───────────────────────────────────────────────────
def clean_md(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'#{1,6}\s*',     '',    text)
    text = re.sub(r'^\s*[\*\-]\s+', '- ',  text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def api_error_detail(response):
    try:
        if isinstance(response, dict):
            error = response.get("error", response)
            if isinstance(error, dict):
                return str(error.get("message") or error.get("status") or "").strip()
            return str(error).strip()
        if isinstance(response, (bytes, bytearray)):
            response = response.decode("utf-8", errors="replace")
        if isinstance(response, str):
            try:
                return api_error_detail(json.loads(response))
            except Exception:
                return response.strip()
    except Exception:
        pass
    return ""

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

# ── Botão ─────────────────────────────────────────────────────
class Btn(Button):
    def __init__(self, bg=None, fg=None, r=8, border_color=None, **kw):
        super().__init__(**kw)
        self._bg = bg or C_BLUE
        self._fg = fg or C_WHITE
        self._r  = r
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

# ── Bolha ─────────────────────────────────────────────────────
class Bubble(BoxLayout):
    def __init__(self, text, is_user=False, initials="IB", **kw):
        super().__init__(orientation="vertical",
                         size_hint_y=None, padding=[dp(4), dp(2)], **kw)
        self.is_user = is_user
        row = BoxLayout(size_hint_y=None, spacing=dp(8))
        av_txt = initials[:2].upper() if is_user else "IB"
        av = Label(text=av_txt, font_size=sp(10), bold=True, color=C_WHITE,
                   size_hint=(None, None), size=(dp(32), dp(32)))
        with av.canvas.before:
            Color(*C_BLUE); Ellipse(pos=av.pos, size=av.size)
        av.bind(pos=lambda w, v: self._draw_av(w),
                size=lambda w, v: self._draw_av(w))
        lbl = Label(text=text, font_size=sp(14),
                    color=C_WHITE if is_user else C_DARK,
                    halign="left", valign="top",
                    text_size=(Window.width * 0.55, None))
        lbl.bind(texture_size=lbl.setter("size"))
        bc  = C_BLUE if is_user else C_WHITE
        brd = C_BLUE_MUTED if is_user else C_BORDER
        rad = [dp(12), dp(4), dp(12), dp(12)] if is_user \
              else [dp(4), dp(12), dp(12), dp(12)]
        bubble = BoxLayout(size_hint=(None, None), padding=[dp(12), dp(10)])
        lbl.bind(size=lambda w, v: self._upd(bubble, w))
        bubble.add_widget(lbl)
        with bubble.canvas.before:
            Color(*brd); RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=rad)
            Color(*bc)
            RoundedRectangle(pos=(bubble.x+dp(1), bubble.y+dp(1)),
                             size=(max(bubble.width-dp(2), 1), max(bubble.height-dp(2), 1)),
                             radius=rad)
        bubble.bind(
            pos=lambda w, v, b=bc, d=brd, r=rad: self._draw_bubble(w, b, d, r),
            size=lambda w, v, b=bc, d=brd, r=rad: self._draw_bubble(w, b, d, r))
        if is_user:
            row.add_widget(Widget()); row.add_widget(bubble); row.add_widget(av)
        else:
            row.add_widget(av); row.add_widget(bubble); row.add_widget(Widget())
        row.size_hint_y = None
        row.bind(minimum_height=row.setter("height"))
        self.add_widget(row); self._row = row
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
            Color(*brd); RoundedRectangle(pos=w.pos, size=w.size, radius=rad)
            Color(*bc)
            RoundedRectangle(pos=(w.x+dp(1), w.y+dp(1)),
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
        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(52),
                        padding=[dp(18), 0], spacing=dp(12))
        bind_bg(hdr, C_BLUE)
        logo_box = BoxLayout(size_hint=(None, None), size=(dp(34), dp(34)))
        with logo_box.canvas:
            Color(*C_WHITE)
            RoundedRectangle(pos=logo_box.pos, size=logo_box.size, radius=[dp(8)])
        logo_box.bind(pos=lambda w, v: self._rdraw_logo(w),
                      size=lambda w, v: self._rdraw_logo(w))
        logo_box.add_widget(Label(text="IB", font_size=sp(12), bold=True,
                                  color=C_BLUE, size_hint=(None, None),
                                  size=(dp(34), dp(34))))
        hdr_t = BoxLayout(orientation="vertical", spacing=dp(1))
        hdr_t.add_widget(Label(text="Ibero Group", font_size=sp(13), bold=True,
                               color=C_WHITE, halign="left",
                               size_hint_y=None, height=dp(22)))
        hdr_t.add_widget(Label(text="Totem ESG", font_size=sp(10),
                               color=get_color_from_hex("#BBDEFB"),
                               halign="left", size_hint_y=None, height=dp(16)))
        hdr.add_widget(logo_box); hdr.add_widget(hdr_t); hdr.add_widget(Widget())
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
        center = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(16))
        bind_bg(center, C_BG)
        center.add_widget(Widget())
        # Card
        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(28), dp(22)], spacing=dp(14))
        with card.canvas.before:
            Color(*C_WHITE)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(18)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(18)),
                 width=dp(1))
        card.bind(pos=lambda w, v: self._rdraw_card(w),
                  size=lambda w, v: self._rdraw_card(w))
        icon_row = BoxLayout(size_hint_y=None, height=dp(60))
        icon_box = BoxLayout(size_hint=(None, None), size=(dp(56), dp(56)))
        with icon_box.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=icon_box.pos, size=icon_box.size, radius=[dp(14)])
        icon_box.bind(pos=lambda w, v: self._rdraw_icon(w),
                      size=lambda w, v: self._rdraw_icon(w))
        icon_box.add_widget(Label(text="IB", font_size=sp(20), bold=True,
                                  color=C_WHITE, size_hint=(None, None),
                                  size=(dp(56), dp(56))))
        icon_row.add_widget(Widget()); icon_row.add_widget(icon_box); icon_row.add_widget(Widget())
        card.add_widget(icon_row)
        card.add_widget(Label(text="Ola! Sou o Agente ESG", font_size=sp(20),
                              bold=True, color=C_DARK, halign="center",
                              size_hint_y=None, height=dp(32)))
        card.add_widget(Label(text="da Ibero Group", font_size=sp(14),
                              color=C_BLUE, halign="center",
                              size_hint_y=None, height=dp(22)))
        card.add_widget(Label(text="Como voce se chama?", font_size=sp(14),
                              color=C_GRAY, halign="center",
                              size_hint_y=None, height=dp(22)))
        self.name_disp = Label(text="Digite seu nome...", font_size=sp(16),
                               color=C_GRAY_LIGHT, halign="left", valign="middle",
                               size_hint_y=None, height=dp(46))
        name_box = BoxLayout(size_hint_y=None, height=dp(46), padding=[dp(14), dp(8)])
        with name_box.canvas.before:
            Color(*C_BLUE_PALE)
            RoundedRectangle(pos=name_box.pos, size=name_box.size, radius=[dp(10)])
            Color(*C_BLUE_MUTED)
            Line(rounded_rectangle=(name_box.x, name_box.y,
                                    name_box.width, name_box.height, dp(10)),
                 width=dp(1.5))
        name_box.bind(pos=lambda w, v: self._rdraw_nb(w),
                      size=lambda w, v: self._rdraw_nb(w))
        name_box.add_widget(self.name_disp)
        card.add_widget(name_box)
        enter_btn = Btn(text="Entrar no Agente ESG", bg=C_BLUE, fg=C_WHITE,
                        font_size=sp(15), bold=True, size_hint_y=None,
                        height=dp(48), r=10)
        enter_btn.bind(on_press=self._confirm)
        card.add_widget(enter_btn)
        card.bind(minimum_height=card.setter("height"))
        center.add_widget(card)
        center.add_widget(self._build_keyboard())
        center.add_widget(Widget())
        root.add_widget(center)
        self.add_widget(root)

    def _rdraw_logo(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_WHITE); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(8)])

    def _rdot(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_GREEN); Ellipse(pos=w.pos, size=w.size)

    def _rdraw_card(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_WHITE); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(18)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(18)), width=dp(1))

    def _rdraw_icon(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(14)])

    def _rdraw_nb(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_BLUE_PALE); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])
            Color(*C_BLUE_MUTED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(10)), width=dp(1.5))

    def _build_keyboard(self):
        rows = [list("QWERTYUIOP"), list("ASDFGHJKL"), list("ZXCVBNM")]
        kb = BoxLayout(orientation="vertical", size_hint_y=None,
                       height=dp(178), spacing=dp(4))
        for row in rows:
            rbox = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
            for k in row:
                btn = Btn(text=k, bg=C_KEY_BG, fg=C_DARK, font_size=sp(14),
                          bold=True, r=7, border_color=C_BORDER_MED)
                btn.bind(on_press=lambda b, k=k: self._type(k))
                rbox.add_widget(btn)
            kb.add_widget(rbox)
        spec = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(40))
        bd = Btn(text="< Del", bg=C_KEY_BG, fg=C_RED, font_size=sp(13),
                 bold=True, r=7, border_color=C_BORDER_MED)
        bd.bind(on_press=lambda b: self._type("DEL"))
        bs = Btn(text="Espaco", bg=C_KEY_BG, fg=C_GRAY, font_size=sp(13),
                 r=7, border_color=C_BORDER_MED)
        bs.bind(on_press=lambda b: self._type(" "))
        bo = Btn(text="OK  >", bg=C_BLUE, fg=C_WHITE, font_size=sp(14),
                 bold=True, r=7)
        bo.bind(on_press=self._confirm)
        spec.add_widget(bd); spec.add_widget(bs); spec.add_widget(bo)
        kb.add_widget(spec)
        return kb

    def _type(self, k):
        if k == "DEL":
            self._typed = self._typed[:-1]
        else:
            if len(self._typed) < 18:
                self._typed += k
        if self._typed:
            self.name_disp.text = self._typed; self.name_disp.color = C_DARK
        else:
            self.name_disp.text = "Digite seu nome..."; self.name_disp.color = C_GRAY_LIGHT

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
    _knowledge = ""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._built      = False
        self._chat_typed = ""
        self._typing     = None
        self._last_failed_question = ""
        self._inact_ev   = None
        self._listening  = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        else:
            self._restart()
        self._load_quick()
        self._load_knowledge()
        Clock.schedule_once(lambda dt: self._ping_internet(), 0.5)
        self._reset_inactivity()

    # ── Inatividade ───────────────────────────────────────────
    def _reset_inactivity(self):
        if self._inact_ev:
            self._inact_ev.cancel()
        self._inact_ev = Clock.schedule_once(
            lambda dt: self._on_inactivity(), INACTIVITY_TIMEOUT)

    def _on_inactivity(self):
        if not self.is_loading:
            self.manager.current = "welcome"

    # ── Supabase: knowledge ───────────────────────────────────
    def _load_knowledge(self):
        if not SUPABASE_URL or "SUA_URL" in SUPABASE_URL:
            return
        UrlRequest(
            f"{SUPABASE_URL}/rest/v1/knowledge?select=category,title,content",
            req_headers={"apikey": SUPABASE_KEY,
                         "Authorization": f"Bearer {SUPABASE_KEY}"},
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._set_knowledge(res), 0),
            on_failure=lambda req, res: None,
            on_error=lambda req, err: None,
            timeout=15)

    def _set_knowledge(self, rows):
        if rows:
            kt = ""
            for r in rows:
                kt += f"[{r.get('category','').upper()}] {r.get('title','')}:\n{r.get('content','')}\n\n"
            ChatScreen._knowledge = kt

    # ── Supabase: quick questions ─────────────────────────────
    def _load_quick(self):
        if not SUPABASE_URL or "SUA_URL" in SUPABASE_URL:
            self.quick_list = []
            return
        UrlRequest(
            f"{SUPABASE_URL}/rest/v1/quick_questions"
            f"?topic=eq.{self.topic}&select=question&order=id.asc",
            req_headers={"apikey": SUPABASE_KEY,
                         "Authorization": f"Bearer {SUPABASE_KEY}"},
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._set_quick(res), 0),
            on_failure=lambda req, res: None,
            on_error=lambda req, err: None,
            timeout=10)

    def _set_quick(self, data):
        if data:
            self.quick_list = data
            if hasattr(self, "quick_grid"):
                self._render_quick()

    # ── Supabase: log ─────────────────────────────────────────
    def _save_log(self, question, answer):
        if not SUPABASE_URL or "SUA_URL" in SUPABASE_URL:
            return
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "operador")
        payload = json.dumps({"tablet_id": f"{TABLET_ID}-{name.lower()[:8]}",
                              "topic": self.topic,
                              "question": question, "answer": answer}).encode()
        UrlRequest(
            f"{SUPABASE_URL}/rest/v1/logs",
            req_body=payload,
            req_headers={"apikey": SUPABASE_KEY,
                         "Authorization": f"Bearer {SUPABASE_KEY}",
                         "Content-Type": "application/json",
                         "Prefer": "return=minimal"},
            on_success=lambda req, res: None,
            on_failure=lambda req, res: None,
            on_error=lambda req, err: None,
            timeout=10)

    # ── Reconhecimento de voz (Android) ──────────────────────
    def _start_voice(self, *_):
        """Abre o reconhecimento de voz do Android via Intent (pt-BR)."""
        self._reset_inactivity()
        try:
            from jnius import autoclass, cast
            from android import activity  # fornecido pelo python-for-android

            Intent           = autoclass("android.content.Intent")
            RecognizerIntent = autoclass("android.speech.RecognizerIntent")
            PythonActivity   = autoclass("org.kivy.android.PythonActivity")
            current_activity = cast(
                "android.app.Activity", PythonActivity.mActivity)

            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT,
                            "Fale sua pergunta...")
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)

            self._SPEECH_REQUEST = 1001
            self._RecognizerIntent = RecognizerIntent

            # Registra callback do resultado
            activity.bind(on_activity_result=self._on_speech_activity_result)

            self._listening = True
            self._set_status("Ouvindo...", C_BLUE)
            self.mic_btn._bg = get_color_from_hex("#E53935")
            self.mic_btn._fg = C_WHITE
            self.mic_btn.text = "Ouvindo"
            self.mic_btn._draw()

            current_activity.startActivityForResult(
                intent, self._SPEECH_REQUEST)

        except Exception as e:
            print(f"Erro voz: {e}")
            self._reset_mic()
            self._add_bubble(
                "O reconhecimento de voz nao esta disponivel. "
                "Use o teclado para digitar sua pergunta.",
                is_user=False)

    def _on_speech_activity_result(self, request_code, result_code, intent):
        """Recebe o texto reconhecido pelo Android."""
        try:
            from jnius import autoclass
            Activity = autoclass("android.app.Activity")
            if request_code == getattr(self, "_SPEECH_REQUEST", 1001):
                if result_code == Activity.RESULT_OK and intent is not None:
                    results = intent.getStringArrayListExtra(
                        self._RecognizerIntent.EXTRA_RESULTS)
                    if results and results.size() > 0:
                        text = results.get(0)
                        Clock.schedule_once(
                            lambda dt: self._on_voice_result(text), 0)
                        return
                Clock.schedule_once(lambda dt: self._on_voice_error(), 0)
        except Exception as e:
            print(f"Erro resultado voz: {e}")
            Clock.schedule_once(lambda dt: self._on_voice_error(), 0)

    def _reset_mic(self):
        self._listening = False
        self._set_status("Online", C_GREEN)
        if hasattr(self, "mic_btn"):
            self.mic_btn._bg   = C_BLUE_PALE
            self.mic_btn._fg   = C_BLUE
            self.mic_btn.color = C_BLUE
            self.mic_btn.text  = "Falar"
            self.mic_btn._draw()

    def _on_voice_result(self, text):
        self._reset_mic()
        if text and text.strip():
            self._chat_typed = text.strip()[:120]
            self._update_chat_display()
            self.send_msg()

    def _on_voice_error(self):
        self._reset_mic()
        self._add_bubble(
            "Nao entendi o que voce falou. Tente novamente ou use o teclado.",
            is_user=False)

    # ── Envio de mensagem ─────────────────────────────────────
    def send_msg(self, *_):
        self._reset_inactivity()
        text = self._chat_typed.strip()
        if not text or self.is_loading:
            return
        if not GEMINI_KEY or "SUA_CHAVE_GEMINI" in GEMINI_KEY:
            self._add_bubble(
                "A chave da IA nao foi incluida neste APK. Gere um novo APK.",
                is_user=False)
            self._set_status("Configuracao", C_RED)
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

        topic_labels = {
            "ambiental": "Indicadores Ambientais",
            "seguranca": "Seguranca e Saude do Trabalho",
            "social":    "Programas Sociais",
            "politicas": "Politicas e Certificacoes",
            "pessoas":   "Departamento de Pessoas e RH",
            "processos": "Engenharia de Processos e Qualidade",
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
        system_text += f"\nSe nao souber, seja honesto com {name} e indique o responsavel ESG."

        contents = []
        for msg in self.history[-8:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        payload = json.dumps({
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 700, "temperature": 0.6},
        }).encode("utf-8")
        self._send_gemini_request(text, payload, 0, 0)

    def _send_gemini_request(self, question, payload, model_index=0, retry_index=0):
        model_index = max(0, min(model_index, len(GEMINI_MODELS)-1))
        model = GEMINI_MODELS[model_index]
        self._set_status("Consultando IA" if retry_index == 0 else "Tentando novamente", C_BLUE)
        UrlRequest(
            gemini_url(model), req_body=payload,
            req_headers={"Content-Type": "application/json",
                         "x-goog-api-key": GEMINI_KEY},
            on_success=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_answer(res, question), 0),
            on_failure=lambda req, res: Clock.schedule_once(
                lambda dt: self._on_http_failure(req, res, question, payload,
                                                  model_index, retry_index), 0),
            on_error=lambda req, err: Clock.schedule_once(
                lambda dt: self._on_network_failure(str(err), question, payload,
                                                     model_index, retry_index), 0),
            timeout=60)

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

    def _retry_or_fallback(self, question, payload, model_index, retry_index, status):
        if retry_index < len(GEMINI_RETRY_DELAYS):
            delay = GEMINI_RETRY_DELAYS[retry_index]
            self._set_status(f"IA ocupada - nova tentativa em {delay}s", C_BLUE)
            Clock.schedule_once(
                lambda dt: self._send_gemini_request(
                    question, payload, model_index, retry_index+1), delay)
            return True
        if model_index+1 < len(GEMINI_MODELS):
            self._set_status("Usando IA alternativa", C_BLUE)
            Clock.schedule_once(
                lambda dt: self._send_gemini_request(
                    question, payload, model_index+1, 0), 1)
            return True
        return False

    def _finish_request_error(self, message, state, question=""):
        if self._typing and self._typing.parent:
            self.msg_box.remove_widget(self._typing)
        self._typing = None
        self._add_bubble(message, is_user=False)
        self.is_loading = False
        self.send_btn.disabled = False
        self._set_status(state, C_RED)
        if question:
            self._last_failed_question = question
            self._chat_typed = question[:120]
            self._update_chat_display()

    def _on_http_failure(self, req, res, question, payload, model_index, retry_index):
        status = getattr(req, "resp_status", 0) or 0
        if status in (429, 500, 502, 503, 504):
            if self._retry_or_fallback(question, payload, model_index, retry_index, status):
                return
            msg   = "A IA esta ocupada. Sua pergunta foi preservada; tente novamente."
            state = "IA ocupada"
        elif status == 403:
            msg   = "Chave Gemini recusada. Gere novamente o APK."
            state = "Erro IA"
        elif status == 404:
            if model_index+1 < len(GEMINI_MODELS):
                Clock.schedule_once(
                    lambda dt: self._send_gemini_request(
                        question, payload, model_index+1, 0), 1)
                return
            msg   = "Modelo de IA indisponivel para esta chave."
            state = "Erro IA"
        else:
            msg   = f"A API respondeu com erro HTTP {status}."
            state = "Erro IA"
        self._finish_request_error(msg, state, question)

    def _on_network_failure(self, err, question, payload, model_index, retry_index):
        if self._retry_or_fallback(question, payload, model_index, retry_index, 0):
            return
        self._finish_request_error(
            "Nao foi possivel alcançar a IA. Verifique o Wi-Fi e tente novamente.",
            "Offline", question)
        Clock.schedule_once(lambda dt: self._ping_internet(), 10)

    def _ping_internet(self):
        UrlRequest("https://www.google.com",
                   on_success=lambda req, res: Clock.schedule_once(
                       lambda dt: self._ping_gemini(), 0),
                   on_failure=lambda req, res: Clock.schedule_once(
                       lambda dt: self._ping_retry(), 0),
                   on_error=lambda req, err: Clock.schedule_once(
                       lambda dt: self._ping_retry(), 0),
                   timeout=8)

    def _ping_gemini(self):
        if not GEMINI_KEY or "SUA_CHAVE_GEMINI" in GEMINI_KEY:
            self._set_status("Configuracao", C_RED); return
        UrlRequest("https://generativelanguage.googleapis.com/v1beta/models",
                   req_headers={"x-goog-api-key": GEMINI_KEY},
                   on_success=lambda req, res: Clock.schedule_once(
                       lambda dt: self._set_status("Online", C_GREEN), 0),
                   on_failure=lambda req, res: Clock.schedule_once(
                       lambda dt: self._set_status("Erro IA", C_RED), 0),
                   on_error=lambda req, err: Clock.schedule_once(
                       lambda dt: self._ping_retry(), 0),
                   timeout=10)

    def _ping_retry(self):
        Clock.schedule_once(lambda dt: self._ping_internet(), 20)

    # ── Build UI ──────────────────────────────────────────────
    def _build(self):
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")
        root = BoxLayout(orientation="horizontal")
        bind_bg(root, C_BG)

        # Sidebar — largura um pouco maior para 6 temas
        sidebar = BoxLayout(orientation="vertical",
                            size_hint_x=None, width=dp(180),
                            padding=[dp(10), dp(14), dp(10), dp(10)],
                            spacing=dp(3))
        bind_bg(sidebar, C_WHITE)

        logo_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        logo_b = BoxLayout(size_hint=(None, None), size=(dp(34), dp(34)))
        with logo_b.canvas:
            Color(*C_BLUE)
            RoundedRectangle(pos=logo_b.pos, size=logo_b.size, radius=[dp(8)])
        logo_b.bind(pos=lambda w, v: self._rdraw_lb(w),
                    size=lambda w, v: self._rdraw_lb(w))
        logo_b.add_widget(Label(text="IB", font_size=sp(12), bold=True,
                                color=C_WHITE, size_hint=(None, None),
                                size=(dp(34), dp(34))))
        tcol = BoxLayout(orientation="vertical", spacing=dp(1))
        tcol.add_widget(Label(text="Ibero Group", font_size=sp(11), bold=True,
                              color=C_DARK, halign="left",
                              size_hint_y=None, height=dp(18)))
        tcol.add_widget(Label(text="Totem ESG", font_size=sp(9),
                              color=C_BLUE, halign="left",
                              size_hint_y=None, height=dp(14)))
        logo_row.add_widget(logo_b); logo_row.add_widget(tcol)
        sidebar.add_widget(logo_row)

        div = Widget(size_hint_y=None, height=dp(1))
        bind_bg(div, C_BORDER)
        sidebar.add_widget(div)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(2)))

        self.greet_lbl = Label(text=f"Ola, {name}!", font_size=sp(11),
                               bold=True, color=C_BLUE, halign="left",
                               size_hint_y=None, height=dp(20))
        sidebar.add_widget(self.greet_lbl)
        sidebar.add_widget(Label(text="TEMAS", font_size=sp(9), bold=True,
                                 color=C_GRAY_LIGHT, halign="left",
                                 size_hint_y=None, height=dp(16)))

        self.topic_btns = {}
        for key, meta in TOPICS.items():
            btn = self._make_topic_btn(key, meta)
            sidebar.add_widget(btn)
            self.topic_btns[key] = btn

        sidebar.add_widget(Widget())

        div2 = Widget(size_hint_y=None, height=dp(1))
        bind_bg(div2, C_BORDER)
        sidebar.add_widget(div2)

        quiz_btn = Btn(text="Quiz ESG", bg=C_BLUE_PALE, fg=C_BLUE,
                       font_size=sp(11), bold=True, r=7,
                       border_color=C_BLUE_MUTED,
                       size_hint_y=None, height=dp(34))
        quiz_btn.bind(on_press=self._open_quiz)
        sidebar.add_widget(quiz_btn)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(3)))

        exit_btn = Btn(text="Sair", bg=C_BG, fg=C_GRAY_LIGHT,
                       font_size=sp(11), r=7, border_color=C_BORDER,
                       size_hint_y=None, height=dp(34))
        exit_btn.bind(on_press=self._exit)
        sidebar.add_widget(exit_btn)
        sidebar.add_widget(Widget(size_hint_y=None, height=dp(4)))
        root.add_widget(sidebar)

        # Chat area
        right = BoxLayout(orientation="vertical")
        bind_bg(right, C_BG)

        sub = BoxLayout(size_hint_y=None, height=dp(46),
                        padding=[dp(14), 0], spacing=dp(8))
        bind_bg(sub, C_WHITE)
        acc = Widget(size_hint=(None, None), size=(dp(3), dp(30)))
        bind_bg(acc, C_BLUE, radius=2)
        self.header_lbl = Label(text="Agente ESG  —  Ambiental",
                                font_size=sp(13), bold=True,
                                color=C_DARK, halign="left")
        sub.add_widget(acc); sub.add_widget(self.header_lbl)
        st_box = BoxLayout(size_hint=(None, None), size=(dp(78), dp(24)),
                           spacing=dp(4), padding=[dp(6), dp(4)])
        bind_bg(st_box, C_BG, radius=12)
        self.st_dot = Widget(size_hint=(None, None), size=(dp(7), dp(7)))
        with self.st_dot.canvas:
            Color(*C_GREEN); Ellipse(pos=self.st_dot.pos, size=self.st_dot.size)
        self.st_dot.bind(pos=lambda w, v: self._draw_dot(w, C_GREEN),
                         size=lambda w, v: self._draw_dot(w, C_GREEN))
        self.st_lbl = Label(text="Online", font_size=sp(10), color=C_GREEN)
        st_box.add_widget(self.st_dot); st_box.add_widget(self.st_lbl)
        sub.add_widget(st_box)
        right.add_widget(sub)

        sep = Widget(size_hint_y=None, height=dp(1))
        bind_bg(sep, C_BORDER)
        right.add_widget(sep)

        self.scroll = ScrollView(do_scroll_x=False)
        self.msg_box = BoxLayout(orientation="vertical", size_hint_y=None,
                                 spacing=dp(10), padding=[dp(12), dp(12)])
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        self.scroll.add_widget(self.msg_box)
        right.add_widget(self.scroll)

        inp_sep = Widget(size_hint_y=None, height=dp(1))
        bind_bg(inp_sep, C_BORDER)
        right.add_widget(inp_sep)

        # Barra de input com botão de voz
        inp_bar = BoxLayout(size_hint_y=None, height=dp(52),
                            padding=[dp(10), dp(7)], spacing=dp(8))
        bind_bg(inp_bar, C_WHITE)

        self.chat_display = Label(
            text=f"Ola {name}, o que deseja saber?",
            font_size=sp(13), color=C_GRAY_LIGHT,
            halign="left", valign="middle", size_hint_x=1)
        disp_box = BoxLayout(padding=[dp(10), dp(5)])
        with disp_box.canvas.before:
            Color(*C_BG)
            RoundedRectangle(pos=disp_box.pos, size=disp_box.size, radius=[dp(10)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(disp_box.x, disp_box.y,
                                    disp_box.width, disp_box.height, dp(10)),
                 width=dp(1.5))
        disp_box.bind(pos=lambda w, v: self._rdraw_disp(w),
                      size=lambda w, v: self._rdraw_disp(w))
        disp_box.add_widget(self.chat_display)

        # Botão microfone (fala em vez de digitar)
        self.mic_btn = Btn(text="Falar", bg=C_BLUE_PALE, fg=C_BLUE,
                           font_size=sp(11), bold=True,
                           size_hint_x=None, width=dp(56), r=10,
                           border_color=C_BLUE_MUTED)
        self.mic_btn.bind(on_press=self._start_voice)

        self.send_btn = Btn(text=">", bg=C_BLUE, fg=C_WHITE,
                            font_size=sp(18), bold=True,
                            size_hint_x=None, width=dp(48), r=10)
        self.send_btn.bind(on_press=self.send_msg)

        inp_bar.add_widget(disp_box)
        inp_bar.add_widget(self.mic_btn)
        inp_bar.add_widget(self.send_btn)
        right.add_widget(inp_bar)

        # Teclado virtual
        right.add_widget(self._build_chat_keyboard(name))
        root.add_widget(right)
        self.add_widget(root)
        self._show_welcome()

    def _rdraw_lb(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(*C_BLUE); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(8)])

    def _rdraw_disp(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_BG); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])
            Color(*C_BORDER_MED)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(10)), width=dp(1.5))

    def _draw_dot(self, w, color):
        w.canvas.clear()
        with w.canvas:
            Color(*color); Ellipse(pos=w.pos, size=w.size)

    def _build_chat_keyboard(self, name):
        rows = [list("QWERTYUIOP"), list("ASDFGHJKL"), list("ZXCVBNM")]
        kb = BoxLayout(orientation="vertical", size_hint_y=None,
                       height=dp(156), spacing=dp(3), padding=[dp(6), dp(3)])
        bind_bg(kb, C_WHITE)
        for row in rows:
            rbox = BoxLayout(spacing=dp(3), size_hint_y=None, height=dp(36))
            for k in row:
                btn = Btn(text=k, bg=C_KEY_BG, fg=C_DARK, font_size=sp(12),
                          bold=True, r=5, border_color=C_BORDER_MED)
                btn.bind(on_press=lambda b, k=k: self._chat_type(k))
                rbox.add_widget(btn)
            kb.add_widget(rbox)
        spec = BoxLayout(spacing=dp(3), size_hint_y=None, height=dp(36),
                         padding=[dp(2), 0])
        bd = Btn(text="< Del", bg=C_KEY_BG, fg=C_RED, font_size=sp(11),
                 bold=True, r=5, border_color=C_BORDER_MED)
        bd.bind(on_press=lambda b: self._chat_type("DEL"))
        bs = Btn(text="Espaco", bg=C_KEY_BG, fg=C_GRAY, font_size=sp(11),
                 r=5, border_color=C_BORDER_MED)
        bs.bind(on_press=lambda b: self._chat_type(" "))
        be = Btn(text="Enviar >", bg=C_BLUE, fg=C_WHITE, font_size=sp(12),
                 bold=True, r=5)
        be.bind(on_press=self.send_msg)
        spec.add_widget(bd); spec.add_widget(bs); spec.add_widget(be)
        kb.add_widget(spec)
        return kb

    def _chat_type(self, k):
        self._reset_inactivity()
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
            self.chat_display.text = self._chat_typed
            self.chat_display.color = C_DARK
        else:
            self.chat_display.text = f"Ola {name}, o que deseja saber?"
            self.chat_display.color = C_GRAY_LIGHT

    def _make_topic_btn(self, key, meta):
        is_act = (key == "ambiental")
        tc  = meta["color"]
        tp  = meta.get("color_pale", C_BLUE_PALE)
        bg  = tp   if is_act else C_BG
        brd = tc   if is_act else C_BORDER
        row = BoxLayout(orientation="horizontal",
                        size_hint_y=None, height=dp(38),
                        spacing=dp(6), padding=[dp(5), dp(4)])
        with row.canvas.before:
            Color(*brd); RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(7)])
            Color(*bg)
            RoundedRectangle(pos=(row.x+dp(1), row.y+dp(1)),
                             size=(max(row.width-dp(2), 1), max(row.height-dp(2), 1)),
                             radius=[dp(6)])
        row._bg = bg; row._brd = brd

        def _rd(w, v, r=row):
            r.canvas.before.clear()
            with r.canvas.before:
                Color(*r._brd); RoundedRectangle(pos=r.pos, size=r.size, radius=[dp(7)])
                Color(*r._bg)
                RoundedRectangle(pos=(r.x+dp(1), r.y+dp(1)),
                                 size=(max(r.width-dp(2), 1), max(r.height-dp(2), 1)),
                                 radius=[dp(6)])
        row.bind(pos=_rd, size=_rd)

        bd = BoxLayout(size_hint=(None, None), size=(dp(24), dp(24)))
        with bd.canvas.before:
            Color(*tc); RoundedRectangle(pos=bd.pos, size=bd.size, radius=[dp(5)])
        bd.bind(pos=lambda w, v, c=tc: self._rdraw_badge(w, c),
                size=lambda w, v, c=tc: self._rdraw_badge(w, c))
        bd.add_widget(Label(text=meta["code"], font_size=sp(8), bold=True,
                            color=C_WHITE, size_hint=(None, None),
                            size=(dp(24), dp(24))))

        lbl = Label(text=meta["label"], font_size=sp(11),
                    bold=is_act, color=tc if is_act else C_GRAY,
                    halign="left")
        row.add_widget(bd); row.add_widget(lbl)
        row._lbl = lbl
        row.bind(on_touch_down=lambda w, t, k=key: self._touch_topic(w, t, k))
        return row

    def _rdraw_badge(self, w, c):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*c); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(5)])

    def _touch_topic(self, row, touch, key):
        if row.collide_point(*touch.pos):
            self.set_topic(key)

    def set_topic(self, key):
        self._reset_inactivity()
        self.topic = key
        meta = TOPICS[key]
        tc   = meta["color"]
        tp   = meta.get("color_pale", C_BLUE_PALE)
        self.header_lbl.text = f"Agente ESG  —  {meta['label']}"

        for k, r in self.topic_btns.items():
            act   = (k == key)
            tmeta = TOPICS[k]
            r._bg  = tmeta.get("color_pale", C_BLUE_PALE) if act else C_BG
            r._brd = tmeta["color"] if act else C_BORDER
            r._lbl.bold  = act
            r._lbl.color = tmeta["color"] if act else C_GRAY
            r.canvas.before.clear()
            with r.canvas.before:
                Color(*r._brd); RoundedRectangle(pos=r.pos, size=r.size, radius=[dp(7)])
                Color(*r._bg)
                RoundedRectangle(pos=(r.x+dp(1), r.y+dp(1)),
                                 size=(max(r.width-dp(2), 1), max(r.height-dp(2), 1)),
                                 radius=[dp(6)])
        self._load_quick()
        # Injeta card colorido com perguntas rápidas do novo tema
        self._inject_quick_card(key)

    def _inject_quick_card(self, key):
        meta = TOPICS[key]
        tc   = meta["color"]
        tp   = meta.get("color_pale", C_BLUE_PALE)
        qs   = self.quick_list if (self.quick_list and self.topic == key) \
               else meta["qs"]

        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(12), dp(10)], spacing=dp(6))
        with card.canvas.before:
            Color(*tp); RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
            Color(*tc)
            Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(12)),
                 width=dp(1.5))
        card.bind(pos=lambda w, v, tp=tp, tc=tc: self._rdraw_topic_card(w, tp, tc),
                  size=lambda w, v, tp=tp, tc=tc: self._rdraw_topic_card(w, tp, tc))
        card.add_widget(Label(text=f"Perguntas sobre {meta['label']}:",
                              font_size=sp(12), bold=True, color=tc,
                              halign="left", size_hint_y=None, height=dp(22)))
        grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(5))
        grid.bind(minimum_height=grid.setter("height"))
        for q in qs[:6]:
            text = q["question"] if isinstance(q, dict) else q
            btn = Btn(text=text, bg=C_WHITE, fg=C_DARK, font_size=sp(11),
                      size_hint_y=None, height=dp(44), r=8, border_color=tc)
            btn.bind(on_press=lambda b, q=text: self._prefill(q))
            grid.add_widget(btn)
        card.add_widget(grid)
        card.bind(minimum_height=card.setter("height"))
        self.msg_box.add_widget(card)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)

    def _rdraw_topic_card(self, w, tp, tc):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*tp); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(12)])
            Color(*tc)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(12)), width=dp(1.5))

    def _show_welcome(self):
        self.msg_box.clear_widgets()
        self.history.clear()
        app  = App.get_running_app()
        name = getattr(app, "operator_name", "Operador")
        wrap = BoxLayout(orientation="vertical", size_hint_y=None,
                         spacing=dp(10), padding=[dp(4), dp(4)])
        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         padding=[dp(16), dp(14)], spacing=dp(8))
        with card.canvas.before:
            Color(*C_WHITE); RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(14)])
            Color(*C_BORDER)
            Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(14)),
                 width=dp(1))
        card.bind(pos=lambda w, v: self._rdraw_wcard(w),
                  size=lambda w, v: self._rdraw_wcard(w))
        card.add_widget(Label(text=f"Bem-vindo, {name}!", font_size=sp(15),
                              bold=True, color=C_BLUE, halign="center",
                              size_hint_y=None, height=dp(26)))
        card.add_widget(Label(text="Escolha um tema ou faca sua pergunta.",
                              font_size=sp(12), color=C_GRAY, halign="center",
                              size_hint_y=None, height=dp(20)))
        card.bind(minimum_height=card.setter("height"))
        wrap.add_widget(card)
        self.quick_grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(7))
        self.quick_grid.bind(minimum_height=self.quick_grid.setter("height"))
        wrap.add_widget(self.quick_grid)
        wrap.bind(minimum_height=wrap.setter("height"))
        self.msg_box.add_widget(wrap)
        self._welcome_wrap = wrap
        self._render_quick()

    def _rdraw_wcard(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*C_WHITE); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(14)])
            Color(*C_BORDER)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(14)), width=dp(1))

    def _render_quick(self):
        self.quick_grid.clear_widgets()
        qs = self.quick_list if self.quick_list else TOPICS[self.topic]["qs"]
        tc = TOPICS[self.topic]["color"]
        for q in qs[:6]:
            text = q["question"] if isinstance(q, dict) else q
            btn = Btn(text=text, bg=C_BG, fg=C_DARK, font_size=sp(11),
                      size_hint_y=None, height=dp(48), r=8, border_color=tc)
            btn.bind(on_press=lambda b, q=text: self._prefill(q))
            self.quick_grid.add_widget(btn)

    def _prefill(self, q):
        self._reset_inactivity()
        self._chat_typed = q
        self._update_chat_display()
        self.send_msg()

    def _add_bubble(self, text, is_user=False, initials="IB"):
        b = Bubble(text=text, is_user=is_user, initials=initials)
        self.msg_box.add_widget(b)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return b

    def _add_typing(self):
        lbl = Label(text="Agente digitando...", font_size=sp(12), color=C_BLUE,
                    size_hint_y=None, height=dp(28), halign="left")
        self.msg_box.add_widget(lbl)
        Clock.schedule_once(lambda dt: self._scroll_end(), 0.1)
        return lbl

    def _scroll_end(self):
        self.scroll.scroll_y = 0

    def _set_status(self, text, color):
        self.st_lbl.text = text; self.st_lbl.color = color
        self._draw_dot(self.st_dot, color)

    def _open_quiz(self, *_):
        self._reset_inactivity()
        quiz = self.manager.get_screen("quiz")
        quiz.start_quiz(self.topic)
        self.manager.current = "quiz"

    def _exit(self, *_):
        if self._inact_ev:
            self._inact_ev.cancel()
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
        self._reset_inactivity()


# ════════════════════════════════════════════════════════════
#  TELA 3 — QUIZ ESG (colorido por tema)
# ════════════════════════════════════════════════════════════
class QuizScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._topic    = "ambiental"
        self._qs       = []
        self._idx      = 0
        self._score    = 0
        self._built    = False
        self._ans_btns = []

    def start_quiz(self, topic):
        import random
        self._topic = topic
        pool = list(QUIZ_DATA.get(topic, QUIZ_DATA["ambiental"]))
        random.shuffle(pool)
        n = min(5, len(pool))
        selected = pool[:n]
        # Embaralha as alternativas de cada pergunta (evita resposta sempre na mesma posicao)
        self._qs = []
        for item in selected:
            options = list(item["a"])
            correct_text = item["correct"]
            random.shuffle(options)
            self._qs.append({
                "q": item["q"],
                "a": options,
                "c": options.index(correct_text),
            })
        self._idx   = 0
        self._score = 0
        if not self._built:
            self._build(); self._built = True
        self._apply_theme()
        self._show_q()

    def _tc(self): return TOPICS[self._topic]["color"]
    def _tp(self): return TOPICS[self._topic].get("color_pale", C_BLUE_PALE)

    def _apply_theme(self):
        tc = self._tc(); tp = self._tp()
        if hasattr(self, "q_card_widget"):
            self._rdraw_q_card(self.q_card_widget, tc, tp)
        if hasattr(self, "q_num_lbl"):
            self.q_num_lbl.color = tc
        if hasattr(self, "prog_fill"):
            draw_bg(self.prog_fill, tc, radius=3)

    def _build(self):
        root = BoxLayout(orientation="vertical")
        bind_bg(root, C_BG)

        hdr = BoxLayout(size_hint_y=None, height=dp(50),
                        padding=[dp(14), 0], spacing=dp(10))
        bind_bg(hdr, C_BLUE)
        hdr.add_widget(Label(text="Quiz ESG — Ibero Group",
                             font_size=sp(14), bold=True, color=C_WHITE))
        back = Btn(text="< Voltar", bg=get_color_from_hex("#1976D2"),
                   fg=C_WHITE, font_size=sp(11), r=7,
                   size_hint_x=None, width=dp(80))
        back.bind(on_press=lambda b: setattr(self.manager, "current", "chat"))
        hdr.add_widget(back)
        root.add_widget(hdr)

        sep = Widget(size_hint_y=None, height=dp(1))
        bind_bg(sep, C_BORDER)
        root.add_widget(sep)

        body = BoxLayout(orientation="vertical",
                         padding=[dp(18), dp(14)], spacing=dp(10))
        bind_bg(body, C_BG)

        # Progresso
        prog_row = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
        self.prog_lbl = Label(text="Pergunta 1 de 5", font_size=sp(11),
                              color=C_GRAY_LIGHT, halign="left", size_hint_x=1)
        self.score_lbl = Label(text="0 pts", font_size=sp(11), bold=True,
                               color=C_BLUE, size_hint_x=None, width=dp(60),
                               halign="right")
        prog_row.add_widget(self.prog_lbl); prog_row.add_widget(self.score_lbl)
        body.add_widget(prog_row)

        prog_track = BoxLayout(size_hint_y=None, height=dp(6))
        bind_bg(prog_track, C_BORDER, radius=3)
        self.prog_fill = Widget(size_hint_x=0, size_hint_y=1)
        draw_bg(self.prog_fill, C_BLUE, radius=3)
        prog_track.add_widget(self.prog_fill); prog_track.add_widget(Widget())
        body.add_widget(prog_track)

        # Card da pergunta
        q_card = BoxLayout(orientation="vertical", size_hint_y=None,
                           padding=[dp(16), dp(14)], spacing=dp(10))
        tc0 = self._tc(); tp0 = self._tp()
        with q_card.canvas.before:
            Color(*tp0); RoundedRectangle(pos=q_card.pos, size=q_card.size, radius=[dp(14)])
            Color(*tc0)
            Line(rounded_rectangle=(q_card.x, q_card.y,
                                    q_card.width, q_card.height, dp(14)), width=dp(1.5))
        q_card.bind(pos=lambda w, v: self._rdraw_q_card(w, self._tc(), self._tp()),
                    size=lambda w, v: self._rdraw_q_card(w, self._tc(), self._tp()))
        self.q_card_widget = q_card

        self.q_num_lbl = Label(text="", font_size=sp(10), bold=True,
                               color=tc0, halign="left",
                               size_hint_y=None, height=dp(18))
        q_card.add_widget(self.q_num_lbl)

        self.q_text_lbl = Label(text="", font_size=sp(14), bold=True,
                                color=C_DARK, halign="left", valign="top",
                                size_hint_y=None, height=dp(64),
                                text_size=(Window.width * 0.6, None))
        q_card.add_widget(self.q_text_lbl)

        self._ans_btns = []
        for i in range(3):
            btn = Btn(text="", bg=C_WHITE, fg=C_DARK, font_size=sp(12),
                      size_hint_y=None, height=dp(46), r=9,
                      border_color=C_BORDER_MED)
            btn.bind(on_press=lambda b, i=i: self._answer(i))
            q_card.add_widget(btn)
            self._ans_btns.append(btn)

        self.feedback_lbl = Label(text="", font_size=sp(12), bold=True,
                                  color=C_GREEN, halign="center",
                                  size_hint_y=None, height=dp(28))
        q_card.add_widget(self.feedback_lbl)
        q_card.bind(minimum_height=q_card.setter("height"))
        body.add_widget(q_card)
        body.add_widget(Widget())
        root.add_widget(body)
        self.add_widget(root)

    def _rdraw_q_card(self, w, tc, tp):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*tp); RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(14)])
            Color(*tc)
            Line(rounded_rectangle=(w.x, w.y, w.width, w.height, dp(14)), width=dp(1.5))

    def _show_q(self):
        if self._idx >= len(self._qs):
            self._show_result(); return
        q     = self._qs[self._idx]
        total = len(self._qs)
        tc    = self._tc()
        self.prog_lbl.text   = f"Pergunta {self._idx+1} de {total}"
        self.score_lbl.text  = f"{self._score} pts"
        self.score_lbl.color = tc
        self.q_num_lbl.text  = TOPICS[self._topic]["label"].upper()
        self.q_num_lbl.color = tc
        self.q_text_lbl.text = q["q"]
        self.feedback_lbl.text = ""
        self.prog_fill.size_hint_x = self._idx / total
        draw_bg(self.prog_fill, tc, radius=3)
        for i, btn in enumerate(self._ans_btns):
            if i < len(q["a"]):
                btn.text = q["a"][i]; btn._bg = C_WHITE
                btn._border = C_BORDER_MED; btn.disabled = False; btn._draw()
            else:
                btn.text = ""; btn.disabled = True

    def _answer(self, idx):
        q  = self._qs[self._idx]; tc = self._tc()
        for btn in self._ans_btns:
            btn.disabled = True
        if idx == q["c"]:
            self._score += 1
            self._ans_btns[idx]._bg     = get_color_from_hex("#E8F5E9")
            self._ans_btns[idx]._border = C_GREEN
            self._ans_btns[idx]._draw()
            self.feedback_lbl.color = C_GREEN
            self.feedback_lbl.text  = "Correto! Muito bem!"
        else:
            self._ans_btns[idx]._bg     = get_color_from_hex("#FFEBEE")
            self._ans_btns[idx]._border = C_RED
            self._ans_btns[idx]._draw()
            if q["c"] < len(self._ans_btns):
                self._ans_btns[q["c"]]._bg     = get_color_from_hex("#E8F5E9")
                self._ans_btns[q["c"]]._border = C_GREEN
                self._ans_btns[q["c"]]._draw()
            self.feedback_lbl.color = C_RED
            self.feedback_lbl.text  = "Nao foi dessa vez. Resposta correta em verde!"
        self.score_lbl.text = f"{self._score} pts"
        self._idx += 1
        # Aguarda para o operador ver o feedback, depois transiciona suave
        Clock.schedule_once(lambda dt: self._fade_next(), 2.0)

    def _fade_next(self):
        from kivy.animation import Animation
        card = self.q_card_widget
        anim = Animation(opacity=0.0, duration=0.2)
        anim.bind(on_complete=lambda *a: self._after_fade())
        anim.start(card)

    def _after_fade(self):
        from kivy.animation import Animation
        self._show_q()
        card = self.q_card_widget
        card.opacity = 0.0
        Animation(opacity=1.0, duration=0.25).start(card)

    def _show_result(self):
        total = len(self._qs)
        pct   = int(self._score / total * 100) if total else 0
        tc    = self._tc()
        self.prog_fill.size_hint_x = 1.0
        draw_bg(self.prog_fill, tc, radius=3)
        self.q_num_lbl.text  = "RESULTADO — " + TOPICS[self._topic]["label"].upper()
        self.q_num_lbl.color = tc
        self.q_text_lbl.text = f"{self._score}/{total} acertos • {pct}%"
        if pct == 100:
            self.feedback_lbl.color = C_GREEN
            self.feedback_lbl.text  = "Perfeito! Voce e um especialista ESG da Ibero Group!"
        elif pct >= 67:
            self.feedback_lbl.color = tc
            self.feedback_lbl.text  = "Muito bom! Continue aprendendo e compartilhe com a equipe!"
        else:
            self.feedback_lbl.color = C_GRAY
            self.feedback_lbl.text  = "Continue estudando! Cada aprendizado fortalece o ESG."
        self.prog_lbl.text = "Quiz concluido!"
        for btn in self._ans_btns:
            btn.text = ""; btn.disabled = True
        Clock.schedule_once(
            lambda dt: setattr(self.manager, "current", "chat"), 4)


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
        sm.add_widget(QuizScreen(name="quiz"))
        return sm


if __name__ == "__main__":
    TotemESGApp().run()
