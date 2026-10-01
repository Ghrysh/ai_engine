import streamlit as st
import pandas as pd
import torch
import altair as alt
import plotly.express as px
from urllib.parse import quote_plus
from streamlit_autorefresh import st_autorefresh
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer, util
import time

st.set_page_config(page_title="EWS Conflict - Orchestrator", layout="wide")

# 2. Autorefresh (Real-time setiap 30 detik)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=1000, key="ews_counter")
except ImportError:
    st.warning("⚠️ Library 'streamlit-autorefresh' tidak ditemukan. Jalankan: pip install streamlit-autorefresh")

encoded_password = quote_plus("p@5s@i_3n9ine")
DB_URL = f"postgresql://ai_engine:{encoded_password}@db:5432/ai_engine_db"
engine = create_engine(DB_URL)

df_display = pd.DataFrame()
df_audit = pd.DataFrame()
df_chart = pd.DataFrame()


@st.cache_resource
def load_ai():
    try:
        return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    except Exception as e:
        st.error(f"Gagal memuat model AI: {e}")
        return None


try:
    model_ai = load_ai()
except:
    model_ai = None


def init_db():
    """Inisialisasi seluruh tabel database untuk mendukung Layer 1-4 [cite: 5, 8]"""
    queries = [
        # Layer 1 - Data Mentah & Intensitas
        """CREATE TABLE IF NOT EXISTS social_media_reports (
            id SERIAL PRIMARY KEY, 
            source TEXT, 
            title TEXT, 
            content TEXT, 
            url TEXT, 
            platform TEXT,
            location TEXT,
            latitude FLOAT,
            longitude FLOAT,
            intensity FLOAT DEFAULT 1.0, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        "ALTER TABLE social_media_reports ADD COLUMN IF NOT EXISTS intensity FLOAT DEFAULT 1.0;",
        
        # Layer 1 - Statistik Risiko
        """CREATE TABLE IF NOT EXISTS risk_statistics (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            keyword TEXT,
            jumlah FLOAT,
            platform TEXT,
            location TEXT,
            latitude FLOAT,
            longitude FLOAT
        );""", # <--- Pastikan ada koma di sini
        
        # Tabel Matriks Indikator Utama
        """CREATE TABLE IF NOT EXISTS matrix_indicators (
            id SERIAL PRIMARY KEY,
            dimensi TEXT,
            sub_dimensi TEXT,
            deskripsi TEXT,
            indikator TEXT,
            fase_laten TEXT,
            fase_persepsi TEXT,
            fase_manifes TEXT,
            fase_eskalasi TEXT,
            fase_krisis TEXT
        );""",
        
        # Layer 4 - Pengaduan Masyarakat
        """CREATE TABLE IF NOT EXISTS public_complaints (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wilayah TEXT,
            kategori TEXT,
            isi_aduan TEXT,
            sumber_aduan TEXT
        );""",
        
        # Layer 2 - Statistik Emosi
        """CREATE TABLE IF NOT EXISTS emotion_statistics (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            emotion TEXT,
            platform TEXT,
            count INTEGER
        );""",
        
        # Layer 3 - Akselerasi Viral
        """CREATE TABLE IF NOT EXISTS viral_acceleration (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            platform TEXT,
            velocity INTEGER,
            unique_users INTEGER,
            batch_id TEXT
        );"""
    ]
    try:
        with engine.begin() as conn:
            for query in queries:
                conn.execute(text(query))
    except Exception as e:
        st.error(f"Database Connection/Init Error: {e}")


def get_all_data():
    try:
        init_db()
        with engine.connect() as conn:
            return pd.read_sql("SELECT * FROM matrix_indicators ORDER BY id DESC", conn)
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")
        return pd.DataFrame()


def save_as_complaint(content, source="Manual Orchestrator"):
    query = text(
        """
        INSERT INTO public_complaints (wilayah, kategori, isi_aduan, sumber_aduan)
        VALUES (:w, :k, :i, :s)
    """
    )
    try:
        with engine.begin() as conn:
            conn.execute(
                query,
                {
                    "w": "Nasional (Manual)",
                    "k": "Potensi Konflik Keagamaan",
                    "i": content,
                    "s": source,
                },
            )
    except Exception as e:
        st.error(f"Gagal mencatat ke data aduan: {e}")


def get_scraped_data_formatted(platform_filter):
    try:
        with engine.connect() as conn:
            if platform_filter == "YouTube":
                query = text(
                    """
                    SELECT DISTINCT title, source, url 
                    FROM social_media_reports 
                    WHERE source NOT IN ('Instagram') 
                    AND (source LIKE '%@%' OR source LIKE '%Channel%' OR source = 'YouTube')
                    ORDER BY title ASC
                """
                )
                return pd.read_sql(query, conn)
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


def get_youtube_channels():
    try:
        with engine.connect() as conn:
            query = text(
                """
                SELECT DISTINCT source 
                FROM social_media_reports 
                WHERE source NOT IN ('Instagram') 
                AND source NOT LIKE '%News%'
                AND (source LIKE '%@%' OR source LIKE '%Channel%')
            """
            )
            df = pd.read_sql(query, conn)
            return df["source"].tolist()
    except:
        return []


def get_videos_by_channel(channel_name):
    try:
        with engine.connect() as conn:
            query = text(
                "SELECT DISTINCT title FROM social_media_reports WHERE source = :s"
            )
            return pd.read_sql(query, conn, params={"s": channel_name})[
                "title"
            ].tolist()
    except:
        return []


@st.cache_data(show_spinner=False)
def encode_database_vectors(_model, df):
    candidates = []
    candidates_meta = []
    col_map = {
        "fase_laten": "Laten",
        "fase_persepsi": "Persepsi",
        "fase_manifes": "Manifes",
        "fase_eskalasi": "Eskalasi",
        "fase_krisis": "Krisis",
    }
    for idx, row in df.iterrows():
        for col_db, fase_name in col_map.items():
            deskripsi = row[col_db]
            if deskripsi and len(str(deskripsi)) > 5:
                ai_text = f"{deskripsi}. (Konteks: Indikator {row['indikator']} dalam dimensi {row['dimensi']})"
                candidates.append(ai_text)
                candidates_meta.append(
                    {
                        "data": row,
                        "fase": fase_name,
                        "deskripsi_match": deskripsi,
                        "ai_text_used": ai_text,
                    }
                )
    if candidates:
        db_vecs = _model.encode(candidates, convert_to_tensor=True)
        return db_vecs, candidates_meta
    return None, None


def init_history_db():
    query = """
    CREATE TABLE IF NOT EXISTS analysis_history (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sumber_case TEXT,
        redaksi_input TEXT,
        fase TEXT,
        dimensi TEXT,
        sub_dimensi TEXT,
        indikator TEXT,
        skor_keyakinan FLOAT,
        rekomendasi TEXT
    );
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(query))
    except Exception as e:
        st.error(f"Gagal init tabel histori: {e}")


def save_analysis(sumber, input_text, fase, dim, sub, ind, score, rek):
    query = text(
        """
        INSERT INTO analysis_history 
        (sumber_case, redaksi_input, fase, dimensi, sub_dimensi, indikator, skor_keyakinan, rekomendasi)
        VALUES (:s, :r, :f, :d, :sd, :i, :sk, :re)
    """
    )
    try:
        with engine.begin() as conn:
            conn.execute(
                query,
                {
                    "s": sumber,
                    "r": input_text,
                    "f": fase,
                    "d": dim,
                    "sd": sub,
                    "i": ind,
                    "sk": score,
                    "re": rek,
                },
            )
    except Exception as e:
        st.error(f"Gagal menyimpan histori: {e}")


def get_history():
    try:
        with engine.connect() as conn:
            return pd.read_sql(
                "SELECT * FROM analysis_history ORDER BY timestamp DESC", conn
            )
    except:
        return pd.DataFrame()
    
def get_matched_keyword(text_content):
    if not text_content: return "Isu Umum"
    # KEYWORDS adalah list yang sama dengan yang ada di Scraper
    keywords_list = ['konflik', 'agama', 'sengketa', 'ibadah', 'intoleransi', 'penodaan', 'gereja', 'masjid', 'sesat', 'kafir', 'penolakan']
    for k in keywords_list:
        if k.lower() in str(text_content).lower():
            return k.capitalize()
    return "Isu Umum"

# Terapkan ke dataframe sebelum di-plot
if not df_chart.empty:
    df_chart['keyword_isu'] = df_chart.apply(lambda x: get_matched_keyword(str(x['title']) + " " + str(x['content'])), axis=1)


init_db()
init_history_db()

if "sub_dimensions" not in st.session_state:
    st.session_state.sub_dimensions = [
        {
            "name": "",
            "description": "",
            "indicators": [
                {
                    "name": "",
                    "laten": "",
                    "persepsi": "",
                    "manifes": "",
                    "eskalasi": "",
                    "krisis": "",
                }
            ],
        }
    ]

if "success_msg" not in st.session_state:
    st.session_state.success_msg = False

st.title("🛡️ EWS Social-Religious Conflict")
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Dashboard Nasional",
        "➕ Input Matriks Baru",
        "🧠 Orchestrator Analisis",
        "📊 Kelola Database (Edit/Hapus)",
        "📜 Histori Analisis AI",
    ]
)

with tab1:
    st.header("🇮🇩 Peta Risiko Kerukunan Nasional (Live Big Data)")

    # 1. AMBIL DAFTAR TAHUN SECARA DINAMIS DARI DATABASE
    try:
        with engine.connect() as conn:
            q_years = text("SELECT DISTINCT EXTRACT(YEAR FROM created_at) as year FROM social_media_reports ORDER BY year DESC")
            db_years = pd.read_sql(q_years, conn)['year'].astype(int).tolist()
            
            # Tambahkan pilihan 'Semua' di awal daftar
            available_years = ["Semua"] + db_years
            
            if len(available_years) == 1: # Jika DB kosong
                available_years = ["Semua", 2026, 2025, 2024]
    except:
        available_years = ["Semua", 2026, 2025, 2024]

    st.markdown("### 🔍 Filter Global Dashboard")
    c_filt1, c_filt2, c_filt3 = st.columns([1, 1, 2])
    
    with c_filt1:
        year_filter = st.selectbox("Pilih Tahun:", available_years, index=0)
    
    with c_filt2:
        month_filter = st.selectbox("Pilih Bulan:", ["Semua", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], index=0)
    
    # 2. LOGIKA STRING SQL DINAMIS (Mendukung pilihan 'Semua')
    sql_date_filter = ""
    sql_date_filter_stats = ""

    # Filter Tahun
    if year_filter != "Semua":
        sql_date_filter += f" AND EXTRACT(YEAR FROM created_at) = {year_filter}"
        sql_date_filter_stats += f" AND EXTRACT(YEAR FROM timestamp) = {year_filter}"

    # Filter Bulan
    if month_filter != "Semua":
        sql_date_filter += f" AND EXTRACT(MONTH FROM created_at) = {month_filter}"
        sql_date_filter_stats += f" AND EXTRACT(MONTH FROM timestamp) = {month_filter}"

    # 1. Inisialisasi variabel di awal agar tidak terjadi NameError
    df_news_display = pd.DataFrame()
    df_sosmed_display = pd.DataFrame()
    df_audit = pd.DataFrame()
    df_chart = pd.DataFrame()
    df_stats = pd.DataFrame()
    df_emotion = pd.DataFrame()
    df_viral = pd.DataFrame()
    total_isu = 0
    total_aduan = 0
    intensity_val = 0
    anger_val = 0

    try:
        # --- 2. PENGAMBILAN DATA UTAMA ---
        with engine.connect() as conn:
            # Volume Isu (Ganti filter manual 2024-2026 dengan filter global)
            total_isu_query = text(f"SELECT COUNT(*) FROM social_media_reports WHERE 1=1 {sql_date_filter}")
            total_isu = pd.read_sql(total_isu_query, conn).iloc[0, 0]

            # Statistik Keyword (Hapus interval 48 jam jika ingin melihat sejarah tahun/bulan)
            q_stats = text(f"""
                SELECT keyword, SUM(jumlah) as total_count 
                FROM risk_statistics 
                WHERE 1=1 {sql_date_filter_stats}
                GROUP BY keyword ORDER BY total_count DESC
            """)
            df_stats = pd.read_sql(q_stats, conn)

            # Tren Grafik
            q_chart = text(f"""
                SELECT created_at as waktu, intensity, platform, location, source, title, content
                FROM social_media_reports 
                WHERE 1=1 {sql_date_filter}
                ORDER BY created_at ASC
            """)
            df_chart = pd.read_sql(q_chart, conn)

            # Statistik Emosi
            q_emotion = text(f"SELECT emotion, SUM(count) as total FROM emotion_statistics WHERE 1=1 {sql_date_filter_stats} GROUP BY emotion")
            df_emotion = pd.read_sql(q_emotion, conn)

            # Kecepatan Isu (Layer 3)
            q_viral = text(f"SELECT platform, SUM(velocity) as total_velocity FROM viral_acceleration WHERE 1=1 {sql_date_filter_stats} GROUP BY platform")
            df_viral = pd.read_sql(q_viral, conn)

            # Integrasi Pengaduan (Layer 4)
            q_aduan_count = text(f"SELECT COUNT(*) FROM public_complaints WHERE 1=1 {sql_date_filter_stats}")
            total_aduan = pd.read_sql(q_aduan_count, conn).iloc[0, 0]

            # --- 3. AMBIL DATA AUDIT (PISAH QUERY AGAR TIDAK REBUTAN KUOTA) ---
            # Ambil khusus News (LIMIT 100)
            # Ambil khusus News
            q_news = text(f"""
                SELECT created_at, source, title, url, location, platform 
                FROM social_media_reports 
                WHERE platform = 'News' {sql_date_filter}
                ORDER BY created_at DESC LIMIT 100
            """)
            df_news_raw = pd.read_sql(q_news, conn)

            # Ambil khusus YouTube (Ganti 'EXTRACT... = 2025' dengan filter global)
            q_sosmed = text(f"""
                SELECT DISTINCT ON (content, source) 
                    created_at, source, title, content, location, platform 
                FROM social_media_reports 
                WHERE platform = 'YouTube' {sql_date_filter}
                ORDER BY content, source, created_at DESC 
                LIMIT 100
            """)
            df_sosmed_raw = pd.read_sql(q_sosmed, conn)

        # --- 4. PROSES TAMPILAN (LANGSUNG RENAME) ---
        if not df_news_raw.empty:
            df_news_display = df_news_raw.rename(columns={
                "created_at": "Waktu Upload", 
                "source": "User/Sumber", 
                "location": "location", 
                "title": "Judul/Topik", 
                "url": "url"
            })

        if not df_sosmed_raw.empty:
            df_sosmed_display = df_sosmed_raw.rename(columns={
                "created_at": "Waktu Upload", 
                "source": "User/Sumber", 
                "location": "location", 
                "title": "Judul/Topik", 
                "content": "Komentar/Konten"
            })

        if not df_chart.empty:
            df_chart['keyword_isu'] = df_chart.apply(
                lambda x: get_matched_keyword(str(x['title']) + " " + str(x['content'])), 
                axis=1
            )

    except Exception as e:
        st.error(f"Gagal memuat data dashboard: {e}")

    # ==========================================
    # 5. MESIN PENILAIAN RISIKO (Layer 1-4 Wisdom) [cite: 108]
    # ==========================================
    intensity_val = df_stats["total_count"].sum() if not df_stats.empty else 0
    anger_val = (
        df_emotion[df_emotion["emotion"] == "anger"]["total"].sum()
        if not df_emotion.empty
        else 0
    )
    total_velocity = df_viral["total_velocity"].sum() if not df_viral.empty else 0

    # Perhitungan Skor Berbobot sesuai Blueprint
    score_intensity = min((intensity_val / 500) * 25, 25)  # 25% Keyword [cite: 111]
    score_emotion = min((anger_val / 100) * 25, 25)  # 25% Emosi Marah [cite: 112, 113]
    score_viral = min((total_velocity / 200) * 20, 20)  # 20% Viralisasi [cite: 114]
    score_aduan = min((total_aduan / 10) * 30, 30)  # 30% Aduan (Embrio) [cite: 115]

    # Bonus Krisis jika terdeteksi kata kunci fatal [cite: 123]
    krisis_words = ["bakar", "serang", "usir", "krisis"]
    bonus_krisis = (
        10
        if not df_stats.empty
        and any(word in df_stats["keyword"].values for word in krisis_words)
        else 0
    )

    risk_score_real = int(
        score_intensity + score_emotion + score_viral + score_aduan + bonus_krisis
    )
    risk_score_real = min(risk_score_real, 100)

    # Penentuan Status & Warna [cite: 127, 128]
    if risk_score_real > 80:
        status_label, status_color = "🚨 DARURAT (MERAH)", "red"
    elif risk_score_real > 60:
        status_label, status_color = "⚠️ SIAGA (ORANYE)", "orange"
    elif risk_score_real > 30:
        status_label, status_color = "🔍 WASPADA (KUNING)", "yellow"
    else:
        status_label, status_color = "✅ AMAN (HIJAU)", "green"

    # UI Metrics Utama
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Skor Risiko Kerukunan",
        f"{risk_score_real}/100",
        status_label,
        delta_color="inverse",
    )
    col2.metric("Intensitas Isu", intensity_val, "Hits")
    col3.metric("Indeks Kemarahan", anger_val, "Emotion Index")
    col4.metric("Aduan (24H)", total_aduan, "Embrio Konflik")

    st.markdown("---")

    # ==========================================
    # 6. VISUALISASI INTEGRASI LAYER 1-4
    # ==========================================
    col_left, col_right = st.columns(2)

    def plot_layer1(df):
        if df.empty:
            return None

        fig = px.line(
            df,
            x="waktu",
            y="intensity",
            color="platform",
            markers=True,
            hover_data={
                "waktu": "|%d %b %Y %H:%M",
                "intensity": ":.2f",
                "keyword_isu": True,
                "title": True,  # Menampilkan Judul/Topik Isu
                "source": True, # Menampilkan Akun/Sumber
                "platform": True
            },
            title="📈 Dinamika Intensitas Isu Nasional",
            labels={"intensity": "Intensitas Isu"},
        )

        # Ubah "spline" menjadi "linear" agar tidak error
        fig.update_traces(line_shape="linear", line_width=3)
        return fig
    
    st.markdown("---")

    with st.container():
        c_news, c_yt = st.columns(2)

        with c_news:
            st.markdown("### 📰 Berita Teratas")
            # Cari berita dengan intensitas tertinggi dalam periode filter
            top_news = df_chart[df_chart['platform'] == 'News'].sort_values(by='intensity', ascending=False).head(1)
            
            if not top_news.empty:
                match_k = get_matched_keyword(str(top_news['title'].values[0]) + " " + str(top_news['content'].values[0]))
                st.warning(f"**Top Isu:** {match_k}")
                st.write(f"**Sumber Pemicu:** {top_news['source'].values[0]}")
                st.caption(f"**Judul Berita:** {top_news['title'].values[0]}")
            else:
                st.info("Belum ada tren berita menonjol.")

        with c_yt:
            st.markdown("### 📺 Youtube Teratas")
            # Cari data YouTube dengan intensitas tertinggi (biasanya komentar)
            top_yt = df_chart[df_chart['platform'] == 'YouTube'].sort_values(by='intensity', ascending=False).head(1)
            
            if not top_yt.empty:
                match_k_yt = get_matched_keyword(str(top_yt['title'].values[0]) + " " + str(top_yt['content'].values[0]))
                # Ambil isi komentar dari database berdasarkan judul video teratas
                with engine.connect() as conn:
                    q_comm = text("SELECT content FROM social_media_reports WHERE title = :t AND platform = 'YouTube' LIMIT 1")
                    res_comm = conn.execute(q_comm, {"t": top_yt['title'].values[0]}).fetchone()
                    komentar = res_comm[0] if res_comm else "Detail komentar tidak ditemukan."

                st.error(f"**Top Isu:** {match_k_yt}")
                st.write(f"**Akun Pemicu:** {top_yt['source'].values[0]}")
                st.write(f"**Judul Video:** {top_yt['title'].values[0]}")
                with st.expander("💬 Lihat Isi Komentar Pemicu"):
                    st.write(komentar)
            else:
                st.info("Belum ada tren komentar YouTube menonjol.")

    with col_left:
        st.subheader("📊 Tren Lonjakan Isu (Layer 1)")
        if not df_chart.empty:
            # PANGGIL FUNGSINYA DI SINI
            chart_output = plot_layer1(df_chart)
            if chart_output:
                st.plotly_chart(chart_output, use_container_width=True)
        else:
            st.info("⌛ Menunggu data tren masuk dari database...")

        st.subheader("📈 Kecepatan Viralisasi (Layer 3)")
        if not df_viral.empty:
            st.bar_chart(df_viral, x="platform", y="total_velocity", color="#FF4B4B")
        else:
            st.info("Kecepatan penyebaran isu terpantau rendah.")

    with col_right:
        st.subheader("🧠 Indeks Emosi Sosial (Layer 2)")
        if not df_emotion.empty:
            c_emotion = (
                alt.Chart(df_emotion)
                .mark_arc(innerRadius=50)
                .encode(
                    theta="total:Q",
                    color=alt.Color(
                        "emotion:N",
                        scale=alt.Scale(
                            domain=["anger", "fear", "neutral"],
                            range=["#FF4B4B", "#FFA500", "#00CC96"],
                        ),
                    ),
                    tooltip=["emotion", "total"],
                )
                .properties(height=250)
            )
            st.altair_chart(c_emotion, use_container_width=True)

        st.subheader("📩 Integrasi Pengaduan (Layer 4)")
        if total_aduan > 10:
            st.error(
                f"🚨 **ZONA MERAH DINI**: Terjadi {total_aduan} aduan berulang. Potensi eskalasi fisik tinggi!"
            )
        else:
            st.success("Sinyal pengaduan masyarakat terpantau stabil.")

    st.markdown("---")

    # ==========================================
    # 7. AUDIT KRONOLOGI & DETAIL
    # ==========================================
    st.subheader("🕵️ Audit Kronologi & Viralisasi")
    tab_news, tab_sosmed, tab_aduan = st.tabs(["🗞️ Berita", "💬 Sosial Media", "📩 Aduan Warga"])

    with tab_news:
        if not df_news_display.empty:
            st.dataframe(df_news_display[['Waktu Upload', 'User/Sumber', 'location', 'Judul/Topik', 'url']], use_container_width=True)
        else:
            st.info("⌛ Menunggu data berita masuk...")

    with tab_sosmed:
        # PERBAIKAN: Langsung panggil variabel yang sudah kita siapkan di atas
        # Variabel ini sudah berisi hasil filter khusus YouTube yang utuh
        if not df_sosmed_display.empty:
            st.dataframe(df_sosmed_display, use_container_width=True)
        else:
            st.info("⌛ Menunggu data sosial media...")

    # Helper function to safely display a DataFrame or show a message if empty
    def safe_display_df(df, columns, empty_message):
        if not df.empty:
            st.dataframe(df[columns], use_container_width=True)
        else:
            st.info(empty_message)

    with tab_aduan:
        # Query langsung ke tabel aduan
        try:
            df_aduan_list = pd.read_sql(
                text(
                    "SELECT timestamp, wilayah, sumber_aduan, isi_aduan FROM public_complaints ORDER BY timestamp DESC LIMIT 10"
                ),
                engine,
            )
            safe_display_df(
                df_aduan_list,
                ["timestamp", "wilayah", "sumber_aduan", "isi_aduan"],
                "📩 Belum ada aduan masuk.",
            )
        except:
            st.info("📩 Tabel aduan belum tersedia.")

    st.markdown("---")
    # Menggunakan variabel year_filter dan month_filter sesuai kode Anda sebelumnya
    st.subheader(f"🗺️ Peta Sebaran Risiko Konflik")

    try:
        with engine.connect() as conn:
            # 1. Bangun Filter Kondisional menggunakan variabel yang benar
            # Kita tetap bisa menggunakan logic params atau langsung sql_date_filter
            
            # Jika ingin menggunakan parameter (:year, :month) untuk keamanan:
            params = {}
            filter_sql = "1=1" # Placeholder agar query tetap valid

            if year_filter != "Semua":
                filter_sql += " AND EXTRACT(YEAR FROM created_at) = :year"
                params["year"] = int(year_filter)

            if month_filter != "Semua":
                filter_sql += " AND EXTRACT(MONTH FROM created_at) = :month"
                params["month"] = int(month_filter) # Pastikan integer karena month_filter Anda adalah angka 1-12

            # 3. Query Agregat dengan Filter Aktif
            q_map = text(f"""
                WITH loc_data AS (
                    SELECT 
                        location, latitude, longitude, platform, source as top_account,
                        intensity,
                        created_at
                    FROM social_media_reports 
                    WHERE latitude IS NOT NULL AND latitude != 0
                    {sql_date_filter} -- Ini otomatis menyambungkan filter Tahun & Bulan
                ),
                agg_data AS (
                    SELECT 
                        location, latitude, longitude,
                        COUNT(*) as total_kejadian,
                        AVG(intensity) as avg_intensity,
                        -- Ambil keyword top di lokasi tersebut berdasarkan filter waktu
                        (SELECT keyword FROM risk_statistics rs 
                         WHERE rs.location = ld.location 
                         {sql_date_filter_stats} -- Gunakan filter versi timestamp
                         GROUP BY keyword ORDER BY SUM(jumlah) DESC LIMIT 1) as top_keyword,
                        -- Ambil akun pemicu di lokasi tersebut berdasarkan filter waktu
                        (SELECT source FROM social_media_reports smr 
                         WHERE smr.location = ld.location 
                         {sql_date_filter}
                         GROUP BY source ORDER BY COUNT(*) DESC LIMIT 1) as trigger_account
                    FROM loc_data ld
                    GROUP BY location, latitude, longitude
                )
                SELECT * FROM agg_data
            """)
            
            df_map = pd.read_sql(q_map, conn)

        if not df_map.empty:
            # Kalkulasi Skor (Intensity 50% + Volume 50%)
            df_map["risk_score"] = (df_map["avg_intensity"] * 7) + (df_map["total_kejadian"] * 0.5)
            df_map["risk_score"] = df_map["risk_score"].clip(0, 100)
            
            # Hover Data
            df_map["Skor Risiko"] = df_map["risk_score"].apply(lambda x: f"{x:.2f} / 100")
            df_map["Top Keyword"] = df_map["top_keyword"].fillna("Isu Umum")
            df_map["Akun Pemicu"] = df_map["trigger_account"]
            df_map["Total Laporan"] = df_map["total_kejadian"].astype(str) + " Laporan"

            fig_map = px.scatter_map(
                df_map,
                lat="latitude",
                lon="longitude",
                color="risk_score",    
                hover_name="location",
                hover_data={
                    "latitude": False, "longitude": False, 
                    "Skor Risiko": True, "Top Keyword": True,
                    "Akun Pemicu": True, "Total Laporan": True,
                    "risk_score": False 
                },
                color_continuous_scale="RdYlGn_r", 
                range_color=[0, 100], 
                zoom=4,
                height=600,
            )

            fig_map.update_traces(marker=dict(size=14, opacity=0.85))
            
            fig_map.update_layout(
                map_style="carto-darkmatter", 
                margin={"r":0,"t":0,"l":0,"b":0}
            )
            
            fig_map.update_coloraxes(colorbar_title="Tingkat Kerawanan")
            st.plotly_chart(fig_map, use_container_width=True)
            
        else:
            st.info(f"📍 Tidak ada data laporan untuk periode Tahun: {year_filter}, Bulan: {month_filter}")

    except Exception as e:
        st.error(f"Gagal memuat peta: {e}")

    # ==========================================
    # 8. PERINGKAT RISIKO WILAYAH (DINAMIS)
    # ==========================================
    st.markdown("---")
    st.subheader("🏆 Peringkat Kerawanan Wilayah (Real-Time)")
    
    if not df_map.empty:
        # Urutkan data berdasarkan risk_score tertinggi
        df_ranking = df_map.sort_values(by="risk_score", ascending=False).copy()
        
        # Tambahkan kolom nomor urut
        df_ranking.insert(0, 'Peringkat', range(1, len(df_ranking) + 1))
        
        # Fungsi untuk memberi warna pada baris skor
        def color_risk(val):
            if val > 80: return 'background-color: #ff4b4b; color: white' # Merah
            elif val > 60: return 'background-color: #ffa500; color: black' # Oranye
            elif val > 30: return 'background-color: #ffff00; color: black' # Kuning
            return 'background-color: #00cc96; color: white' # Hijau

        # Tampilkan tabel dengan gaya visual
        st.dataframe(
            df_ranking[['Peringkat', 'location', 'Skor Risiko', 'Top Keyword', 'Akun Pemicu', 'Total Laporan']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "location": "Nama Wilayah",
                "Skor Risiko": st.column_config.TextColumn("Indeks Risiko"),
                "Top Keyword": "Isu Utama",
                "Akun Pemicu": "Top Account",
                "Total Laporan": "Volume Data"
            }
        )
    else:
        st.info("📍 Belum ada data wilayah untuk diurutkan.")

with tab2:
    if st.session_state.success_msg:
        st.success("✅ Data Berhasil Disimpan ke Database PostgreSQL!")
        st.session_state.success_msg = False

    st.subheader("Form Input Indikator & Deskripsi Konteks AI")
    st.info(
        "💡 **Tips:** Isi 'Deskripsi Sub-Dimensi' dengan penjelasan detail agar AI lebih akurat melakukan klasifikasi."
    )

    dimensi_name = st.text_input("Nama Dimensi Utama", key="dim_input_main")

    for s_idx, sub in enumerate(st.session_state.sub_dimensions):
        with st.container():
            st.markdown(f"### 📂 Sub-Dimensi #{s_idx+1}")

            c_sub1, c_sub2 = st.columns([1, 2])

            sub["name"] = c_sub1.text_input(
                f"Nama Sub-Dimensi", value=sub["name"], key=f"sub_name_{s_idx}"
            )

            sub["description"] = c_sub2.text_area(
                "Deskripsi Konteks (Untuk Kecerdasan AI)",
                value=sub.get("description", ""),
                key=f"sub_desc_{s_idx}",
                placeholder="Jelaskan detail cakupan sub-dimensi ini agar AI paham konteksnya...",
                height=68,
            )

            for i_idx, ind in enumerate(sub["indicators"]):
                st.markdown(f"**📍 Indikator {i_idx+1}**")
                ind["name"] = st.text_input(
                    "Nama Indikator", value=ind["name"], key=f"ind_n_{s_idx}_{i_idx}"
                )

                c1, c2, c3, c4, c5 = st.columns(5)
                ind["laten"] = c1.text_area(
                    "Laten", value=ind["laten"], key=f"lt_{s_idx}_{i_idx}"
                )
                ind["persepsi"] = c2.text_area(
                    "Persepsi", value=ind["persepsi"], key=f"ps_{s_idx}_{i_idx}"
                )
                ind["manifes"] = c3.text_area(
                    "Manifes", value=ind["manifes"], key=f"mn_{s_idx}_{i_idx}"
                )
                ind["eskalasi"] = c4.text_area(
                    "Eskalasi", value=ind["eskalasi"], key=f"es_{s_idx}_{i_idx}"
                )
                ind["krisis"] = c5.text_area(
                    "Krisis", value=ind["krisis"], key=f"kr_{s_idx}_{i_idx}"
                )

            if st.button(
                f"➕ Tambah Indikator di Sub #{s_idx+1}", key=f"btn_add_ind_{s_idx}"
            ):
                sub["indicators"].append(
                    {
                        "name": "",
                        "laten": "",
                        "persepsi": "",
                        "manifes": "",
                        "eskalasi": "",
                        "krisis": "",
                    }
                )
                st.rerun()
        st.markdown("---")

    if st.button("➕ Tambah Sub-Dimensi Baru"):
        st.session_state.sub_dimensions.append(
            {
                "name": "",
                "description": "",
                "indicators": [
                    {
                        "name": "",
                        "laten": "",
                        "persepsi": "",
                        "manifes": "",
                        "eskalasi": "",
                        "krisis": "",
                    }
                ],
            }
        )
        st.rerun()

    st.markdown("###")

    if st.button("💾 SIMPAN SELURUH MATRIKS", type="primary"):
        data_to_save = []
        if not dimensi_name.strip():
            st.warning("⚠️ Nama Dimensi Utama tidak boleh kosong!")
        else:
            for sub in st.session_state.sub_dimensions:
                for ind in sub["indicators"]:
                    if ind["name"].strip():
                        data_to_save.append(
                            {
                                "dimensi": dimensi_name,
                                "sub_dimensi": sub["name"],
                                "deskripsi": sub.get("description", ""),
                                "indikator": ind["name"],
                                "fase_laten": ind["laten"],
                                "fase_persepsi": ind["persepsi"],
                                "fase_manifes": ind["manifes"],
                                "fase_eskalasi": ind["eskalasi"],
                                "fase_krisis": ind["krisis"],
                            }
                        )

            if not data_to_save:
                st.warning(
                    "⚠️ Belum ada indikator yang diisi (Minimal isi Nama Indikator)."
                )
            else:
                try:
                    df_save = pd.DataFrame(data_to_save)

                    with engine.begin() as connection:
                        df_save.to_sql(
                            "matrix_indicators",
                            con=connection,
                            if_exists="append",
                            index=False,
                            method="multi",
                        )

                    st.session_state.sub_dimensions = [
                        {
                            "name": "",
                            "description": "",
                            "indicators": [
                                {
                                    "name": "",
                                    "laten": "",
                                    "persepsi": "",
                                    "manifes": "",
                                    "eskalasi": "",
                                    "krisis": "",
                                }
                            ],
                        }
                    ]
                    st.session_state.success_msg = True
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Gagal Total! Pesan Error: {e}")

with tab3:
    st.subheader("🧠 Intelligence Orchestrator (Deep Reasoning Mode)")
    df_m = get_all_data()

    cached_vecs = None
    cached_meta = None

    if df_m.empty:
        st.info("Kamus indikator masih kosong. Silakan isi di Tab 2.")
    else:
        if model_ai:
            with st.spinner("Memuat Database ke Memori..."):
                cached_vecs, cached_meta = encode_database_vectors(model_ai, df_m)

        case_mode = st.radio("Sumber:", ["Manual", "Scraping"], horizontal=True)
        txt_input = ""

        if case_mode == "Scraping":
            platform = st.selectbox(
                "Pilih Platform Sumber:", ["News", "YouTube", "Instagram"]
            )

            if platform == "YouTube":
                st.markdown("### 📺 Analisis Sentimen YouTube")
                with engine.connect() as conn:
                    q_video = text(
                        """
                        SELECT DISTINCT title 
                        FROM social_media_reports 
                        WHERE source = 'YouTube' OR source LIKE '%Channel%' OR source LIKE '@%'
                        ORDER BY title ASC
                    """
                    )
                    videos = pd.read_sql(q_video, conn)

                if not videos.empty:
                    selected_video = st.selectbox(
                        "Pilih Topik Video:", videos["title"].tolist()
                    )
                    with engine.connect() as conn:
                        q_comments = text(
                            """
                            SELECT source, content 
                            FROM social_media_reports 
                            WHERE title = :v AND source LIKE '@%'
                            ORDER BY created_at DESC
                            LIMIT 50
                        """
                        )
                        df_comments = pd.read_sql(
                            q_comments, conn, params={"v": selected_video}
                        )

                    if not df_comments.empty:
                        df_comments = df_comments.drop_duplicates(subset=["content"])
                        with st.spinner(
                            "AI sedang menyaring komentar sampah/netral..."
                        ):
                            anchor_conflict = "marah protes tolak bubarkan sesat kafir ribut berantem tidak setuju sengketa"
                            anchor_vec = model_ai.encode(
                                anchor_conflict, convert_to_tensor=True
                            )
                            comment_vecs = model_ai.encode(
                                df_comments["content"].tolist(), convert_to_tensor=True
                            )
                            scores = util.cos_sim(anchor_vec, comment_vecs)[0]
                            df_comments["conflict_score"] = scores.tolist()
                            df_filtered = df_comments[
                                df_comments["conflict_score"] > 0.15
                            ].sort_values(by="conflict_score", ascending=False)

                        if df_filtered.empty:
                            st.info(
                                "Video ini bersih. Tidak ditemukan komentar yang memicu konflik."
                            )
                        else:
                            df_filtered["display"] = df_filtered.apply(
                                lambda x: f"[{x['conflict_score']:.2f}] {x['content'][:80]}...",
                                axis=1,
                            )
                            sel_comment_display = st.selectbox(
                                f"Ditemukan {len(df_filtered)} Komentar Berpotensi Konflik:",
                                df_filtered["display"].tolist(),
                            )
                            row_comment = df_filtered[
                                df_filtered["display"] == sel_comment_display
                            ].iloc[0]
                            real_content = row_comment["content"]
                            user_source = row_comment["source"]
                            txt_input = f'Topik Video: {selected_video}. Komentar Netizen ({user_source}): "{real_content}"'
                            st.info(f"**Full Komentar:** {real_content}")
                            st.caption(f"Input yang akan dianalisis AI: _{txt_input}_")
                    else:
                        st.warning("Belum ada komentar di video ini.")
                else:
                    st.warning("Belum ada data video YouTube.")

            elif platform == "News":
                with engine.connect() as conn:
                    query = text(
                        """
                        SELECT title, content, source, created_at
                        FROM social_media_reports 
                        WHERE source NOT IN ('YouTube', 'Instagram')
                        AND source NOT LIKE '@%' 
                        AND source NOT LIKE '%Channel%'
                        ORDER BY created_at DESC 
                        LIMIT 150
                    """
                    )
                    df_news = pd.read_sql(query, conn)

                if not df_news.empty:
                    df_news = df_news.drop_duplicates(subset=["title"])
                    df_news = df_news.head(20)
                    df_news["source"] = df_news["source"].fillna("Web")
                    df_news["display_label"] = df_news.apply(
                        lambda x: f"[{x['source']}] {x['title'].strip()}", axis=1
                    )

                    sel = st.selectbox(
                        "Pilih Berita Terkini:", df_news["display_label"].tolist()
                    )
                    txt_input = df_news[df_news["display_label"] == sel][
                        "content"
                    ].values[0]
                    with st.expander("📖 Lihat Isi Berita Lengkap"):
                        st.info(txt_input)
                else:
                    st.warning("Belum ada data berita yang valid.")

            elif platform == "Instagram":
                st.markdown("### 📸 Analisis Sentimen Instagram")
                with engine.connect() as conn:
                    query_ig = text(
                        """
                        SELECT title, source, content 
                        FROM social_media_reports 
                        WHERE source = 'Instagram' 
                        OR source LIKE '%ig_%'
                        ORDER BY created_at DESC
                    """
                    )
                    df_ig = pd.read_sql(query_ig, conn)

                if not df_ig.empty:
                    df_ig["display_label"] = df_ig.apply(
                        lambda x: f"INSTAGRAM : {x['title']} - {x['source']}", axis=1
                    )

                    selected_ig = st.selectbox(
                        "Pilih Postingan/Komentar Instagram:",
                        options=df_ig["display_label"].tolist(),
                    )

                    txt_input = df_ig[df_ig["display_label"] == selected_ig][
                        "content"
                    ].values[0]

                    with st.expander("💬 Lihat Detail Konten Instagram"):
                        st.info(txt_input)
                else:
                    st.info(
                        "💡 **Info:** Data Instagram belum tersedia. Pastikan robot scraper Instagram sudah berjalan dengan session yang valid."
                    )

        else:
            txt_input = st.text_area(
                "Masukkan Redaksi Kejadian / Kronologi:",
                height=150,
                placeholder="Contoh: Terjadi aksi saling ejek antar pemuda...",
            )

        if st.button("🚀 Analisis AI"):
            if model_ai and txt_input:
                save_as_complaint(txt_input)
                bar = st.progress(0, "Membaca makna input...")
                try:
                    input_vec = model_ai.encode(txt_input, convert_to_tensor=True)
                    cos_scores = util.cos_sim(input_vec, cached_vecs)[0]
                    best_idx = int(torch.argmax(cos_scores))
                    best_score = float(cos_scores[best_idx])
                    winner = cached_meta[best_idx]
                    bar.progress(100, "Selesai!")
                    if best_score < 0.25:
                        st.info("🟢 **Netral / Tidak Relevan** (Skor < 25%)")
                    else:
                        row_data = winner["data"]
                        rekomendasi_map = {
                            "Laten": "⚠️ **Pre-emtif**: Pemetaan aktor & dialog.",
                            "Persepsi": "🔍 **Preventif**: Kontra-narasi & sosialisasi.",
                            "Manifes": "🤝 **Mediasi**: Pertemukan pihak dengan fasilitator.",
                            "Eskalasi": "👮 **Intervensi**: Keamanan ketat & isolasi.",
                            "Krisis": "🚨 **Darurat**: Penegakan hukum & logistik.",
                        }
                        rec_text = rekomendasi_map.get(winner["fase"], "Tinjau Situasi")
                        st.success(
                            f"✅ Terdeteksi: {row_data['dimensi']} (Keyakinan: {best_score:.1%})"
                        )
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("FASE", winner["fase"])
                        c2.metric("DIMENSI", row_data["dimensi"])
                        c3.metric("SUB-DIMENSI", row_data["sub_dimensi"])
                        c4.metric("INDIKATOR", row_data["indikator"])
                        st.warning(f"💡 **REKOMENDASI:** {rec_text}")
                        st.markdown("---")
                        st.subheader("📊 Tingkat Akurasi")
                        st.progress(
                            best_score,
                            text=f"Kecocokan Makna dengan Fase {winner['fase']}: {best_score:.1%}",
                        )
                        chart_df = pd.DataFrame(
                            {
                                "Parameter": [f"Kecocokan dgn Fase {winner['fase']}"],
                                "Skor (%)": [best_score * 100],
                            }
                        )
                        st.bar_chart(
                            chart_df, x="Parameter", y="Skor (%)", color="#FF4B4B"
                        )
                        with st.expander("🔎 Mengapa AI memilih ini?"):
                            st.write("**Input Anda:**")
                            st.caption(txt_input)
                            st.write("**Paling mirip secara makna dengan kondisi:**")
                            st.info(f"_{winner['deskripsi_match']}_")
                            st.write(
                                f"Kondisi ini terdapat pada indikator **{row_data['indikator']}**."
                            )
                        save_analysis(
                            "Manual/Scrape",
                            txt_input,
                            winner["fase"],
                            row_data["dimensi"],
                            row_data["sub_dimensi"],
                            row_data["indikator"],
                            best_score,
                            rec_text,
                        )
                except Exception as e:
                    st.error(f"Error System: {e}")
            else:
                st.warning("Input kosong.")

with tab4:
    st.subheader("⚙️ Manajemen Database")
    df_w = get_all_data()

    if not df_w.empty:
        for idx, row in df_w.iterrows():
            with st.expander(
                f"📝 #{row['id']} - {row['dimensi']} > {row['indikator']}"
            ):
                with st.form(f"edit_{row['id']}"):
                    col_a, col_b = st.columns(2)
                    e_dim = col_a.text_input("Dimensi", value=row["dimensi"])
                    e_sub = col_b.text_input("Sub Dimensi", value=row["sub_dimensi"])
                    e_desc = st.text_area(
                        "Deskripsi Konteks AI (Penjelasan Sub-Dimensi)",
                        value=row["deskripsi"] if "deskripsi" in row else "",
                        help="Edit penjelasan ini untuk meningkatkan akurasi deteksi AI.",
                    )
                    e_ind = st.text_input("Indikator", value=row["indikator"])
                    st.markdown("**Edit Fase:**")
                    f1, f2, f3, f4, f5 = st.columns(5)
                    e_l = f1.text_area("Laten", value=row["fase_laten"])
                    e_p = f2.text_area("Persepsi", value=row["fase_persepsi"])
                    e_m = f3.text_area("Manifes", value=row["fase_manifes"])
                    e_e = f4.text_area("Eskalasi", value=row["fase_eskalasi"])
                    e_k = f5.text_area("Krisis", value=row["fase_krisis"])
                    btn_up, btn_del = st.columns([1, 1])
                    if btn_up.form_submit_button(
                        "💾 Update Data", use_container_width=True
                    ):
                        with engine.begin() as conn:
                            conn.execute(
                                text(
                                    """
                                UPDATE matrix_indicators 
                                SET dimensi=:d, sub_dimensi=:s, deskripsi=:desc, indikator=:i, 
                                    fase_laten=:l, fase_persepsi=:p, fase_manifes=:m, 
                                    fase_eskalasi=:e, fase_krisis=:k 
                                WHERE id=:id
                            """
                                ),
                                {
                                    "d": e_dim,
                                    "s": e_sub,
                                    "desc": e_desc,
                                    "i": e_ind,
                                    "l": e_l,
                                    "p": e_p,
                                    "m": e_m,
                                    "e": e_e,
                                    "k": e_k,
                                    "id": row["id"],
                                },
                            )
                        st.success(f"Data ID #{row['id']} berhasil diperbarui!")
                        st.rerun()
                    if btn_del.form_submit_button(
                        "🗑️ Hapus Baris", use_container_width=True, type="secondary"
                    ):
                        with engine.begin() as conn:
                            conn.execute(
                                text("DELETE FROM matrix_indicators WHERE id=:id"),
                                {"id": row["id"]},
                            )
                        st.warning(f"Data ID #{row['id']} telah dihapus.")
                        st.rerun()
    else:
        st.info(
            "Database masih kosong atau belum terhubung. Silakan isi data di Tab 2."
        )

with tab5:
    st.subheader("📜 Rekam Jejak Analisis Intelligence")
    df_h = get_history()

    if df_h.empty:
        st.info("Belum ada riwayat analisis yang tersimpan.")
    else:
        col_f1, col_f2 = st.columns(2)
        filter_case = col_f1.multiselect(
            "Filter Sumber Case:", options=df_h["sumber_case"].unique(), default=[]
        )
        filter_fase = col_f2.multiselect(
            "Filter Fase Terdeteksi:", options=df_h["fase"].unique(), default=[]
        )
        filtered_df = df_h.copy()
        if filter_case:
            filtered_df = filtered_df[filtered_df["sumber_case"].isin(filter_case)]
        if filter_fase:
            filtered_df = filtered_df[filtered_df["fase"].isin(filter_fase)]
        st.dataframe(filtered_df, use_container_width=True)
        st.markdown("---")
        st.subheader("🔍 Detail Per Kejadian")
        list_ids = filtered_df["id"].tolist()
        if list_ids:
            selected_id = st.selectbox("Pilih ID Kejadian untuk Detail:", list_ids)
            if selected_id:
                detail = filtered_df[filtered_df["id"] == selected_id].iloc[0]
                c_det1, c_det2 = st.columns([1, 2])
                with c_det1:
                    st.write(f"**Waktu:** {detail['timestamp']}")
                    st.write(f"**Sumber:** {detail['sumber_case']}")
                    st.metric("Fase Terdeteksi", detail["fase"])
                    st.metric(
                        "Skor Keyakinan AI", f"{detail['skor_keyakinan']*100:.1f}%"
                    )
                with c_det2:
                    st.write("**Redaksi Kejadian:**")
                    st.info(detail["redaksi_input"])
                    st.write("**Struktur Matriks:**")
                    st.json(
                        {
                            "Dimensi": detail["dimensi"],
                            "Sub-Dimensi": detail["sub_dimensi"],
                            "Indikator": detail["indikator"],
                        }
                    )
                    st.write("**Rekomendasi Tindakan:**")
                    st.warning(detail["rekomendasi"])
        else:
            st.warning("Tidak ada data yang cocok dengan filter.")
        st.markdown("---")
        if st.button("🗑️ Bersihkan Seluruh Histori", type="secondary"):
            try:
                with engine.begin() as conn:
                    conn.execute(text("TRUNCATE TABLE analysis_history"))
                st.success("Histori berhasil dibersihkan!")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal membersihkan histori: {e}")
