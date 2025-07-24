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

# Проверяем, является ли выбранная дата текущей (последней доступной)
is_current_date = st.session_state.selected_date == available_dates[-1]

if is_current_date:
    # Для текущей даты - находим последний час с данными
    last_hour = filtered_df[filtered_df[st.session_state.selected_direction].notna()]["hour"].max()
    if pd.isna(last_hour):
        last_hour = 0  # если нет данных вообще
    else:
        last_hour = int(last_hour)
    
    # Создаем список часов от (last_hour-23) до last_hour
    hours = [(last_hour - 23 + i) % 24 for i in range(24)]
    # Корректируем отрицательные значения
    hours = [h if h >= 0 else h + 24 for h in hours]
    
    # Создаем метки для оси X
    x_labels = [f"{h:02d}:00" for h in hours]
    
    # Собираем данные в правильном порядке
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
                if isinstance(wait_val, str):
                    wait_val = ''.join(filter(str.isdigit, wait_val))
                    wait_val = float(wait_val) if wait_val else 0
                waits.append(max(0, float(wait_val)))
            else:
                waits.append(0)
        else:
            counts.append(0)
            waits.append(0)
    
    x_axis = x_labels
    x_title = f"Время (последние 24 часа до {last_hour:02d}:00)"
else:
    # Для не текущих дат - стандартный график 00:00-23:00
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
                if isinstance(wait_val, str):
                    wait_val = ''.join(filter(str.isdigit, wait_val))
                    wait_val = float(wait_val) if wait_val else 0
                waits.append(max(0, float(wait_val)))
            else:
                waits.append(0)
        else:
            counts.append(0)
            waits.append(0)
    
    x_axis = [f"{h:02d}:00" for h in hours]
    x_title = "Часы (00:00-23:00)"

# Создаем график
fig = go.Figure()

# График количества машин
fig.add_trace(go.Scatter(
    x=x_axis,
    y=counts,
    name="Количество машин",
    yaxis="y1",
    mode="lines+markers",
    line=dict(color="blue", width=3),
    marker=dict(size=8)
))

# График времени ожидания
fig.add_trace(go.Scatter(
    x=x_axis,
    y=waits,
    name="Часы ожидания",
    yaxis="y2",
    mode="lines+markers",
    line=dict(color="red", width=3),
    marker=dict(size=8)
))

# Фиксированные параметры осей
y1_range = [0, 1500]  # Фиксированный диапазон для количества машин
y1_tickvals = list(range(0, 1501, 100))  # Шаг 100 для оси количества машин

y2_range = [0, 5]  # Фиксированный диапазон для времени ожидания
y2_tickvals = list(range(0, 6, 1))  # Шаг 1 для оси времени ожидания

# Настраиваем макет с фиксированными шкалами
fig.update_layout(
    title=f"Данные за {st.session_state.selected_date.strftime('%d.%m.%Y')} | Направление: {direction_rus}",
    xaxis=dict(
        title=x_title,
        tickmode="array",
        tickvals=x_axis[::2],
        tickfont=dict(size=10),
        tickangle=45
    ),
    yaxis=dict(
        title="Количество машин",
        range=y1_range,
        tickvals=y1_tickvals,
        showgrid=True,
        zeroline=False,
        side="left"
    ),
    yaxis2=dict(
        title="Часы ожидания",
        range=y2_range,
        tickvals=y2_tickvals,
        overlaying="y",
        side="right",
        showgrid=False,
        zeroline=False,
    ),
    legend=dict(x=0.1, y=1.15, orientation="h"),
    height=500,
    margin=dict(l=50, r=50, t=100, b=100),
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
