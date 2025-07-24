import streamlit as st
import pandas as pd

st.set_page_config(page_title="Мост в Крым", layout="wide")

st.title("Мониторинг очередей на мосту в Крым")

# Загружаем CSV
@st.cache_data
def load_data():
    df = pd.read_csv("crimea_bridge.csv")
    df['datetime'] = pd.to_datetime(df['date'] + " " + df['time'], 
format="%d.%m.%Y %H:%M")
    return df

data = load_data()

# Отображаем таблицу
st.subheader("Последние данные")
st.dataframe(data.sort_values(by="datetime", ascending=False))

# Графики
st.subheader("График ожидания (время в часах)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**На въезд в Крым (со стороны Тамани)**")
    
st.line_chart(data.set_index('datetime')["to_crimea_wait"].dropna().apply(lambda 
x: float(x.split()[1])))

with col2:
    st.markdown("**На выезд из Крыма (со стороны Керчи)**")
    
st.line_chart(data.set_index('datetime')["from_crimea_wait"].dropna().apply(lambda 
x: float(x.split()[1])))

