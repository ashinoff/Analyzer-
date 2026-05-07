"""
Streamlit-приложение: анализ аномального потребления.
Эстетика: editorial dark, диспетчерская энергосистемы.
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

# =====================================================================
# СТИЛИ
# =====================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,600;9..144,800&family=Manrope:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
    --bg: #0a0b0f;
    --surface: #13141a;
    --surface-2: #1c1d24;
    --border: #262830;
    --border-soft: #1c1d24;
    --text: #e8e9ed;
    --text-dim: #8a8d99;
    --text-faint: #5a5d68;
    --accent: #f5d442;
    --accent-dim: #c9ad36;
    --danger: #ff7b72;
    --good: #6dcf91;
}

html, body, [class*="css"] {
    font-family: 'Manrope', system-ui, sans-serif !important;
    color: var(--text);
}

.stApp { background: var(--bg); }

/* убрать дефолтный header Streamlit */
header[data-testid="stHeader"] { background: transparent; }
.stDeployButton { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

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

/* шапка — журнальный стиль */
.hero {
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    padding: 1.4rem 0;
    margin-bottom: 1.8rem;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 2rem;
}
.hero-title {
    font-family: 'Fraunces', serif;
    font-weight: 800;
    font-size: 2.6rem;
    letter-spacing: -0.03em;
    line-height: 1;
    margin: 0;
}
.hero-title em {
    font-style: italic;
    font-weight: 300;
    color: var(--accent);
}
.hero-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    text-align: right;
    line-height: 1.6;
    white-space: nowrap;
}
.hero-meta b { color: var(--accent); font-weight: 500; }

/* лента метрик — без плиток, как в газете */
.metric-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.metric-cell {
    padding: 1.2rem 1.4rem;
    border-right: 1px solid var(--border);
}
.metric-cell:last-child { border-right: none; }
.metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: var(--text-dim);
    margin-bottom: 0.45rem;
}
.metric-value {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 2.4rem;
    line-height: 1;
    color: var(--text);
}
.metric-value.accent { color: var(--accent); }

/* секционные заголовки */
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--text-dim);
    margin: 2rem 0 0.6rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}
.section-title {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.5rem;
    line-height: 1.1;
    margin: 0.2rem 0 1.2rem 0;
}

/* флаги — карточки */
.flag-row {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.4rem;
    background: var(--surface);
    border-left: 3px solid var(--accent);
    border-radius: 2px;
}
.flag-row .emoji { font-size: 1.05rem; }
.flag-row .name { font-weight: 500; color: var(--text); }
.flag-empty {
    padding: 0.7rem 0.9rem;
    color: var(--good);
    background: rgba(109, 207, 145, 0.07);
    border-left: 3px solid var(--good);
    border-radius: 2px;
}

/* карточка-список */
.kv-list { font-family: 'Manrope', sans-serif; }
.kv-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.5rem 0;
    border-bottom: 1px dashed var(--border-soft);
    gap: 1rem;
}
.kv-row:last-child { border-bottom: none; }
.kv-key {
    color: var(--text-dim);
    font-size: 0.85rem;
}
.kv-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.92rem;
    color: var(--text);
    text-align: right;
    word-break: break-word;
}

/* таблицы */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 2px;
}

/* tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    padding: 0.8rem 1.2rem;
    color: var(--text-dim);
    background: transparent;
    border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* sidebar */
[data-testid="stSidebar"] {
    background: var(--surface);
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] h1 {
    font-family: 'Fraunces', serif !important;
    font-size: 1.4rem !important;
    margin-bottom: 0.4rem;
}

/* кнопки */
.stDownloadButton button, .stButton button {
    background: var(--accent) !important;
    color: var(--bg) !important;
    border: none !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    padding: 0.6rem 1.4rem !important;
    border-radius: 2px !important;
}
.stDownloadButton button:hover, .stButton button:hover {
    background: #ffe055 !important;
}

/* file uploader */
[data-testid="stFileUploaderDropzone"] {
    background: var(--surface) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 2px !important;
}

/* status-pills для отчёта о загрузке */
.pill {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 2px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    margin: 0.15rem 0.2rem 0.15rem 0;
    border: 1px solid var(--border);
}
.pill.found { color: var(--good); border-color: rgba(109, 207, 145, 0.3); }
.pill.miss  { color: var(--text-dim); }

/* инфо-блоки заглушек */
.empty-state {
    border: 1px dashed var(--border);
    padding: 2.5rem;
    text-align: center;
    color: var(--text-dim);
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-size: 1.1rem;
    margin: 1rem 0;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =====================================================================
# Plotly-тема под общий стиль
# =====================================================================
PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='JetBrains Mono, monospace', color='#8a8d99', size=11),
    xaxis=dict(gridcolor='#1c1d24', linecolor='#262830', zerolinecolor='#262830',
               tickfont=dict(color='#8a8d99')),
    yaxis=dict(gridcolor='#1c1d24', linecolor='#262830', zerolinecolor='#262830',
               tickfont=dict(color='#8a8d99')),
    margin=dict(l=10, r=10, t=20, b=10),
    showlegend=False,
)

ACCENT = '#f5d442'
DANGER = '#ff7b72'
SUBTLE = '#3a3d48'

# =====================================================================
# САЙДБАР: ПОРОГИ
# =====================================================================
with st.sidebar:
    st.markdown("# Настройки")
    st.markdown('<div style="color:var(--text-dim);font-size:0.85rem;margin-bottom:1.2rem;">Подкручивайте — таблица пересчитается.</div>', unsafe_allow_html=True)

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
- `Заводской номер ПУ`, `Наименование точки учета`, адресные поля — для удобства идентификации
- `Тип события`, `Дата события` — пока заложено, не используется

**Какие флаги считаются:**
- 🔻 Подозрение на хищение — резкое устойчивое падение vs опорный период
- 🔇 Долгое молчание ПУ — длинные пропуски в показаниях
- ⚡ Превышение мощности — пиковое потребление выше разрешённой
- 📊 Нестабильность — высокий коэффициент вариации
- 📐 Одинаковые числа подряд — подозрение на ручной ввод «по нормативу»
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
# ЛЕНТА МЕТРИК (вместо st.metric)
# =====================================================================
n_with_flags = int((registry['кол-во_флагов'] > 0).sum())
n_high_risk = int((registry['кол-во_флагов'] >= 3).sum())

st.markdown(f"""
<div class="metric-strip">
  <div class="metric-cell">
    <div class="metric-label">Абонентов в файле</div>
    <div class="metric-value">{report['total_rows']:,}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Месяцев данных</div>
    <div class="metric-value">{report['months_detected']}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">С флагами</div>
    <div class="metric-value accent">{n_with_flags:,}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Высокий риск (3+ флага)</div>
    <div class="metric-value accent">{n_high_risk:,}</div>
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
            st.markdown('<div style="color:var(--good);">✓ полный набор</div>', unsafe_allow_html=True)

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
        colors = [SUBTLE if k == 0 else ACCENT for k in flag_counts.index]
        fig = go.Figure(go.Bar(
            x=flag_counts.index.astype(int).astype(str), y=flag_counts.values,
            text=flag_counts.values, textposition='outside',
            marker_color=colors,
            textfont=dict(family='JetBrains Mono', color='#e8e9ed', size=12),
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=320,
                          xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col2:
        st.markdown('<div class="section-label">Срабатывание</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Каждого флага</div>', unsafe_allow_html=True)
        flag_names = [f['name'] for f in FLAG_DEFINITIONS if f['name'] in flags.columns]
        flag_sums = sorted([(FLAG_TITLES.get(n, n), int(flags[n].sum())) for n in flag_names],
                           key=lambda x: x[1])
        fig2 = go.Figure(go.Bar(
            y=[n for n, _ in flag_sums], x=[v for _, v in flag_sums],
            text=[v for _, v in flag_sums], textposition='outside',
            orientation='h', marker_color=DANGER,
            textfont=dict(family='JetBrains Mono', color='#e8e9ed', size=12),
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=320,
                           xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    st.markdown('<div class="section-label">Сезонная классификация</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">По характеру потребления</div>', unsafe_allow_html=True)
    seas = registry['сезонность'].value_counts()
    season_color = {'круглогодичный': '#6dcf91', 'летний (дача)': '#f5d442',
                    'зимний (отопление)': '#ff7b72', 'нет данных': SUBTLE}
    fig3 = go.Figure(go.Bar(
        x=seas.index, y=seas.values, text=seas.values, textposition='outside',
        marker_color=[season_color.get(k, SUBTLE) for k in seas.index],
        textfont=dict(family='JetBrains Mono', color='#e8e9ed', size=12),
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

    # переименовать колонки на русский для отображения
    display_view = view.rename(columns={
        **METRIC_LABELS,
        **{k: f"{FLAG_EMOJI.get(k,'')} {FLAG_TITLES.get(k,k)}" for k in flags.columns},
    })

    st.markdown(
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.78rem;'
        f'color:var(--text-dim);text-transform:uppercase;letter-spacing:0.12em;'
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
            line=dict(color=ACCENT, width=1.4),
            marker=dict(size=4, color=ACCENT),
            connectgaps=False,
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=380,
                          xaxis_title=None, yaxis_title='кВт·ч')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        c1, c2 = st.columns(2)

        with c1:
            st.markdown('<div class="section-label">Активные флаги</div>', unsafe_allow_html=True)
            row_flags = [n for n in flags.columns if flags.loc[selected, n]]
            if row_flags:
                html = ""
                for n in row_flags:
                    html += (f'<div class="flag-row">'
                             f'<span class="emoji">{FLAG_EMOJI.get(n,"🚩")}</span>'
                             f'<span class="name">{FLAG_TITLES.get(n,n)}</span></div>')
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown('<div class="flag-empty">✓ Без флагов</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-label" style="margin-top:1.5rem;">Ключевые метрики</div>', unsafe_allow_html=True)
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
<div style="margin-top:3rem;padding:1rem 0;border-top:1px solid var(--border);
            font-family:'JetBrains Mono',monospace;font-size:0.7rem;
            color:var(--text-faint);text-transform:uppercase;letter-spacing:0.18em;
            text-align:center;">
  Прототип · Данные не сохраняются · Работает в браузере
</div>
""", unsafe_allow_html=True)
