import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

st.set_page_config(layout="wide")

@st.cache_data
def load_data(path="crimea_bridge.csv"):
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
    df["hour"] = df["time"].str.slice(0,2).astype(int)
    
    # Получаем список доступных дат
    available_dates = sorted(df["date"].dt.date.unique())
    return df, available_dates

# Загружаем данные и доступные даты
df, available_dates = load_data()

# Устанавливаем направление по умолчанию
if "selected_direction" not in st.session_state:
    st.session_state.selected_direction = "to_crimea"

# Устанавливаем дату по умолчанию (последняя доступная)
if "selected_date" not in st.session_state:
    st.session_state.selected_date = available_dates[-1]

direction_map = {
    "В Крым": "to_crimea",
    "Из Крыма": "from_crimea"
}

direction_rus = st.radio(
    "Выберите направление",
    options=list(direction_map.keys()),
    index=0 if st.session_state.selected_direction == "to_crimea" else 1,
    horizontal=True
)

st.session_state.selected_direction = direction_map[direction_rus]

def change_date(delta):
    """Изменяет дату с учетом доступных дат"""
    current_index = available_dates.index(st.session_state.selected_date)
    new_index = current_index + delta
    
    # Проверяем границы диапазона
    if 0 <= new_index < len(available_dates):
        st.session_state.selected_date = available_dates[new_index]

# Создаем компактный блок управления датой с центрированием
st.markdown("""
    <style>
    .date-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    .date-nav {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
    }
    .nav-button {
        padding: 0;
        margin: 0;
        height: 48px;
        width: 48px;
        font-size: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
    }
    .date-input {
        height: 48px;
        width: 5px;
        padding: 12px 14px;
        font-size: 16px;
        border: 1px solid #ccc;
        border-radius: 4px;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-title {
        font-size: 14px;
        color: #555;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-wait {
        color: #ff7f0e;
    }
    </style>
""", unsafe_allow_html=True)

# Контейнер для центрирования
st.markdown('<div class="date-container">', unsafe_allow_html=True)
st.markdown('<div class="date-nav">', unsafe_allow_html=True)

# Кнопка "назад"
prev_disabled = available_dates.index(st.session_state.selected_date) == 0
prev_button = st.button("←", disabled=prev_disabled, key="prev_date")
if prev_button:
    change_date(-1)

# Календарь с ограничением выбора только доступными датами
new_date = st.date_input(
    "Выберите дату",
    value=st.session_state.selected_date,
    min_value=available_dates[0],
    max_value=available_dates[-1],
    format="DD.MM.YYYY",
    key="date_picker",
    label_visibility="collapsed"
)

# Обновляем выбранную дату
if new_date in available_dates:
    st.session_state.selected_date = new_date
else:
    st.warning(f"Нет данных за {new_date.strftime('%d.%m.%Y')}")

# Кнопка "вперед"
next_disabled = available_dates.index(st.session_state.selected_date) == len(available_dates) - 1
next_button = st.button("→", disabled=next_disabled, key="next_date")
if next_button:
    change_date(1)

st.markdown('</div>', unsafe_allow_html=True)  # Закрываем date-nav
st.markdown('</div>', unsafe_allow_html=True)  # Закрываем date-container

# Фильтруем данные по выбранной дате
filtered_df = df[df["date"].dt.date == st.session_state.selected_date]

# Создаем данные для графика
hours = list(range(24))
counts = []
waits = []

col_count = st.session_state.selected_direction
col_wait = col_count + "_wait"

for h in hours:
    row = filtered_df[filtered_df["hour"] == h]
    if not row.empty:
        # Обработка значений количества машин
        count_val = row[col_count].values[0]
        if pd.notna(count_val):
            counts.append(max(0, int(count_val)))
        else:
            counts.append(0)
        
        # Обработка значений времени ожидания
        wait_val = row[col_wait].values[0]
        if pd.notna(wait_val):
            # Преобразуем строки в числа, если необходимо
            if isinstance(wait_val, str):
                # Убираем текст и оставляем только цифры
                wait_val = ''.join(filter(str.isdigit, wait_val))
                wait_val = float(wait_val) if wait_val else 0
            waits.append(max(0, float(wait_val)))
        else:
            waits.append(0)
    else:
        counts.append(0)
        waits.append(0)

# Создаем график
fig = go.Figure()

# График количества машин
fig.add_trace(go.Scatter(
    x=hours,
    y=counts,
    name="Количество машин",
    yaxis="y1",
    mode="lines+markers",
    line=dict(color="blue", width=3),
    marker=dict(size=8)
))

# График времени ожидания
fig.add_trace(go.Scatter(
    x=hours,
    y=waits,
    name="Часы ожидания",
    yaxis="y2",
    mode="lines+markers",
    line=dict(color="red", width=3),
    marker=dict(size=8)
))

# Вычисляем безопасные границы для осей
y1_max = max(counts) * 1.2 if counts and max(counts) > 0 else 100
y2_max = max(waits) * 1.2 if waits and max(waits) > 0 else 5

# Настраиваем макет с гарантией положительных значений
fig.update_layout(
    title=f"Данные за {st.session_state.selected_date.strftime('%d.%m.%Y')} | Направление: {direction_rus}",
    xaxis=dict(
        title="Часы",
        tickmode="array",
        tickvals=list(range(0, 24, 2)),
        range=[0, 23],
        tickfont=dict(size=12)
    ),
    yaxis=dict(
        title="Количество машин",
        range=[0, y1_max],
        showgrid=False,
        zeroline=False,
        side="left"
    ),
    yaxis2=dict(
        title="Часы ожидания",
        range=[0, y2_max],
        overlaying="y",
        side="right",
        showgrid=False,
        zeroline=False,
    ),
    legend=dict(x=0.1, y=1.15, orientation="h"),
    height=500,
    margin=dict(l=50, r=50, t=100, b=50),
    showlegend=True,
    modebar={'remove': ['zoom', 'pan', 'select', 'zoomIn', 'zoomOut', 'resetScale', 'autoScale', 'toImage']}
)

# Отключаем интерактивные элементы Plotly
fig.update_layout(dragmode=False)

# Отображаем график
st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# Ключевые метрики
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Всего машин за сутки</div>
            <div class="metric-value">{sum(counts)}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Максимальное время ожидания</div>
            <div class="metric-value metric-wait">{max(waits) if waits else 0:.1f} часов</div>
        </div>
    """, unsafe_allow_html=True)