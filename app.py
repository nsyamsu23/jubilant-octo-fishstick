import streamlit as st
from g4f.client import Client
import requests
import json
import pandas as pd
import datetime
import pytz

st.set_page_config(page_title="Backtesting GPT", layout="wide")
LOCAL_TIMEZONE = "Asia/Jakarta"

# Fungsi untuk mengambil data berita dari Fastbull
def get_fastbull_news(checkImportant=0, pageSize=1000, timestamp=None, includeCalendar=1):
    url = "https://api.fastbull.com/fastbull-news-service/api/getNewsPageByTagIds"
    params = {"checkImportant": checkImportant, "pageSize": pageSize, "timestamp": timestamp or "", "includeCalendar": includeCalendar}
    headers = {"Langid": "13"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 0:
            return json.loads(data['bodyMessage'])['pageDatas']
    return None

client = Client()

col1, col2 = st.columns([2, 1])

# Kolom 1: Berita Fastbull
with col1:
    st.header("📢 News")
    col_time11, col_time2, col_time3, col_time4 = st.columns(4)
    with col_time11:
        selected_date = st.date_input("Pilih Tanggal", datetime.datetime.now())
    with col_time2:
        selected_hour = st.number_input("Jam", min_value=0, max_value=23, value=0, step=1)
    with col_time3:
        selected_minute = st.number_input("Menit", min_value=0, max_value=59, value=0, step=1)
    with col_time4:
        selected_second = st.number_input("Detik", min_value=0, max_value=59, value=0, step=1)

    combined_datetime = datetime.datetime(
        selected_date.year, selected_date.month, selected_date.day,
        selected_hour, selected_minute, selected_second
    )

    local_tz = pytz.timezone(LOCAL_TIMEZONE)
    dt_localized = local_tz.localize(combined_datetime)
    dt_utc = dt_localized.astimezone(pytz.utc)
    timestamp = int(dt_utc.timestamp() * 1000)

    st.write(f"**Waktu UTC:** {dt_utc}, **Waktu Lokal ({LOCAL_TIMEZONE}):** {dt_localized}, **Timestamp (ms):** {timestamp}")

    if st.button("Ambil Data"):
        news_data = get_fastbull_news(timestamp=timestamp)
        if news_data:
            st.session_state["news_data"] = pd.DataFrame([
                {"releasedDate": item["releasedDate"], "newsTitle": item["newsTitle"], "important": item["important"]}
                for item in news_data
            ])
        else:
            st.warning("Data tidak tersedia atau terjadi kesalahan dalam mengambil data.")

    if "news_data" in st.session_state:
        df = st.session_state["news_data"].copy()
        df["releasedDate"] = pd.to_datetime(df["releasedDate"], unit='ms').dt.tz_localize('UTC').dt.tz_convert(LOCAL_TIMEZONE)
        
        # Mengatur tampilan DataFrame agar memanjang ke bawah
        st.write("Total Berita:", len(df))
        
        # Menambahkan pengaturan tampilan untuk DataFrame
        st.dataframe(
            df.style.apply(
                lambda x: ['background-color: red; color: white;' if v == 1 else '' for v in df["important"]], 
                axis=0
            ),
            use_container_width=True,
            height=10000  # Menambahkan tinggi tetap untuk scrolling
        )

# Kolom 2: Chatbot GPT
with col2:
    st.header("🤖 Chatbot GPT")
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    chat_container = st.container()
    with chat_container:
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    prompt = st.chat_input("Ask a question...")
    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": """\n
You are a helpful financial assistant working for Example Co.
Your name is "Example Copilot", and you were trained by Example Co.
You will do your best to answer the user's query.

Use the following guidelines:
- Formal and Professional Tone: Maintain a business-like, sophisticated tone, suitable for a professional audience.
- Clarity and Conciseness: Keep explanations clear and to the point, avoiding unnecessary complexity.
- Focus on Expertise and Experience: Emphasize expertise and real-world experiences, using direct quotes to add a personal touch.
- Subject-Specific Jargon: Use industry-specific terms, ensuring they are accessible to a general audience through explanations.
- Narrative Flow: Ensure a logical flow, connecting ideas and points effectively.
- Incorporate Statistics and Examples: Support points with relevant statistics, examples, or case studies for real-world context.
- Provide Actionable Advice: Offer practical, actionable advice that the user can implement immediately.
- Encourage Engagement: Encourage the user to ask more questions, guiding them to explore further topics.
- professional, sophisticated, clear, concise, expertise, experience, direct quotes, jargon, narrative flow, statistics, examples, actionable advice, engagement


"""},
                        *st.session_state["messages"]
                    ],
                    web_search=False
                )
                response_text = response.choices[0].message.content
                st.markdown(response_text)
        st.session_state["messages"].append({"role": "assistant", "content": response_text})
