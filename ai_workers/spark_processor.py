from pyspark.sql import SparkSession
from pyspark.sql.functions import year, from_json, col, udf, lower, regexp_replace, to_timestamp, current_timestamp, explode, get_json_object, lit, coalesce
from pyspark.sql.types import FloatType, StructType, StructField, StringType, ArrayType
from sentence_transformers import SentenceTransformer
import json
import sys
import uuid 
import time

# ==========================================
# 1. KONFIGURASI & LOGGING
# ==========================================
def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

# Schema Data Mentah dari Kafka
json_schema = StructType([
    StructField("created_at", StringType(), True),
    StructField("source", StringType(), True),
    StructField("title", StringType(), True),
    StructField("content", StringType(), True),
    StructField("url", StringType(), True),
    StructField("platform", StringType(), True),
    StructField("location", StringType(), True)
])

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

# --- 2. UDF GEOCODING (SINKRON DENGAN SCRAPER) ---
def get_lat(city):
    # Pastikan mengambil dari variabel global WILAYAH_COORDINATES
    res = WILAYAH_COORDINATES.get(city, WILAYAH_COORDINATES['Nasional'])
    return float(res[0]) # Latitude adalah elemen pertama

def get_lon(city):
    # Pastikan mengambil dari variabel global WILAYAH_COORDINATES
    res = WILAYAH_COORDINATES.get(city, WILAYAH_COORDINATES['Nasional'])
    return float(res[1]) # Longitude adalah elemen kedua

get_lat_udf = udf(get_lat, FloatType())
get_lon_udf = udf(get_lon, FloatType())

# ==========================================
# 3. UDF & AI LOGIC
# ==========================================
def calculate_intensity(text, sentiment_score):
    if not text: return 0.0
    weight = 1.0 
    high_risk_keywords = ['serang', 'bakar', 'darah', 'mati', 'hancur', 'bubarkan', 'ilegal', 'sesat']
    if any(word in str(text).lower() for word in high_risk_keywords):
        weight += 0.5
    intensity = weight + (abs(sentiment_score) if sentiment_score < 0 else 0)
    return float(intensity)

calculate_intensity_udf = udf(calculate_intensity, FloatType())

SENSITIVE_KEYWORDS = [
    "penolakan", "gereja", "masjid", "penistaan", "sesat", "kafir", 
    "bubarkan", "usir", "serang", "bakar", "hujat", "ilegal", 
    "penyegelan", "aliran menyimpang", "jihad", "serbu", "konflik", "agama"
]

def extract_keywords_func(text):
    if not text: return []
    found = [word for word in SENSITIVE_KEYWORDS if word in text.lower()]
    return found

keyword_udf = udf(extract_keywords_func, ArrayType(StringType()))

# Load AI Model
try:
    log("🧠 Loading AI Model...")
    model_ai = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except:
    model_ai = None

def analyze_emotion_and_sentiment(text_content):
    try:
        if not text_content: 
            return json.dumps({"sentiment": "neutral", "emotion": "none", "score": 0.5})
        
        text = text_content.lower()
        emotion = "neutral"
        score = 0.5
        
        if any(w in text for w in ["biadab", "kurang ajar", "lawan", "hancurkan", "laknat", "bakar"]):
            emotion = "anger"
            score = 0.85
        elif any(w in text for w in ["waspada", "khawatir", "ancaman", "bahaya", "terancam"]):
            emotion = "fear"
            score = 0.75
        elif any(w in text for w in ["sedih", "tangis", "korban"]):
            emotion = "sadness"
            score = 0.6
            
        sentiment = "negative" if score > 0.6 else "neutral"
        return json.dumps({"sentiment": sentiment, "score": score, "emotion": emotion})
    except: 
        return json.dumps({"sentiment": "error", "emotion": "none", "score": 0.0})

sentiment_udf = udf(analyze_emotion_and_sentiment, StringType())

# ==========================================
# 4. SPARK SESSION
# ==========================================
log("🔥 Inisialisasi Spark Session...")
spark = SparkSession.builder \
    .appName("EWS_Processor_Final_v2025") \
    .master("local[*]") \
    .config("spark.jars", "/app/jars/postgresql-42.5.0.jar,"
                          "/app/jars/spark-sql-kafka-0-10_2.12-3.5.0.jar,"
                          "/app/jars/spark-token-provider-kafka-0-10_2.12-3.5.0.jar,"
                          "/app/jars/kafka-clients-3.4.1.jar,"
                          "/app/jars/commons-pool2-2.11.1.jar,"
                          "/app/jars/hadoop-aws-3.3.4.jar,"
                          "/app/jars/aws-java-sdk-bundle-1.12.262.jar") \
    .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

db_properties = {"user": "ai_engine", "password": "p@5s@i_3n9ine", "driver": "org.postgresql.Driver"}
db_url = "jdbc:postgresql://db:5432/ai_engine_db"

# ==========================================
# 5. BATCH PROCESSING (SINK)
# ==========================================
def process_batch(batch_df, batch_id):
    count_data = batch_df.count()
    
    if count_data > 0:
        log(f"✅ [BATCH {batch_id}] Memproses {count_data} data asli tahun 2025.")
        
        # 1. Simpan ke Database Utama (Audit)
        try:
            db_main_df = batch_df.select("source", "title", "content", "url", "platform", "location", "latitude", "longitude", "created_at", "intensity")
            db_main_df.write.jdbc(url=db_url, table="social_media_reports", mode="append", properties=db_properties)
            log("   -> [DB] Tabel 'social_media_reports' UPDATE OK.")
        except Exception as e:
            log(f"   -> [DB ERROR] Laporan utama: {e}")

        # 2. Analisis Statistik (Layer 1 - Titik Individual)
        try:
            stats_df = batch_df.select(
                col("created_at").alias("timestamp"),
                explode(col("found_keywords")).alias("keyword"),
                lit(1.0).alias("jumlah"),
                "platform", "location", "latitude", "longitude"
            )
            stats_df.write.jdbc(url=db_url, table="risk_statistics", mode="append", properties=db_properties)
            log("   -> [ANALYTICS] Statistik Keyword OK.")
        except Exception as e:
            pass

        # 3. Analisis Emosi (Layer 2)
        try:
            # Ganti current_timestamp() dengan mengambil nilai dari kolom created_at
            emotion_analytics = batch_df.select(
                "platform",
                "created_at", # Pastikan kolom ini diselect
                get_json_object(col("sentiment_data"), "$.emotion").alias("emotion")
            ).groupBy("emotion", "platform", "created_at").count() \
             .withColumnRenamed("created_at", "timestamp") # Ubah nama agar sesuai tabel tujuan
            
            emotion_analytics.write.jdbc(url=db_url, table="emotion_statistics", mode="append", properties=db_properties)
            log("   -> [ANALYTICS] Statistik Emosi Sinkron OK.")
        except Exception as e:
            log(f"   -> [ANALYTICS ERROR] Emosi: {e}")
        
        # 4. Analisis Kecepatan Viralisasi (Layer 3)
        try:
            # 1. Pastikan created_at diikutkan dalam grouping atau pemilihan kolom
            viral_df = batch_df.groupBy("platform", "created_at").count() \
                .withColumnRenamed("count", "velocity") \
                .withColumnRenamed("created_at", "timestamp") \
                .withColumn("unique_users", lit(count_data)) \
                .withColumn("batch_id", lit(batch_id))
            
            # 2. Kirim ke Database
            viral_df.write.jdbc(url=db_url, table="viral_acceleration", mode="append", properties=db_properties)
            log("   -> [ANALYTICS] Statistik Viralisasi Sinkron OK.")
        except Exception as e:
            log(f"   -> [ANALYTICS ERROR] Viralisasi: {e}")

# ==========================================
# 6. STREAMING PIPELINE
# ==========================================
log("📡 Connecting to Kafka (ews_raw_data)...")

df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "ews_raw_data") \
    .option("startingOffsets", "earliest") \
    .load()

# Step A: Deklarasikan df_parsed pertama kali
df_parsed = df_raw.selectExpr("CAST(value AS STRING) as json_payload") \
    .select(from_json(col("json_payload"), json_schema).alias("data")) \
    .select("data.*")

# Step B: Penanganan Tanggal & FILTER 2025
df_enriched = df_parsed \
    .withColumn("parsed_time", to_timestamp(col("created_at"))) \
    .withColumn("created_at", coalesce(col("parsed_time"), current_timestamp())) \
    .drop("parsed_time") \

# Step C: Geocoding & Analisis Konten
df_enriched = df_enriched \
    .withColumn("location", coalesce(col("location"), lit("Nasional"))) \
    .withColumn("latitude", get_lat_udf(col("location"))) \
    .withColumn("longitude", get_lon_udf(col("location"))) \
    .withColumn("clean_content", regexp_replace(lower(col("content")), "[^a-zA-Z0-9\\s]", "")) \
    .withColumn("found_keywords", keyword_udf(col("clean_content"))) \
    .withColumn("sentiment_data", sentiment_udf(col("clean_content"))) \
    .withColumn("sentiment_score", get_json_object(col("sentiment_data"), "$.score").cast("float")) \
    .withColumn("intensity", calculate_intensity_udf(col("clean_content"), col("sentiment_score")))

# GENERATE CHECKPOINT UNIK
checkpoint_dir = f"/tmp/spark_checkpoint_{uuid.uuid4().hex}"
log(f"🚀 Pipeline 2025 dimulai! CP: {checkpoint_dir}")

query = df_enriched.writeStream \
    .foreachBatch(process_batch) \
    .option("checkpointLocation", checkpoint_dir) \
    .start()

query.awaitTermination()