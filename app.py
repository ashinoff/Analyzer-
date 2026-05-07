"""
Streamlit-приложение: анализ аномального потребления.
Эстетика: editorial dark, диспетчерская энергосистемы, расширенная палитра.
CSS жёстко перекрывает дефолты — config.toml желателен, но не обязателен.
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go

from analyzer import (
    analyze, DEFAULT_CONFIG, FLAG_DEFINITIONS,
    detect_month_columns, MONTHS_RU
)

st.set_page_config(
    page_title="Анализ потребления",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# СЛОВАРИ ЛОКАЛИЗАЦИИ
# =====================================================================
METRIC_LABELS = {
    'active_months':    'Активных месяцев',
    'mean_kwh':         'Среднее, кВт·ч/мес',
    'total_kwh':        'Всего, кВт·ч',
    'max_kwh':          'Пиковый месяц, кВт·ч',
    'avg_recent':       'Среднее в недавнем периоде',
    'avg_baseline':     'Среднее в опорном периоде',
    'drop_ratio':       'Доля падения',
    'longest_silence':  'Макс. пауза в показаниях, мес.',
    'longest_flat_run': 'Макс. серия одинаковых, мес.',
    'power_ratio':      'Отношение пиковой/разрешённой',
    'cohort_z':         'Z-оценка в когорте',
    'сезонность':       'Сезонность',
    'мало_данных':      'Мало данных',
    'кол-во_флагов':    'Кол-во флагов',
}

FLAG_EMOJI = {
    'подозрение_хищение':   '🔻',
    'долгое_молчание':      '🔇',
    'превышение_мощности':  '⚡',
    'нестабильность':       '📊',
    'одинаковые_подряд':    '📐',
    'аномалия_в_когорте':   '👥',
}

FLAG_TITLES = {
    'подозрение_хищение':   'Подозрение на хищение',
    'долгое_молчание':      'Долгое молчание ПУ',
    'превышение_мощности':  'Превышение мощности',
    'нестабильность':       'Нестабильность',
    'одинаковые_подряд':    'Одинаковые подряд',
    'аномалия_в_когорте':   'Аномалия в когорте',
}

# Цвет на флаг — расширенная палитра
FLAG_COLOR = {
    'подозрение_хищение':   '#ff6b6b',  # коралл
    'долгое_молчание':      '#a78bfa',  # лиловый
    'превышение_мощности':  '#f5d442',  # электр. жёлтый
    'нестабильность':       '#5eead4',  # бирюза
    'одинаковые_подряд':    '#fb923c',  # янтарь
    'аномалия_в_когорте':   '#f472b6',  # розовый
}

# =====================================================================
# СТИЛИ — жёстко перекрывают дефолты Streamlit
# =====================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,600;9..144,800;9..144,900&family=Manrope:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

:root {
    --bg: #0a0b0f;
    --bg-glow: #14151d;
    --surface: #14151c;
    --surface-2: #1c1d26;
    --border: #2a2c38;
    --border-soft: #1f2029;
    --text: #ececf0;
    --text-dim: #8e91a0;
    --text-faint: #5a5d6a;

    --accent: #f5d442;          /* электрический жёлтый */
    --accent-glow: #fde047;
    --coral: #ff6b6b;           /* для опасности */
    --mint: #5eead4;            /* для нормы */
    --lilac: #a78bfa;           /* для нейтрального */
    --amber: #fb923c;           /* для предупреждения */
    --rose: #f472b6;            /* для редкого */
}

/* фон с лёгким свечением сверху */
.stApp {
    background:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(245, 212, 66, 0.08), transparent 70%),
        radial-gradient(ellipse 60% 40% at 100% 0%, rgba(167, 139, 250, 0.06), transparent 60%),
        var(--bg) !important;
}

html, body, [class*="css"], .stApp, .stApp * {
    font-family: 'Manrope', system-ui, sans-serif;
    color: var(--text);
}

/* шапка / тулбар */
header[data-testid="stHeader"] { background: transparent !important; }
.stDeployButton, #MainMenu, footer { display: none !important; visibility: hidden !important; }

/* типографика */
h1, h2, h3, .display-font {
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--text);
}
h1 { font-size: 3.2rem !important; line-height: 1; }
h2 { font-size: 1.6rem !important; }
h3 { font-size: 1.2rem !important; }

.mono { font-family: 'JetBrains Mono', monospace !important; }

/* ============ HERO ============ */
.hero {
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    padding: 1.6rem 0;
    margin: 0.5rem 0 2rem 0;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 2rem;
}
.hero-title {
    font-family: 'Fraunces', serif !important;
    font-weight: 800;
    font-size: 3rem;
    letter-spacing: -0.035em;
    line-height: 0.95;
    margin: 0;
    color: var(--text);
}
.hero-title em {
    font-style: italic;
    font-weight: 300;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-glow) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-meta {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    text-align: right;
    line-height: 1.7;
    white-space: nowrap;
}
.hero-meta b { color: var(--accent); font-weight: 500; }

/* ============ ЛЕНТА МЕТРИК ============ */
.metric-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: linear-gradient(180deg, var(--surface) 0%, var(--bg) 100%);
    margin-bottom: 2rem;
    overflow: hidden;
}
.metric-cell {
    padding: 1.4rem 1.6rem;
    border-right: 1px solid var(--border);
    position: relative;
}
.metric-cell:last-child { border-right: none; }
.metric-cell::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--cell-accent, transparent);
}
.metric-label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--text-dim);
    margin-bottom: 0.5rem;
}
.metric-value {
    font-family: 'Fraunces', serif !important;
    font-weight: 600;
    font-size: 2.6rem;
    line-height: 1;
    color: var(--text);
}
.metric-value.accent { color: var(--accent); }
.metric-value.coral  { color: var(--coral); }
.metric-value.mint   { color: var(--mint); }

/* ============ СЕКЦИОННЫЕ ЗАГОЛОВКИ ============ */
.section-label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.25em;
    color: var(--accent);
    margin: 2rem 0 0.4rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.section-label::before {
    content: '';
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--accent);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--accent);
}
.section-title {
    font-family: 'Fraunces', serif !important;
    font-weight: 600;
    font-size: 1.6rem;
    line-height: 1.1;
    margin: 0.3rem 0 1.3rem 0;
    color: var(--text);
}

/* ============ ФЛАГИ ============ */
.flag-row {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.7rem 1rem;
    margin-bottom: 0.5rem;
    background: linear-gradient(90deg, var(--flag-color, var(--accent))15 0%, var(--surface) 30%);
    border-left: 3px solid var(--flag-color, var(--accent));
    border-radius: 2px;
    transition: transform 0.15s ease;
}
.flag-row:hover { transform: translateX(4px); }
.flag-row .emoji { font-size: 1.1rem; }
.flag-row .name { font-weight: 500; color: var(--text); font-size: 0.95rem; }
.flag-empty {
    padding: 0.9rem 1.1rem;
    color: var(--mint);
    background: linear-gradient(90deg, rgba(94, 234, 212, 0.1), rgba(94, 234, 212, 0.02));
    border-left: 3px solid var(--mint);
    border-radius: 2px;
    font-weight: 500;
}

/* ============ KEY-VALUE СПИСОК ============ */
.kv-list { font-family: 'Manrope', sans-serif; }
.kv-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.55rem 0;
    border-bottom: 1px dashed var(--border-soft);
    gap: 1rem;
}
.kv-row:last-child { border-bottom: none; }
.kv-key { color: var(--text-dim); font-size: 0.86rem; }
.kv-val {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.92rem;
    color: var(--text);
    text-align: right;
    word-break: break-word;
}

/* ============ ТАБЫ ============ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--border);
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    padding: 0.85rem 1.4rem;
    color: var(--text-dim);
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    transition: color 0.2s;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text); }
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
    background: linear-gradient(180deg, transparent 50%, rgba(245, 212, 66, 0.05));
}

/* ============ САЙДБАР ============ */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] h1 {
    font-family: 'Fraunces', serif !important;
    font-size: 1.6rem !important;
    margin-bottom: 0.5rem;
    color: var(--text);
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 3px;
    margin-bottom: 0.5rem;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    font-family: 'Manrope', sans-serif !important;
    font-weight: 500;
    color: var(--text);
}

/* ============ СЛАЙДЕРЫ — ЖЁЛТЫЕ ============ */
/* активная часть трека */
.stSlider [data-baseweb="slider"] > div > div > div {
    background: var(--accent) !important;
}
/* ползунок */
.stSlider [role="slider"] {
    background-color: var(--accent) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px rgba(245, 212, 66, 0.15) !important;
}
/* подпись со значением (всплывает над ползунком) */
.stSlider [data-baseweb="tooltip"] > div {
    background: var(--accent) !important;
    color: var(--bg) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 500;
}
/* числовое значение под ползунком */
.stSlider [data-testid="stTickBarMin"],
.stSlider [data-testid="stTickBarMax"] {
    color: var(--text-faint) !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* number input */
.stNumberInput input {
    background: var(--bg) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stNumberInput button {
    background: var(--surface-2) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

/* select */
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
}

/* ============ КНОПКИ ============ */
.stDownloadButton button, .stButton button {
    background: var(--accent) !important;
    color: var(--bg) !important;
    border: none !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    padding: 0.7rem 1.6rem !important;
    border-radius: 3px !important;
    transition: transform 0.1s, box-shadow 0.2s;
}
.stDownloadButton button:hover, .stButton button:hover {
    background: var(--accent-glow) !important;
    box-shadow: 0 0 24px rgba(245, 212, 66, 0.3);
    transform: translateY(-1px);
}

/* file uploader */
[data-testid="stFileUploaderDropzone"] {
    background: var(--surface) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 4px !important;
    transition: border-color 0.2s, background 0.2s;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent) !important;
    background: var(--surface-2) !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: var(--accent) !important;
    color: var(--bg) !important;
}

/* dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 3px;
    overflow: hidden;
}

/* ============ PILLS ============ */
.pill {
    display: inline-block;
    padding: 0.22rem 0.7rem;
    border-radius: 2px;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.74rem;
    margin: 0.18rem 0.22rem 0.18rem 0;
    border: 1px solid var(--border);
    background: var(--surface);
}
.pill.found { color: var(--mint); border-color: rgba(94, 234, 212, 0.3); }
.pill.miss  { color: var(--text-dim); }

/* ============ ЗАГЛУШКА ============ */
.empty-state {
    border: 1px dashed var(--border);
    padding: 3rem 2rem;
    text-align: center;
    color: var(--text-dim);
    font-family: 'Fraunces', serif !important;
    font-style: italic;
    font-size: 1.2rem;
    margin: 1rem 0;
    background: linear-gradient(180deg, var(--surface) 0%, transparent 100%);
    border-radius: 4px;
}

/* ============ ПОДВАЛ ============ */
.footer-strip {
    margin-top: 3rem;
    padding: 1.2rem 0;
    border-top: 1px solid var(--border);
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.2em;
    text-align: center;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =====================================================================
# Plotly-тема
# =====================================================================
PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='JetBrains Mono, monospace', color='#8e91a0', size=11),
    xaxis=dict(gridcolor='#1f2029', linecolor='#2a2c38', zerolinecolor='#2a2c38',
               tickfont=dict(color='#8e91a0')),
    yaxis=dict(gridcolor='#1f2029', linecolor='#2a2c38', zerolinecolor='#2a2c38',
               tickfont=dict(color='#8e91a0')),
    margin=dict(l=10, r=10, t=20, b=10),
    showlegend=False,
)

ACCENT = '#f5d442'
CORAL = '#ff6b6b'
MINT = '#5eead4'
LILAC = '#a78bfa'
AMBER = '#fb923c'
SUBTLE = '#3a3d48'

# =====================================================================
# САЙДБАР: ПОРОГИ
# =====================================================================
with st.sidebar:
    st.markdown("# Настройки")
    st.markdown('<div style="color:var(--text-dim);font-size:0.85rem;margin-bottom:1.4rem;font-family:Manrope;">Подкручивайте — таблица пересчитается.</div>', unsafe_allow_html=True)

    with st.expander("🔻 Хищение", expanded=True):
        cfg_theft_drop = st.slider("Падение, %", 20, 95, 50, 5) / 100
        cfg_theft_recent = st.slider("Недавний период, мес.", 3, 24, 12)
        cfg_theft_baseline = st.slider("Опорный период, мес.", 6, 36, 24)
        cfg_theft_min = st.number_input("Мин. опорное, кВт·ч", 0, 10000, 50, 10)

    with st.expander("🔇 Молчание ПУ"):
        cfg_silence = st.slider("Подряд месяцев без показаний", 3, 24, 6)

    with st.expander("⚡ Превышение мощности"):
        cfg_power_ratio = st.slider("Порог пиковой/разрешённой", 0.5, 3.0, 1.0, 0.1)

    with st.expander("📊 Нестабильность"):
        cfg_cv = st.slider("Коэфф. вариации", 0.3, 3.0, 1.2, 0.1)

    with st.expander("📐 Одинаковые подряд"):
        cfg_flat = st.slider("Подряд одинаковых значений", 3, 24, 6)

    with st.expander("👥 Аномалия в когорте"):
        cfg_z = st.slider("Robust z-score порог", 1.5, 5.0, 3.0, 0.1)

    with st.expander("🔧 Прочее"):
        cfg_min_active = st.slider("Мин. активных месяцев", 3, 36, 12)

config = {
    "theft_recent_months": cfg_theft_recent, "theft_baseline_months": cfg_theft_baseline,
    "theft_drop_pct": cfg_theft_drop, "theft_min_baseline_kwh": cfg_theft_min,
    "silence_months": cfg_silence, "power_overrun_ratio": cfg_power_ratio,
    "cv_threshold": cfg_cv, "flat_run_months": cfg_flat,
    "cohort_zscore": cfg_z, "min_active_months": cfg_min_active,
}

# =====================================================================
# ШАПКА
# =====================================================================
st.markdown("""
<div class="hero">
  <h1 class="hero-title">Анализ <em>аномального</em><br/>потребления</h1>
  <div class="hero-meta">
    <b>⚡ Энергоучёт</b><br/>
    Реестр абонентов с флагами<br/>
    Данные не сохраняются
  </div>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# ЗАГРУЗКА
# =====================================================================
uploaded = st.file_uploader(
    "Excel-файл с потреблением",
    type=['xlsx', 'xls'],
    label_visibility="collapsed",
)

if not uploaded:
    st.markdown("""
    <div class="empty-state">
      Перетащите выгрузку выше, чтобы начать анализ.<br/>
      <span style="font-size:0.85rem;font-style:normal;font-family:'JetBrains Mono',monospace;color:var(--text-faint);">Минимум: столбцы вида «Январь 2024», «Февраль 2024»…</span>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Какие колонки распознаются и как добавить флаг"):
        st.markdown("""
**Обязательно** — помесячные столбцы вида `Январь 2019`, `Февраль 2019` ... `Январь 2026`.

**Опционально** (без них часть флагов пропускается, но анализ работает):
- `Разрешенная мощность` — для флага «превышение мощности»
- `Вид потребителя` (ФИЗ/ЮР) — для «аномалия в когорте»
- `Заводской номер ПУ`, `Наименование точки учета`, адресные поля

**Какие флаги считаются:**
- 🔻 Подозрение на хищение — резкое устойчивое падение
- 🔇 Долгое молчание ПУ — длинные пропуски в показаниях
- ⚡ Превышение мощности — пиковое потребление выше разрешённой
- 📊 Нестабильность — высокий коэффициент вариации
- 📐 Одинаковые подряд — подозрение на ручной ввод «по нормативу»
- 👥 Аномалия в когорте — потребление сильно выше/ниже соседей
        """)
    st.stop()

# =====================================================================
# АНАЛИЗ
# =====================================================================
@st.cache_data(show_spinner="Читаю файл…")
def load_excel(file_bytes):
    return pd.read_excel(io.BytesIO(file_bytes))

@st.cache_data(show_spinner="Анализирую…")
def run_analysis(file_bytes, config):
    df = load_excel(file_bytes)
    return df, *analyze(df, config)

try:
    df_raw, registry, base, flags, report = run_analysis(uploaded.getvalue(), config)
except ValueError as e:
    st.error(f"❌ {e}")
    st.stop()

# =====================================================================
# ЛЕНТА МЕТРИК
# =====================================================================
n_with_flags = int((registry['кол-во_флагов'] > 0).sum())
n_high_risk = int((registry['кол-во_флагов'] >= 3).sum())

st.markdown(f"""
<div class="metric-strip">
  <div class="metric-cell" style="--cell-accent:var(--lilac);">
    <div class="metric-label">Абонентов в файле</div>
    <div class="metric-value">{report['total_rows']:,}</div>
  </div>
  <div class="metric-cell" style="--cell-accent:var(--mint);">
    <div class="metric-label">Месяцев данных</div>
    <div class="metric-value">{report['months_detected']}</div>
  </div>
  <div class="metric-cell" style="--cell-accent:var(--accent);">
    <div class="metric-label">С флагами</div>
    <div class="metric-value accent">{n_with_flags:,}</div>
  </div>
  <div class="metric-cell" style="--cell-accent:var(--coral);">
    <div class="metric-label">Высокий риск (3+ флага)</div>
    <div class="metric-value coral">{n_high_risk:,}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# =====================================================================
# ОТЧЁТ О ЗАГРУЗКЕ
# =====================================================================
with st.expander(f"Период: {report['period_range']} · что распознано в файле", expanded=False):
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown('<div class="section-label">Найденные колонки</div>', unsafe_allow_html=True)
        pills = "".join(f'<span class="pill found">{v}</span>' for v in report['columns_found'].values())
        st.markdown(f'<div>{pills}</div>', unsafe_allow_html=True)
    with cc2:
        if report['flags_skipped']:
            st.markdown('<div class="section-label">Пропущенные флаги</div>', unsafe_allow_html=True)
            for f in report['flags_skipped']:
                st.markdown(
                    f'<div style="margin:0.3rem 0;font-size:0.88rem;">'
                    f'<span class="mono" style="color:var(--accent);">{f["name"]}</span> '
                    f'<span style="color:var(--text-dim);">— {f["reason"]}</span></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="section-label">Все флаги вычислены</div>', unsafe_allow_html=True)
            st.markdown('<div style="color:var(--mint);font-family:JetBrains Mono;">✓ полный набор</div>', unsafe_allow_html=True)

# =====================================================================
# ВКЛАДКИ
# =====================================================================
tab_summary, tab_registry, tab_detail = st.tabs(["Сводка", "Реестр", "Абонент"])

# ----- СВОДКА -----
with tab_summary:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-label">Распределение</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">По числу флагов</div>', unsafe_allow_html=True)
        flag_counts = registry['кол-во_флагов'].value_counts().sort_index()
        # градиент: 0 — серый, 1 — мята, 2 — жёлтый, 3+ — коралл
        scale = {0: SUBTLE, 1: MINT, 2: ACCENT, 3: AMBER, 4: CORAL, 5: CORAL}
        colors = [scale.get(int(k), CORAL) for k in flag_counts.index]
        fig = go.Figure(go.Bar(
            x=flag_counts.index.astype(int).astype(str), y=flag_counts.values,
            text=flag_counts.values, textposition='outside',
            marker=dict(color=colors, line=dict(color=colors, width=0)),
            textfont=dict(family='JetBrains Mono', color='#ececf0', size=12),
            hovertemplate='<b>%{x} флагов</b><br>%{y} абонентов<extra></extra>',
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=320,
                          xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col2:
        st.markdown('<div class="section-label">Срабатывание</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Каждого флага</div>', unsafe_allow_html=True)
        flag_names = [f['name'] for f in FLAG_DEFINITIONS if f['name'] in flags.columns]
        flag_data = sorted(
            [(FLAG_TITLES.get(n, n), int(flags[n].sum()), FLAG_COLOR.get(n, CORAL)) for n in flag_names],
            key=lambda x: x[1]
        )
        fig2 = go.Figure(go.Bar(
            y=[t for t, _, _ in flag_data],
            x=[v for _, v, _ in flag_data],
            text=[v for _, v, _ in flag_data],
            textposition='outside',
            orientation='h',
            marker=dict(color=[c for _, _, c in flag_data]),
            textfont=dict(family='JetBrains Mono', color='#ececf0', size=12),
            hovertemplate='<b>%{y}</b><br>%{x} абонентов<extra></extra>',
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=320,
                           xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    st.markdown('<div class="section-label">Сезонная классификация</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">По характеру потребления</div>', unsafe_allow_html=True)
    seas = registry['сезонность'].value_counts()
    season_color = {'круглогодичный': MINT, 'летний (дача)': ACCENT,
                    'зимний (отопление)': CORAL, 'нет данных': SUBTLE}
    fig3 = go.Figure(go.Bar(
        x=seas.index, y=seas.values, text=seas.values, textposition='outside',
        marker_color=[season_color.get(k, SUBTLE) for k in seas.index],
        textfont=dict(family='JetBrains Mono', color='#ececf0', size=12),
        hovertemplate='<b>%{x}</b><br>%{y} абонентов<extra></extra>',
    ))
    fig3.update_layout(**PLOTLY_LAYOUT, height=280,
                       xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

# ----- РЕЕСТР -----
with tab_registry:
    st.markdown('<div class="section-label">Реестр</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Абоненты с флагами</div>', unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([1, 1.2, 2])
    with fc1:
        min_flags = st.number_input("Мин. флагов", 0, 10, 1, 1)
    with fc2:
        seasons = ['(все)'] + list(registry['сезонность'].unique())
        season_filter = st.selectbox("Сезонность", seasons)
    with fc3:
        active_flag_filter = st.multiselect(
            "Только с этими флагами (И)",
            options=[c for c in flags.columns],
            format_func=lambda x: f"{FLAG_EMOJI.get(x,'')} {FLAG_TITLES.get(x, x)}",
        )

    view = registry[registry['кол-во_флагов'] >= min_flags].copy()
    if season_filter != '(все)':
        view = view[view['сезонность'] == season_filter]
    for fn in active_flag_filter:
        view = view[view[fn] == True]

    display_view = view.rename(columns={
        **METRIC_LABELS,
        **{k: f"{FLAG_EMOJI.get(k,'')} {FLAG_TITLES.get(k,k)}" for k in flags.columns},
    })

    st.markdown(
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.78rem;'
        f'color:var(--text-dim);text-transform:uppercase;letter-spacing:0.14em;'
        f'margin:0.5rem 0 0.8rem 0;">'
        f'Показано <span style="color:var(--accent);">{len(view):,}</span> из {len(registry):,} абонентов'
        f'</div>',
        unsafe_allow_html=True
    )
    st.dataframe(display_view, use_container_width=True, height=480)

    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine='openpyxl') as w:
        display_view.to_excel(w, index=False, sheet_name='Реестр')
    st.download_button(
        "Скачать реестр (Excel)",
        data=excel_buf.getvalue(),
        file_name="реестр_аномалий.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ----- АБОНЕНТ -----
with tab_detail:
    st.markdown('<div class="section-label">Детальный просмотр</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">График и метрики абонента</div>', unsafe_allow_html=True)

    def label(idx):
        r = registry.loc[idx]
        parts = []
        for col in ['Заводской номер прибора учета', 'Наименование точки учета',
                    'Населенный пункт', 'Улица', 'Дом']:
            if col in r and pd.notna(r[col]):
                parts.append(str(r[col]))
        flags_n = int(r.get('кол-во_флагов', 0))
        suffix = f"  ⚑ {flags_n}" if flags_n else ""
        return f"#{idx} · {' · '.join(parts) if parts else 'без идентификатора'}{suffix}"

    sorted_idx = registry.sort_values('кол-во_флагов', ascending=False).index.tolist()
    selected = st.selectbox("Абонент", options=sorted_idx, format_func=label,
                            label_visibility="collapsed")

    if selected is not None:
        month_info = detect_month_columns(df_raw)
        month_cols = [c for (c, _, _) in month_info]
        periods = [pd.Period(f"{y}-{m:02d}", freq='M') for (_, y, m) in month_info]
        s = pd.to_numeric(df_raw.loc[selected, month_cols], errors='coerce')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[p.to_timestamp() for p in periods], y=s.values,
            mode='lines+markers',
            line=dict(color=ACCENT, width=1.6),
            marker=dict(size=5, color=ACCENT, line=dict(color='#0a0b0f', width=1)),
            connectgaps=False,
            fill='tozeroy',
            fillcolor='rgba(245, 212, 66, 0.08)',
            hovertemplate='<b>%{x|%b %Y}</b><br>%{y:,.0f} кВт·ч<extra></extra>',
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=400,
                          xaxis_title=None, yaxis_title='кВт·ч')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        c1, c2 = st.columns(2)

        with c1:
            st.markdown('<div class="section-label">Активные флаги</div>', unsafe_allow_html=True)
            row_flags = [n for n in flags.columns if flags.loc[selected, n]]
            if row_flags:
                html = ""
                for n in row_flags:
                    color = FLAG_COLOR.get(n, ACCENT)
                    html += (f'<div class="flag-row" style="--flag-color:{color};">'
                             f'<span class="emoji">{FLAG_EMOJI.get(n,"🚩")}</span>'
                             f'<span class="name">{FLAG_TITLES.get(n,n)}</span></div>')
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown('<div class="flag-empty">✓ Без флагов</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-label" style="margin-top:1.6rem;">Ключевые метрики</div>', unsafe_allow_html=True)
            metric_keys = ['active_months', 'mean_kwh', 'avg_recent', 'avg_baseline',
                           'drop_ratio', 'longest_silence', 'longest_flat_run',
                           'power_ratio', 'cohort_z', 'сезонность']
            html = '<div class="kv-list">'
            for k in metric_keys:
                if k in registry.columns:
                    v = registry.loc[selected, k]
                    if pd.notna(v):
                        if isinstance(v, (int, float, np.floating)):
                            v_fmt = f"{v:,.2f}" if isinstance(v, float) else f"{v:,}"
                        else:
                            v_fmt = str(v)
                        html += (f'<div class="kv-row">'
                                 f'<span class="kv-key">{METRIC_LABELS.get(k,k)}</span>'
                                 f'<span class="kv-val">{v_fmt}</span></div>')
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="section-label">Метаданные</div>', unsafe_allow_html=True)
            html = '<div class="kv-list">'
            meta_cols = ['Вид потребителя', 'Заводской номер прибора учета',
                         'Наименование точки учета', 'Населенный пункт',
                         'Улица', 'Дом', 'Разрешенная мощность',
                         'Тип события', 'Дата события']
            for col in meta_cols:
                if col in registry.columns:
                    v = registry.loc[selected, col]
                    if pd.notna(v):
                        html += (f'<div class="kv-row">'
                                 f'<span class="kv-key">{col}</span>'
                                 f'<span class="kv-val">{v}</span></div>')
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

# =====================================================================
# ПОДВАЛ
# =====================================================================
st.markdown("""
<div class="footer-strip">
  Прототип · Данные не сохраняются · Работает в браузере
</div>
""", unsafe_allow_html=True)
