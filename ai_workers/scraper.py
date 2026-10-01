import time
from urllib import response
import feedparser
import threading
import json
import requests
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from googleapiclient.discovery import build
from datetime import datetime
from newspaper import Article, Config
from googlenewsdecoder import new_decoderv1
from kafka import KafkaProducer

# ==========================================
# 1. KONFIGURASI API & DATABASE
# ==========================================
YOUTUBE_API_KEY = "AIzaSyBT8hjvAEdSdJpEP5Gn9r-nSObjjuLxofs"
# Gunakan nama service postgres_db sesuai docker-compose
encoded_password = quote_plus("p@5s@i_3n9ine")
DB_URL = f"postgresql://ai_engine:{encoded_password}@db:5432/ai_engine_db"
engine = create_engine(DB_URL)

# Konfigurasi Scraper News
config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
config.request_timeout = 15

# ==========================================
# 2. INGESTION LAYER: KAFKA PRODUCER (DIPERBAIKI)
# ==========================================
# Ambil broker dari env docker, default ke kafka:9092
broker = os.getenv('KAFKA_BROKER', 'kafka:9092') 

try:
    producer = KafkaProducer(
        bootstrap_servers=[broker],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',
        retries=5,
        request_timeout_ms=30000
    )
    print(f"🚀 [KAFKA] Producer terhubung ke Broker: {broker}")
except Exception as e:
    print(f"❌ [KAFKA] Gagal inisialisasi Producer: {e}")
    producer = None

def send_to_kafka(topic, data):
    """Mengirim data ke antrian Kafka dengan Flush"""
    if producer:
        try:
            producer.send(topic, data)
            producer.flush() # Pastikan data benar-benar terkirim
            print(f"📡 [INGESTION] Data dikirim ke Kafka ({topic}): {data['title'][:40]}...")
        except Exception as e:
            print(f"⚠️ [KAFKA] Gagal kirim data: {e}")
    else:
        # Ini pesan yang sering muncul di log Anda, sekarang diproteksi
        print("❌ [KAFKA] Producer tidak aktif, data dilewati.")

# ==========================================
# 3. DATA SOURCE LOGIC
# ==========================================

# Tambahkan daftar kota untuk deteksi lokasi berita sederhana
# Kamus Koordinat Wilayah Indonesia (Titik Tetap)
WILAYAH_COORDINATES = {
    # --- PROVINSI & KOTA UTAMA ---
    'Aceh': (4.6951, 96.7494), 'Banda Aceh': (5.5483, 95.3238), 'Meulaboh': (4.1449, 96.1252),
    'Sumatera Utara': (2.1121, 99.3965), 'Medan': (3.5952, 98.6722), 'Deli Serdang': (3.5511, 98.8512),
    'Sumatera Barat': (-0.7399, 100.8000), 'Padang': (-0.9471, 100.4172),
    'Riau': (0.2933, 101.7068), 'Pekanbaru': (0.5071, 101.4478),
    'Kepulauan Riau': (3.9456, 108.1428), 'Batam': (1.1301, 104.0520),
    'Jambi': (-1.6186, 103.6238),
    'Sumatera Selatan': (-3.3194, 104.9144), 'Palembang': (-2.9761, 104.7754),
    'Bengkulu': (-3.7928, 102.2608),
    'Lampung': (-4.5586, 105.4068), 'Bandar Lampung': (-5.4292, 105.2611),
    'Kepulauan Bangka Belitung': (-2.7410, 106.4406),

    # --- JAWA (LEVEL KABUPATEN/KOTA) ---
    'DKI Jakarta': (-6.2088, 106.8456), 'Jakarta Pusat': (-6.1805, 106.8284),
    'Jawa Barat': (-7.0909, 107.6689), 'Bandung': (-6.9175, 107.6191), 'Bekasi': (-6.2383, 106.9756), 
    'Depok': (-6.4025, 106.7942), 'Bogor': (-6.5971, 106.8060), 'Cianjur': (-6.8222, 107.1394),
    'Sukabumi': (-6.9277, 106.9300), 'Tasikmalaya': (-7.3274, 108.2207), 'Garut': (-7.2279, 107.9087),
    'Cirebon': (-6.7320, 108.5523), 'Indramayu': (-6.3273, 108.3249), 'Majalengka': (-6.8361, 108.2278),
    'Banten': (-6.4058, 106.0600), 'Tangerang': (-6.1702, 106.6403), 'Serang': (-6.1153, 106.1510), 'Cilegon': (-6.0118, 106.0275),
    'Jawa Tengah': (-7.1510, 110.1403), 'Semarang': (-6.9667, 110.4167), 'Solo': (-7.5703, 110.8292), 'Surakarta': (-7.5703, 110.8292),
    'Cilacap': (-7.7167, 109.0167), 'Banyumas': (-7.4500, 109.2500), 'Brebes': (-6.8700, 108.9200),
    'DI Yogyakarta': (-7.8753, 110.4262), 'Sleman': (-7.7167, 110.3500), 'Bantul': (-7.8833, 110.3333),
    'Jawa Timur': (-7.5361, 112.2384), 'Surabaya': (-7.2575, 112.7521), 'Malang': (-7.9819, 112.6304),
    'Sampang': (-7.1450, 113.2500), 'Pamekasan': (-7.1600, 113.4800), 'Bangkalan': (-7.0300, 112.7500),
    'Sumenep': (-7.0000, 113.8500), 'Jember': (-8.1724, 113.6995), 'Banyuwangi': (-8.2192, 114.3691),

    # --- BALI & NUSA TENGGARA ---
    'Bali': (-8.3405, 115.0920), 'Denpasar': (-8.6705, 115.2126),
    'Nusa Tenggara Barat': (-8.6529, 117.3616), 'Mataram': (-8.5833, 116.1167), 'Bima': (-8.4667, 118.7167),
    'Nusa Tenggara Timur': (-8.6574, 121.0794), 'Kupang': (-10.1772, 123.6070),

    # --- KALIMANTAN ---
    'Kalimantan Barat': (-0.2788, 111.4753), 'Pontianak': (-0.0333, 109.3333), 'Kubu Raya': (-0.0100, 109.3300), 'Singkawang': (0.9167, 108.9833),
    'Kalimantan Tengah': (-1.6825, 113.3824), 'Palangkaraya': (-2.2100, 113.9200),
    'Kalimantan Selatan': (-3.0926, 115.2838), 'Banjarmasin': (-3.3167, 114.5833),
    'Kalimantan Timur': (0.4384, 116.4712), 'Samarinda': (-0.5000, 117.1500), 'Balikpapan': (-1.2667, 116.8333), 'IKN': (-0.9700, 116.7000),
    'Kalimantan Utara': (3.0731, 116.0414),

    # --- SULAWESI ---
    'Sulawesi Utara': (0.6247, 123.9750), 'Manado': (1.4833, 124.8333),
    'Sulawesi Tengah': (-1.4300, 121.4455), 'Palu': (-0.8917, 119.8706), 'Poso': (-1.3959, 120.7539),
    'Sulawesi Selatan': (-3.6688, 119.9740), 'Makassar': (-5.1476, 119.4327),
    'Sulawesi Tenggara': (-4.1449, 122.1746), 'Kendari': (-3.9667, 122.5833),
    'Gorontalo': (0.6999, 122.4467),
    'Sulawesi Barat': (-2.8441, 119.2321),

    # --- MALUKU & PAPUA ---
    'Maluku': (-3.2385, 130.1453), 'Ambon': (-3.6954, 128.1814),
    'Maluku Utara': (1.5709, 127.8088), 'Ternate': (0.7833, 127.3667),
    'Papua': (-4.2699, 138.0803), 'Jayapura': (-2.5330, 140.7170),
    'Papua Barat': (-1.3361, 133.1747), 'Manokwari': (-0.8500, 134.0667),
    'Papua Selatan': (-7.5000, 139.0000), 'Merauke': (-8.4667, 140.3333),
    'Papua Tengah': (-3.5000, 136.0000), 'Nabire': (-3.3667, 135.5000),
    'Papua Pegunungan': (-4.0000, 139.0000), 'Wamena': (-4.0167, 138.9000),
    'Papua Barat Daya': (-1.0000, 131.5000), 'Sorong': (-0.8833, 131.2500),
    
    # --- DEFAULT ---
    'Nasional': (-2.5489, 118.0149)
}

def detect_location(text_content):
    """
    Mendeteksi lokasi berdasarkan keyword dan mengembalikan Nama Wilayah, Lat, dan Lon tetap.
    """
    if not text_content: 
        return "Nasional", -2.5489, 118.0149

    for wilayah, coord in WILAYAH_COORDINATES.items():
        if wilayah.lower() in text_content.lower():
            # Menggunakan koordinat asli tanpa random/noise
            return wilayah, coord[0], coord[1]
            
    # Default ke titik tengah Indonesia jika tidak terdeteksi
    return "Nasional", -2.5489, 118.0149

def calculate_intensity(title, content):
    """
    Menghitung intensitas berdasarkan bobot kategori isu kerukunan.
    """
    if not title: title = ""
    if not content: content = ""
    
    text_data = (title + " " + content).lower()
    score = 1.0  # Skor dasar
    
    # Kamus Indikator sesuai kategori risiko
    indicators = {
        "kategori_anarki": {"weight": 10.0, "keywords": ["bakar", "serang", "rusak", "bentrok", "darah", "anarki"]},
        "kategori_provokasi": {"weight": 5.0, "keywords": ["sesat", "kafir", "tolak", "provokasi", "haramkan", "intoleran"]},
        "kategori_administratif": {"weight": 2.0, "keywords": ["izin", "imb", "wakaf", "sengketa", "skb", "lahan"]}
    }

    for cat, data in indicators.items():
        if any(word in text_data for word in data["keywords"]):
            if data["weight"] > score:
                score = data["weight"]
    
    return score

# Parameter Pencarian
KEYWORDS = ['konflik', 'agama', 'sengketa', 'ibadah', 'intoleransi', 'penodaan', 'gereja', 'masjid', 'sesat', 'kafir', 'penolakan']
YOUTUBE_KEYWORDS = "konflik agama OR sengketa ibadah OR penolakan gereja OR penolakan masjid OR intoleransi"

def init_db():
    """Inisialisasi tabel dengan kolom intensity untuk penilaian risiko"""
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS social_media_reports (
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
                );
            """))
            # Tambahkan kolom intensity jika tabel sudah ada tapi kolomnya belum ada
            conn.execute(text("""
                ALTER TABLE social_media_reports 
                ADD COLUMN IF NOT EXISTS intensity FLOAT DEFAULT 1.0;
            """))
            print("✅ [DB] Tabel social_media_reports siap dengan kolom intensity.")
    except Exception as e:
        print(f"⚠️ DB Init Warning: {e}")

def scrape_web_news():
    print(f"🌐 [{datetime.now().strftime('%H:%M:%S')}] Memulai Scraping Berita Web...")
    rss_urls = [
        "https://news.google.com/rss/search?q=konflik+agama+indonesia&hl=id&gl=ID&ceid=ID:id",
        "https://news.google.com/rss/search?q=sengketa+rumah+ibadah+indonesia&hl=id&gl=ID&ceid=ID:id"
    ]
    for rss_url in rss_urls:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title_raw = entry.title
            # Filter kata kunci di judul sebelum proses berat (decode URL)
            if any(key in title_raw.lower() for key in KEYWORDS):
                try:
                    # Mendapatkan URL asli dari Google News
                    decoded_res = new_decoderv1(entry.link, interval=1)
                    real_link = decoded_res.get('decoded_url') if decoded_res.get('status') else entry.link
                    
                    # --- CEK DUPLIKAT BERDASARKAN URL ---
                    with engine.connect() as conn:
                        check = conn.execute(
                            text("SELECT id FROM social_media_reports WHERE url = :u"), 
                            {"u": real_link}
                        ).fetchone()
                    
                    if not check:
                        article = Article(real_link, config=config)
                        article.download()
                        article.parse()
                        
                        # Validasi panjang konten agar data yang masuk berkualitas
                        if len(article.text) > 200:
                            # 1. Deteksi Lokasi Presisi (Tanpa Jittering/Random)
                            loc_name, lat, lon = detect_location(article.text)
                            
                            # 2. Hitung Intensitas (Berdasarkan bobot kategori)
                            skor_isu = calculate_intensity(title_raw, article.text)
                            
                            payload = {
                                "source": entry.source.get('title', 'News'),
                                "title": title_raw,
                                "content": article.text,
                                "url": real_link,
                                "platform": "News",
                                "intensity": skor_isu,
                                "created_at": entry.published,
                                "location": loc_name,
                                "latitude": lat,
                                "longitude": lon
                            }
                            send_to_kafka('ews_raw_data', payload)
                        else:
                            print(f"⏩ Skip: Konten berita terlalu pendek ({real_link[:40]}...)")
                    else:
                        # Log opsional jika ingin melihat berita yang sudah ada
                        pass 
                except Exception as e:
                    print(f"⚠️ Gagal memproses berita: {e}")
                    continue

def get_video_ids(query):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(q=query, part='snippet', type='video', maxResults=50, order='date', regionCode='ID', relevanceLanguage='id')
        response = request.execute()
        return [item['id']['videoId'] for item in response.get('items', [])]
    except Exception as e:
        print(f"❌ YOUTUBE SEARCH ERROR: {e}")
        return []

def scrape_youtube_comments(video_id):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        video_request = youtube.videos().list(part="snippet", id=video_id)
        video_response = video_request.execute()
        if not video_response.get('items'): return
        
        judul_video = video_response['items'][0]['snippet']['title']
        request = youtube.commentThreads().list(part="snippet", videoId=video_id, maxResults=100, textFormat="plainText")
        response = request.execute()
        
        c_count = 0
        for item in response.get('items', []):
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
            original_time = item['snippet']['topLevelComment']['snippet']['publishedAt']
            
            # --- 1. FILTER KEYWORD ---
            if any(key in comment.lower() for key in KEYWORDS):
                
                # --- 2. CEK DUPLIKAT KE DATABASE (Pindahkan ke Sini) ---
                with engine.connect() as conn:
                    duplicate_check = conn.execute(
                        text("SELECT id FROM social_media_reports WHERE content = :c AND url = :u"), 
                        {"c": comment, "u": f"https://youtu.be/{video_id}"}
                    ).fetchone()

                if not duplicate_check:
                    # --- 3. PROSES DATA JIKA BUKAN DUPLIKAT ---
                    skor_isu = calculate_intensity(judul_video, comment)
                    loc_name, lat, lon = detect_location(judul_video + " " + comment)
                    
                    payload = {
                        "source": author,
                        "title": judul_video,
                        "content": comment,
                        "url": f"https://youtu.be/{video_id}",
                        "platform": "YouTube",
                        "intensity": skor_isu,
                        "created_at": original_time,
                        "location": loc_name,
                        "latitude": lat,
                        "longitude": lon
                    }
                    send_to_kafka('ews_raw_data', payload)
                    c_count += 1
                else:
                    # Log opsional untuk melihat data yang dilewati
                    print(f"⏭️ Skipping duplicate YouTube comment from {author}")
        
        if c_count > 0:
            print(f"✅ YOUTUBE: Berhasil memfilter {c_count} komentar baru.")
            
    except Exception as e:
        if "commentsDisabled" not in str(e):
            print(f"⚠️ YOUTUBE ERROR ID {video_id}: {e}")

# ==========================================
# 4. EXECUTION ORCHESTRATOR
# ==========================================

def run_pipeline():
    while True:
        print(f"\n🚀 [{datetime.now().strftime('%H:%M:%S')}] SIKLUS INGESTION DIMULAI...")
        
        # Jalankan News
        t_news = threading.Thread(target=scrape_web_news)
        t_news.start()
        
        # Jalankan YouTube
        v_ids = get_video_ids(YOUTUBE_KEYWORDS)
        for v_id in v_ids:
            scrape_youtube_comments(v_id)
            time.sleep(1) # Delay antar video agar tidak kena limit quota
            
        t_news.join()
        print(f"💤 Siklus Selesai. Istirahat 1 jam...")
        time.sleep(3600)

if __name__ == "__main__":
    init_db()
    run_pipeline()