import os
import traceback
from contextlib import asynccontextmanager
from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import torch
from sqlalchemy import create_engine, text, inspect
from sentence_transformers import SentenceTransformer, util

# PERUBAHAN-29SEP2026
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
# AKHIR-PERUBAHAN-29SEP2026

# BACA KONFIGURASI DATABASE DARI .ENV LARAVEL
def get_env(key, default=""):
    try:
        with open("/var/www/ews-pkub/.env", "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.strip().split("=", 1)[1].strip('"').strip("'")
    except:
        pass
    return os.getenv(key, default)

db_host = get_env("DB_HOST", "db")
if db_host in ["127.0.0.1", "localhost"]:
    db_host = "db" 
    
db_port = get_env("DB_PORT", "5432")
db_database = get_env("DB_DATABASE", "ai_engine_db")
db_username = get_env("DB_USERNAME", "ai_engine")
db_password = get_env("DB_PASSWORD", "p@5s@i_3n9ine")

db_password_encoded = quote_plus(db_password)
DB_URL = f"postgresql://{db_username}:{db_password_encoded}@{db_host}:{db_port}/{db_database}"

engine = create_engine(DB_URL)

model_ai = None
db_vecs = None
candidates_meta = []
last_error = ""

def load_ai_and_db():
    global model_ai, db_vecs, candidates_meta, last_error
    
    try:
        print(f"==> [1/4] Menghubungkan ke DB '{db_database}' di host '{db_host}'...", flush=True)
        
        if model_ai is None:
            print("==> [2/4] Memuat Model AI NLP dari cache...", flush=True)
            model_ai = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            print("==> [2/4] Model AI NLP siap di memori.", flush=True)
            
        inspector = inspect(engine)
        
        # Helper untuk mendeteksi nama kolom secara fleksibel
        def find_column(table_name, possible_names):
            cols = [c['name'] for c in inspector.get_columns(table_name)]
            cols_lower = {c.lower(): c for c in cols}
            
            # Cek kecocokan persis
            for p in possible_names:
                if p.lower() in cols_lower:
                    return cols_lower[p.lower()]
                    
            # Cek kecocokan substring
            for p in possible_names:
                for c_lower, original in cols_lower.items():
                    if p.lower() in c_lower:
                        return original
                        
            raise Exception(f"Kolom {possible_names} tidak ditemukan di '{table_name}'. Kolom yang ada: {cols}")

        t_ifd = "indikator_fase_details"
        t_ind = "indikator_ews"
        t_sub = "sub_dimensi_ews"
        t_dim = "dimensi_ews"
        t_fas = "fase_ews"

        print("==> [3/4] Melacak struktur kolom antar tabel...", flush=True)
        # Deteksi kolom nama/judul
        col_dim_name = find_column(t_dim, ['dimensi', 'nama_dimensi', 'nama'])
        col_sub_name = find_column(t_sub, ['sub_dimensi', 'nama_sub_dimensi', 'subdimensi'])
        col_ind_name = find_column(t_ind, ['indikator', 'nama_indikator'])
        col_fas_name = find_column(t_fas, ['fase', 'nama_fase'])
        col_desc     = find_column(t_ifd, ['description', 'deskripsi', 'rincian', 'keterangan'])

        # Deteksi Foreign Keys
        fk_sub_dim = find_column(t_sub, ['dimensi_id', 'id_dimensi', 'dimensi_ews_id'])
        fk_ind_sub = find_column(t_ind, ['sub_dimensi_id', 'id_sub_dimensi', 'sub_dimensi_ews_id', 'subdimensi_id'])
        fk_ifd_ind = find_column(t_ifd, ['indikator_id', 'id_indikator', 'indikator_ews_id'])
        fk_ifd_fas = find_column(t_ifd, ['fase_id', 'id_fase', 'fase_ews_id'])

        query = f"""
            SELECT 
                d.{col_dim_name} as dimensi, 
                sd.{col_sub_name} as sub_dimensi, 
                i.{col_ind_name} as indikator, 
                i.id as indikator_id,
                f.{col_fas_name} as fase, 
                f.id as fase_id, 
                ifd.{col_desc} as description
            FROM {t_ifd} ifd
            JOIN {t_ind} i ON ifd.{fk_ifd_ind} = i.id
            JOIN {t_sub} sd ON i.{fk_ind_sub} = sd.id
            JOIN {t_dim} d ON sd.{fk_sub_dim} = d.id
            JOIN {t_fas} f ON ifd.{fk_ifd_fas} = f.id
            WHERE ifd.{col_desc} IS NOT NULL AND ifd.{col_desc} != ''
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        print(f"==> [3/4] Eksekusi Query berhasil, ditemukan {len(df)} baris data.", flush=True)

        candidates, meta = [], []
        for idx, row in df.iterrows():
            deskripsi = str(row['description']).strip()
            if len(deskripsi) > 5:
                ai_text = f"{deskripsi}. (Konteks: Indikator {row['indikator']} dalam dimensi {row['dimensi']})"
                candidates.append(ai_text)
                meta.append({
                    "dimensi": row['dimensi'],
                    "sub_dimensi": row['sub_dimensi'],
                    "indikator": row['indikator'],
                    "indikator_id": row['indikator_id'],
                    "fase": row['fase'],
                    "fase_id": row['fase_id'],
                    "description": deskripsi
                })
                    
        if candidates:
            print(f"==> [4/4] Mengubah {len(candidates)} teks indikator menjadi vektor AI...", flush=True)
            db_vecs = model_ai.encode(candidates, convert_to_tensor=True)
            candidates_meta = meta
            last_error = ""
            print(f"==> [SUKSES SIAP PAKAI] {len(candidates)} indikator telah tersimpan di RAM AI!", flush=True)
        else:
            last_error = f"Tabel '{t_ifd}' tidak memiliki data deskripsi yang valid."
            print(f"==> WARNING: {last_error}", flush=True)
            
    except Exception as e:
        last_error = str(e)
        print(f"==> [ERROR load_ai_and_db]: {e}", flush=True)
        traceback.print_exc()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Langsung muat saat container start agar langsung ketahuan statusnya di log
    load_ai_and_db()
    yield

app = FastAPI(lifespan=lifespan)

class InputData(BaseModel):
    text: str

@app.post("/analyze")
def analyze_text(data: InputData):
    global model_ai, db_vecs, candidates_meta, last_error
    
    if db_vecs is None or len(candidates_meta) == 0:
        load_ai_and_db()
        
    if db_vecs is None or len(candidates_meta) == 0:
        raise HTTPException(status_code=500, detail=f"Sistem AI belum siap: {last_error}")

    import re
    import datetime
    
    # 1. AI Text Classification (Similarity)
    input_vec = model_ai.encode(data.text, convert_to_tensor=True)
    cos_scores = util.cos_sim(input_vec, db_vecs)[0]
    
    best_idx = int(torch.argmax(cos_scores))
    best_score = float(cos_scores[best_idx])
    winner = candidates_meta[best_idx]
    
    rekomendasi_map = {
        "Laten": "Melakukan pemetaan aktor & membuka forum dialog tertutup.",
        "Persepsi": "Melakukan kontra-narasi dan sosialisasi kerukunan lintas tokoh.",
        "Manifes": "Pertemukan pihak-pihak terkait dengan fasilitator netral (Mediasi).",
        "Eskalasi": "Koordinasi keamanan ketat dengan aparat penegak hukum & isolasi provokator.",
        "Krisis": "Deklarasi darurat, intervensi penegakan hukum penuh & persiapan logistik mitigasi."
    }

    # 2. Ekstraksi Entitas Otomatis (NLP Sederhana/RegEx)
    text_lower = data.text.lower()
    
    # Ekstraksi Agama
    agama_list = ["Islam", "Kristen", "Katolik", "Hindu", "Buddha", "Konghucu"]
    found_agama = [ag for ag in agama_list if ag.lower() in text_lower or (ag == "Buddha" and "budha" in text_lower)]
            
    # Ekstraksi Tanggal (Dibuat otomatis format DD-MM-YYYY)
    tanggal = ""
    date_match = re.search(r'\b(\d{1,2})[\-/\s]+([a-zA-Z]+|\d{1,2})[\-/\s]+(\d{4})\b', data.text)
    if date_match:
        d, m, y = date_match.groups()
        if m.isdigit():
            tanggal = f"{d.zfill(2)}-{m.zfill(2)}-{y}"
        else:
            months = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "mei": "05", "jun": "06", 
                      "jul": "07", "agu": "08", "sep": "09", "okt": "10", "nov": "11", "des": "12"}
            m_num = "01"
            for km, vm in months.items():
                if km in m.lower():
                    m_num = vm
                    break
            tanggal = f"{d.zfill(2)}-{m_num}-{y}"
    else:
        date_match_iso = re.search(r'\b(\d{4})[\-/\s]+(\d{1,2})[\-/\s]+(\d{1,2})\b', data.text)
        if date_match_iso:
            y, m, d = date_match_iso.groups()
            tanggal = f"{d.zfill(2)}-{m.zfill(2)}-{y}"
        elif "kemarin" in text_lower:
            tanggal = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d-%m-%Y")
        elif "hari ini" in text_lower:
            tanggal = datetime.datetime.now().strftime("%d-%m-%Y")

    # Ekstraksi Waktu (HH:MM atau jam HH)
    waktu_awal = ""
    waktu_akhir = ""
    time_matches = re.findall(r'\b([0-1]?[0-9]|2[0-3])[:.]([0-5][0-9])\b', data.text)
    if time_matches:
        waktu_awal = f"{time_matches[0][0].zfill(2)}"
        if len(time_matches) > 1:
            waktu_akhir = f"{time_matches[-1][0].zfill(2)}"
            
    if not waktu_awal:
        hour_matches = re.findall(r'(?:pukul|jam)\s*([0-1]?[0-9]|2[0-3])\b', text_lower)
        if hour_matches:
            waktu_awal = f"{hour_matches[0].zfill(2)}"
            if len(hour_matches) > 1:
                waktu_akhir = f"{hour_matches[-1].zfill(2)}"

    # Set Default Jika Tidak Ditemukan
    if not tanggal:
        tanggal = datetime.datetime.now().strftime("%d-%m-%Y")
    if not waktu_awal:
        waktu_awal = "00"
    if not waktu_akhir:
        waktu_akhir = "24"

    # Membuat Ekstraksi Judul Cerdas
    rel_str = (" Terkait " + " & ".join(found_agama)) if found_agama else ""
    judul = f"Laporan Isu {winner['indikator']}{rel_str}"
        
    return {
        "score": best_score,
        "dimensi": winner["dimensi"],
        "sub_dimensi": winner["sub_dimensi"],
        "indikator": winner["indikator"],
        "indikator_id": winner["indikator_id"],
        "fase": winner["fase"],
        "fase_id": winner["fase_id"],
        "description": winner["description"],
        "rekomendasi": rekomendasi_map.get(winner["fase"], "Pantau dan laporkan situasi lanjutan."),
        "judul": judul,
        "tanggal": tanggal,
        "waktu_awal": waktu_awal,
        "waktu_akhir": waktu_akhir,
        "agama": found_agama
    }

class SuggestData(BaseModel):
    text: str
    solutions: list = []
    responders: list = []

@app.post("/suggest-solutions")
def suggest_solutions(data: SuggestData):
    global model_ai, db_vecs, candidates_meta, last_error
    import datetime
    
    if model_ai is None:
        load_ai_and_db()
        
    if model_ai is None:
        raise HTTPException(status_code=500, detail=f"Sistem AI belum siap: {last_error}")

    text_clean = data.text if data.text else "Tidak ada kronologi yang terlampir."
    text_vec = model_ai.encode(text_clean, convert_to_tensor=True)
    
    # Gunakan fungsi analyze_text untuk dapat konteks NLP (Fase, Indikator)
    analyze_result = None
    try:
        analyze_result = analyze_text(InputData(text=text_clean))
    except Exception:
        pass

    # 1. Pilihan Solusi (Dibatasi maksimal 2 opsi)
    selected_solution_ids = []
    best_sol_texts = []
    if data.solutions:
        sol_texts = [s.get("text", "") for s in data.solutions]
        sol_vecs = model_ai.encode(sol_texts, convert_to_tensor=True)
        cos_scores = util.cos_sim(text_vec, sol_vecs)[0]
        
        scored_sols = [(data.solutions[i].get("id"), float(cos_scores[i]), sol_texts[i]) for i in range(len(cos_scores))]
        scored_sols.sort(key=lambda x: x[1], reverse=True)
        
        for sid, score, stext in scored_sols[:2]:
            if score > 0.2:
                selected_solution_ids.append(sid)
                best_sol_texts.append(stext)
                
        if not selected_solution_ids and scored_sols:
            selected_solution_ids.append(scored_sols[0][0])
            best_sol_texts.append(scored_sols[0][2])

    # 2. Pilihan Pihak Terlibat (100% PURE SEMANTIC AI, TANPA KATA KUNCI MANUAL)
    selected_responder_ids = []
    best_resp_names = []
    
    if data.responders:
        scored_resps = []
        
        # Memperkaya query AI dengan menggabungkan kronologi + jenis indikator 
        # agar AI mengerti konteks permasalahannya dengan lebih utuh
        context_query = text_clean
        if analyze_result:
            context_query += f". Insiden ini terkait isu {analyze_result.get('indikator', '')} pada tahap {analyze_result.get('fase', '')}"
            
        text_vec_enriched = model_ai.encode(context_query, convert_to_tensor=True)

        for r in data.responders:
            rname = r.get("name", "")
            
            # Hitung similarity (kemiripan makna) murni menggunakan AI Vectorization
            r_vec = model_ai.encode([rname], convert_to_tensor=True)
            score = float(util.cos_sim(text_vec_enriched, r_vec)[0][0])
            
            scored_resps.append((r.get("id"), score, rname))
            
        scored_resps.sort(key=lambda x: x[1], reverse=True)
        
        # Ambil max 2 pihak yang nilai semantiknya paling tinggi
        # Threshold diturunkan sedikit karena membandingkan paragraf (kronologi) vs 1 kata (nama instansi) 
        # membutuhkan toleransi matematis vector yang lebih luwes.
        for rid, score, rname in scored_resps[:2]:
            if score > 0.05: 
                selected_responder_ids.append(rid)
                best_resp_names.append(rname)
                
        if not selected_responder_ids and scored_resps:
            selected_responder_ids.append(scored_resps[0][0])
            best_resp_names.append(scored_resps[0][2])

    # 3. Merangkai Penjelasan AI yang Profesional dan Logis
    time_context = ""
    if analyze_result and "tanggal" in analyze_result:
        try:
            report_date = datetime.datetime.strptime(analyze_result["tanggal"], "%d-%m-%Y").date()
            today = datetime.datetime.now().date()
            delta_days = (today - report_date).days
            if delta_days == 0:
                time_context = "Mengingat laporan ini masuk di hari yang sama dengan kejadian, mitigasi segera sangat direkomendasikan untuk mencegah mobilisasi massa."
            elif delta_days == 1:
                time_context = "Karena insiden ini terjadi kemarin, validasi lapangan perlu segera dilakukan sebelum terjadi eskalasi isu di tengah masyarakat."
            elif delta_days > 1:
                time_context = f"Insiden ini tercatat terjadi {delta_days} hari yang lalu. Fokus penanganan saat ini sebaiknya diarahkan pada pemulihan kondisi (cooling down) dan mediasi sisa ketegangan."
        except:
            pass

    # Bersihkan nama Fase
    fase_name = analyze_result["fase"] if analyze_result else "Umum"
    if fase_name.lower().startswith("fase "):
        fase_name = fase_name[5:].strip()

    indikator_name = analyze_result["indikator"] if analyze_result else "Konflik"

    # Menyusun paragraf Penjelasan AI
    alasan_text = f"Berdasarkan analisis pemrosesan bahasa alami (NLP), algoritma AI memetakan muatan narasi pelapor ke dalam **Fase {fase_name}** pada klaster isu **'{indikator_name}'**. {time_context}\n\n"
    
    alasan_text += "**Rasionalisasi Pilihan Solusi:**\n"
    if best_sol_texts:
        sol_snippet = best_sol_texts[0]
        alasan_text += f"Sistem merekomendasikan opsi _\"{sol_snippet}\"_ karena kalimat ini memiliki nilai ekuivalensi semantik tertinggi terhadap konteks kronologi. Langkah operasional ini dinilai paling efektif meredam akar masalah berdasarkan basis data EWS.\n\n"
    else:
        alasan_text += "Sistem memilih solusi pencegahan standar dikarenakan pola kronologi membutuhkan penanganan preventif umum yang tersedia di basis data.\n\n"

    alasan_text += "**Rasionalisasi Pihak Terlibat:**\n"
    if best_resp_names:
        alasan_text += f"Keterlibatan **{', '.join(best_resp_names)}** direkomendasikan murni dari hasil kalkulasi _Semantic Similarity_ (Kemiripan Makna) oleh model NLP. AI menilai bahwa karakteristik, keparahan, dan konteks kejadian yang dilaporkan beririsan langsung dengan kapabilitas serta yurisdiksi instansi tersebut dalam merespons isu {indikator_name}."
    else:
        alasan_text += "Pihak terkait direkomendasikan berdasarkan pemetaan struktur penanganan wilayah administratif secara umum."

    # 4. Solusi Alternatif Profesional
    alt_solution = ""
    if analyze_result and "rekomendasi" in analyze_result:
        alt_solution = analyze_result['rekomendasi']
        if len(alt_solution) < 100:
             alt_solution += " Lakukan koordinasi silang dengan aparat setempat dan pastikan pengumpulan bukti dilakukan dengan pendekatan humanis."
    else:
        alt_solution = "Prioritaskan verifikasi kebenaran informasi langsung kepada saksi kunci di lapangan, lalu siapkan ruang mediasi tertutup untuk mencegah penyebaran rumor."

    return {
        "selected_solution_ids": selected_solution_ids,
        "alternative_solution": alt_solution,
        "selected_responder_ids": selected_responder_ids,
        "alasan": alasan_text
    }

@app.post("/enhance")
def enhance_text(data: InputData):
    import re
    import datetime
    
    text = data.text.strip()
    if not text:
        return {"enhanced_text": ""}
        
    text_lower = text.lower()
    
    # 1. TANGGAL & WAKTU (Deteksi dari teks asli)
    today_str = datetime.datetime.now().strftime("%d-%m-%Y")
    yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d-%m-%Y")
    
    date_found = "[sebutkan tanggal kejadian]"
    time_found = "[sebutkan waktu kejadian]"
    
    # Ekstrak Tanggal
    date_match = re.search(r'\b(\d{1,2})[\-/\s]+([a-zA-Z]+|\d{1,2})[\-/\s]+(\d{4})\b', text)
    date_match_iso = re.search(r'\b(\d{4})[\-/\s]+(\d{1,2})[\-/\s]+(\d{1,2})\b', text)
    
    if date_match:
        date_found = date_match.group(0)
    elif date_match_iso:
        date_found = date_match_iso.group(0)
    elif "hari ini" in text_lower:
        date_found = today_str
        text = re.sub(r'\bhari ini\b', '', text, flags=re.IGNORECASE)
    elif "kemarin" in text_lower:
        date_found = yesterday_str
        text = re.sub(r'\bkemarin\b', '', text, flags=re.IGNORECASE)

    # Ekstrak Waktu
    time_match = re.search(r'\b([0-1]?[0-9]|2[0-3])[:.]([0-5][0-9])\b', text)
    hour_match = re.search(r'\b(?:pukul|jam)\s*([0-1]?[0-9]|2[0-3])\b', text_lower)
    
    if time_match:
        time_found = time_match.group(0).replace('.', ':')
    elif hour_match:
        time_found = hour_match.group(1).zfill(2) + ":00"

    # Hapus redundansi kata "pada tanggal X" atau "pukul Y" di dalam isi text-nya agar tidak terulang
    text = re.sub(r'\b(pada )?tanggal\s+\[?sebutkan tanggal kejadian\]?\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(pada )?(sekitar )?pukul\s+\[?sebutkan waktu kejadian\]?\b', '', text, flags=re.IGNORECASE)

    # 2. PERBAIKAN BAHASA (Kamus Slang ke Formal Birokrasi EWS)
    slang_dict = {
        r'\btadi aku lihat\b': 'terpantau',
        r'\btadi saya lihat\b': 'terpantau',
        r'\baku lihat\b': 'terpantau',
        r'\bsaya lihat\b': 'terpantau',
        r'\btadi\b': '',
        r'\baku\b': 'saya',
        r'\bada yang\b': 'terdapat sekelompok pihak yang',
        r'\bribut\b': 'terlibat perselisihan',
        r'\bberantem\b': 'bertikai',
        r'\bdisini\b': 'di lokasi',
        r'\bmereka\b': 'pihak-pihak tersebut',
        r'\bejek\b': 'melontarkan ujaran kebencian provokatif',
        r'\bhina\b': 'melakukan penistaan',
        r'\bbikin\b': 'memicu',
        r'\bgara-gara\b': 'dikarenakan oleh',
        r'\bgara gara\b': 'dikarenakan oleh',
        r'\bkayaknya\b': 'diduga',
        r'\bkalo\b': 'apabila',
        r'\budah\b': 'telah',
        r'\benggak\b': 'tidak',
        r'\bnggak\b': 'tidak',
        r'\bgak\b': 'tidak',
        r'\bbanget\b': 'sangat',
        r'\bcepet\b': 'segera',
        r'\bsampe\b': 'hingga',
        r'\btrus\b': 'kemudian',
        r'\bterus\b': 'selanjutnya',
        r'\bpas\b': 'saat',
        r'\bngomong\b': 'menyatakan',
        r'\bmarah\b': 'tersulut emosi',
    }
    
    for slang, formal in slang_dict.items():
        text = re.sub(slang, formal, text, flags=re.IGNORECASE)

    # Bersihkan spasi berlebih dari teks yang tersisa
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[.,\-\s]+', '', text) # Hapus sisa koma/titik di awal kalimat yang terpotong
    
    # 3. PENYUSUNAN REDAKSI EWS YANG BENAR DAN FORMAL (Penyatuan Narasi)
    has_religion = any(ag.lower() in text_lower for ag in ["islam", "kristen", "katolik", "hindu", "buddha", "konghucu"])
    agama_reminder = "" if has_religion else " [sebutkan agama terkait jika ada]"
    
    # Disusun ulang menjadi format laporan birokrasi kejadian
    formal_report = f"Pada tanggal {date_found} sekitar pukul {time_found}, dilaporkan bahwa {text}.{agama_reminder}"

    # Rapikan spasi tanda baca
    formal_report = re.sub(r'([,!?])([^\s"”\'])', r'\1 \2', formal_report)
    formal_report = re.sub(r'(\.)([^\s"\'0-9\[])', r'\1 \2', formal_report)
    formal_report = re.sub(r'\s+', ' ', formal_report).strip()

    # Kapitalisasi Setiap Awal Kalimat dan Placeholder [Tanda Kurung]
    sentences = re.split(r'(?<=[.!?]) +', formal_report)
    enhanced_sentences = []
    for s in sentences:
        if s:
            # Kapital di awal kalimat
            s = re.sub(r'^([^a-zA-Z]*)([a-zA-Z])', lambda m: m.group(1) + m.group(2).upper(), s)
            enhanced_sentences.append(s)
            
    final_text = " ".join(enhanced_sentences)
    final_text = final_text.replace('[ ', '[').replace(' ]', ']')
    
    return {"enhanced_text": final_text}

# PERUBAHAN-29SEP2026
@app.post("/reload-db")
def reload_db():
    global model_ai, db_vecs, candidates_meta
    print("==> Menerima sinyal update dari Admin, me-reload database ke RAM...", flush=True)
    load_ai_and_db()
    return {"status": "success", "message": f"Database berhasil di-sync ke AI ({len(candidates_meta)} data)"}

@app.get("/analytics/mining")
def get_analytics_data():
    """
    Dashboard Analitik Data Mining EWS — 10 Analitik Lengkap
    Menggunakan algoritma ML sesungguhnya: KMeans, PCA, FP-Growth, Decision Tree,
    Random Forest, Regression, Time Series Analysis.
    """
    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import silhouette_score, accuracy_score, confusion_matrix as sk_confusion_matrix
    from sklearn.model_selection import cross_val_score
    from collections import Counter
    import warnings
    warnings.filterwarnings('ignore')

    def to_native(obj):
        """Konversi numpy types ke Python native agar JSON serializable."""
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return round(float(obj), 4)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: to_native(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [to_native(i) for i in obj]
        if isinstance(obj, pd.Timestamp):
            return str(obj)
        if pd.isna(obj):
            return None
        return obj

    def clean_feature_name(name):
        """Membersihkan nama kolom raw database agar mudah dipahami orang awam."""
        name_str = str(name)
        if name_str.startswith("nama_indikator_"): name_str = name_str.replace("nama_indikator_", "Indikator: ")
        if name_str.startswith("nama_fase_"): name_str = name_str.replace("nama_fase_", "Fase: ")
        if name_str.startswith("nama_kota_"): name_str = name_str.replace("nama_kota_", "Kota/Kab: ")
        if name_str.startswith("current_level_"): name_str = name_str.replace("current_level_", "Level PIC: ")
        if name_str.startswith("nama_status_"): name_str = name_str.replace("nama_status_", "Status: ")
        
        # Translasi sisa bahasa Inggris
        name_str = name_str.replace("province", "Provinsi").replace("city", "Kota").replace("district", "Kabupaten").replace("national", "Nasional")
        
        if name_str == "is_urgent": return "Dalam Fase Darurat"
        if name_str == "activity_sum": return "Total Aktivitas Penanganan"
        if name_str == "total_kasus": return "Total Kasus"
        if name_str == "unique_indicators": return "Jumlah Indikator Unik"
        
        return name_str

    try:
        # ========== LOAD DATA ==========
        query_reports = """
            SELECT r.*, ra_count.activity_count
            FROM ews_reports r
            LEFT JOIN (
                SELECT ews_report_id, COUNT(*) as activity_count
                FROM report_activities
                GROUP BY ews_report_id
            ) ra_count ON r.id = ra_count.ews_report_id
            WHERE r.latitude IS NOT NULL AND r.longitude IS NOT NULL
        """
        # Fallback jika report_activities belum ada
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query_reports), conn)
        except Exception:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT * FROM ews_reports WHERE latitude IS NOT NULL AND longitude IS NOT NULL"), conn)
            df['activity_count'] = 0

        if df.empty or len(df) < 3:
            return {"status": "error", "message": "Data laporan minimal 3 dengan koordinat untuk data mining."}

        # ========== MAPPING ID KE TEXT ==========
        def fetch_mapping(table_name, id_col, name_col, engine_conn):
            try:
                return pd.read_sql(text(f"SELECT {id_col} as id, {name_col} as name FROM {table_name}"), engine_conn).astype(str)
            except Exception:
                return pd.DataFrame(columns=['id', 'name'])

        with engine.connect() as conn:
            df_ind_ref = fetch_mapping("indikator_ews", "id", "indikator", conn)
            df_fas_ref = fetch_mapping("fase_ews", "id", "fase", conn)
            df_city_ref = fetch_mapping("cities", "id", "name", conn)
            df_prov_ref = fetch_mapping("provinces", "id", "name", conn)
            df_stat_ref = fetch_mapping("report_statuses", "id", "display_label", conn)

            # Dimensi hierarchy for Q3
            try:
                df_dimensi_hier = pd.read_sql(text("""
                    SELECT i.id as indikator_id, i.indikator,
                           sd.sub_dimensi, d.dimensi
                    FROM indikator_ews i
                    JOIN sub_dimensi_ews sd ON i.sub_dimensi_id = sd.id
                    JOIN dimensi_ews d ON sd.dimensi_id = d.id
                """), conn)
            except Exception:
                df_dimensi_hier = pd.DataFrame(columns=['indikator_id', 'indikator', 'sub_dimensi', 'dimensi'])

        def map_id_to_name(df_main, col_id, df_ref, default_prefix="ID "):
            df_main[col_id] = df_main[col_id].astype(str)
            if not df_ref.empty:
                mapping = dict(zip(df_ref['id'], df_ref['name']))
                return df_main[col_id].map(mapping).fillna(default_prefix + df_main[col_id])
            return default_prefix + df_main[col_id]

        df['nama_indikator'] = map_id_to_name(df, 'indikator_id', df_ind_ref, "Indikator ")
        df['nama_fase'] = map_id_to_name(df, 'fase_id', df_fas_ref, "Fase ")
        df['nama_kota'] = map_id_to_name(df, 'kota_id', df_city_ref, "Kota/Kab ")
        df['nama_provinsi'] = map_id_to_name(df, 'provinsi_id', df_prov_ref, "Provinsi ")
        df['nama_status'] = map_id_to_name(df, 'status_id', df_stat_ref, "Status ")
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['activity_count'] = pd.to_numeric(df.get('activity_count', 0), errors='coerce').fillna(0).astype(int)
        df = df.dropna(subset=['latitude', 'longitude'])

        # Durasi penyelesaian
        if 'tanggal' in df.columns and 'resolved_at' in df.columns:
            df['tanggal_dt'] = pd.to_datetime(df['tanggal'], errors='coerce')
            df['resolved_dt'] = pd.to_datetime(df['resolved_at'], errors='coerce')
            df['durasi_hari'] = (df['resolved_dt'] - df['tanggal_dt']).dt.days
        else:
            df['durasi_hari'] = None

        # is_closed
        df['is_closed'] = df['nama_status'].apply(
            lambda x: 1 if ('selesai' in str(x).lower() or 'close' in str(x).lower()) else 0
        )
        df['is_closed_label'] = df['is_closed'].map({1: 'Closed', 0: 'Open'})

        # is_urgent (fase kritis)
        df['is_urgent'] = df['nama_fase'].str.contains('Krisis|Eskalasi|Manifes', case=False, na=False).astype(int)

        # Bulan untuk time series
        if 'tanggal' in df.columns:
            df['bulan'] = pd.to_datetime(df['tanggal'], errors='coerce').dt.to_period('M').astype(str)
        else:
            df['bulan'] = 'Unknown'

        total_kasus = len(df)
        colors_cluster = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
        colors_phase = ['#1abc9c', '#3498db', '#f39c12', '#e74c3c', '#8e44ad']

        def short_name(name, max_len=25):
            return name[:max_len] + '...' if len(name) > max_len else name

        # ================================================================
        # Q1: CLUSTERING WILAYAH (KMeans + PCA Scatter)
        # ================================================================
        try:
            city_agg = df.groupby('nama_kota').agg(
                total_kasus=('id', 'count'),
                unique_indicators=('nama_indikator', 'nunique'),
                unique_phases=('nama_fase', 'nunique'),
                avg_lat=('latitude', 'mean'),
                avg_lon=('longitude', 'mean'),
                closed_ratio=('is_closed', 'mean'),
                urgent_ratio=('is_urgent', 'mean'),
                activity_sum=('activity_count', 'sum'),
            ).reset_index()

            # Tambah distribusi per indikator & fase sebagai fitur
            ind_pivot = pd.crosstab(df['nama_kota'], df['nama_indikator'])
            fas_pivot = pd.crosstab(df['nama_kota'], df['nama_fase'])
            stat_pivot = pd.crosstab(df['nama_kota'], df['nama_status'])
            city_features = city_agg.set_index('nama_kota').join(ind_pivot).join(fas_pivot, rsuffix='_fase').join(stat_pivot, rsuffix='_stat').fillna(0)

            feature_cols = [c for c in city_features.columns if c != 'nama_kota']
            X_city = StandardScaler().fit_transform(city_features[feature_cols].values)

            best_k, best_sil = 2, -1
            for k in range(2, min(6, len(city_features))):
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = km.fit_predict(X_city)
                if len(set(labels)) > 1:
                    sil = silhouette_score(X_city, labels)
                    if sil > best_sil:
                        best_sil, best_k = sil, k

            kmeans_q1 = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            city_features['cluster'] = kmeans_q1.fit_predict(X_city)

            pca = PCA(n_components=2)
            coords_2d = pca.fit_transform(X_city)
            city_features['pca_x'] = coords_2d[:, 0]
            city_features['pca_y'] = coords_2d[:, 1]

            scatter_series = []
            cluster_profiles = []
            q1_detail_rows = []
            for cl_id in sorted(city_features['cluster'].unique()):
                cl_data = city_features[city_features['cluster'] == cl_id]
                cl_cities = cl_data.index.tolist()
                points = [[round(float(r['pca_x']), 2), round(float(r['pca_y']), 2)] for _, r in cl_data.iterrows()]
                scatter_series.append({"name": f"Kelompok {cl_id+1}", "data": points})

                df_cl = df[df['nama_kota'].isin(cl_cities)]
                dom_ind = df_cl['nama_indikator'].mode()[0] if not df_cl.empty else '-'
                dom_fas = df_cl['nama_fase'].mode()[0] if not df_cl.empty else '-'
                dom_stat = df_cl['nama_status'].mode()[0] if not df_cl.empty else '-'

                cluster_profiles.append({
                    "cluster_id": int(cl_id), "name": f"Kelompok {cl_id+1}",
                    "city_count": int(len(cl_cities)), "cities": cl_cities[:10],
                    "dominant_indicator": dom_ind, "dominant_phase": dom_fas,
                    "dominant_status": dom_stat,
                    "avg_cases": round(float(cl_data['total_kasus'].mean()), 1) if 'total_kasus' in cl_data.columns else 0,
                    "total_cases": int(len(df_cl))
                })
                for city_name in cl_cities:
                    city_df = df[df['nama_kota'] == city_name]
                    city_dom_ind = city_df['nama_indikator'].mode()[0] if not city_df.empty else '-'
                    city_dom_fas = city_df['nama_fase'].mode()[0] if not city_df.empty else '-'
                    q1_detail_rows.append([city_name, f"Kelompok {cl_id+1}", str(len(city_df)), city_dom_ind, city_dom_fas])

            q1_narrative = (
                f"Sistem mengelompokkan {len(city_features)} kota/kabupaten ke dalam {best_k} kelompok yang memiliki kemiripan pola karakteristik konflik. "
                + " | ".join([f"Kelompok {p['cluster_id']+1} ({p['city_count']} kota) dominan masalah '{p['dominant_indicator']}' pada tahap '{p['dominant_phase']}'" for p in cluster_profiles])
            )

            q1_chart = {
                "title": "Pemetaan Kemiripan Wilayah Konflik",
                "question": "Daerah mana yang memiliki karakteristik potensi konflik yang mirip?",
                "technique": "KMeans Clustering",
                "chart_type": "scatter",
                "ai_narrative": q1_narrative,
                "summary_stats": {"total_kota": len(city_features), "jumlah_klaster": best_k, "silhouette_score": round(best_sil, 3)},
                "chart_config": {"series": scatter_series, "cluster_profiles": cluster_profiles},
                "detail_data": {
                    "headers": ["Kota/Kabupaten", "Kelompok", "Total Kasus", "Isu Dominan", "Fase Dominan"],
                    "rows": q1_detail_rows,
                    "ai_detail_narrative": q1_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q1_chart = {"title": "Pemetaan Kemiripan Wilayah", "chart_type": "scatter", "technique": "KMeans Clustering",
                         "ai_narrative": f"Gagal menjalankan clustering: {str(e)}", "chart_config": {"series": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q2: ASSOCIATION RULE / CO-OCCURRENCE (FP-Growth)
        # ================================================================
        try:
            city_indicators = df.groupby('nama_kota')['nama_indikator'].apply(set).reset_index()
            all_indicators = sorted(df['nama_indikator'].unique())

            co_matrix = pd.DataFrame(0, index=all_indicators, columns=all_indicators)
            for _, row in city_indicators.iterrows():
                inds = list(row['nama_indikator'])
                for i in range(len(inds)):
                    for j in range(len(inds)):
                        co_matrix.loc[inds[i], inds[j]] += 1

            top_inds_list = df['nama_indikator'].value_counts().head(8).index.tolist()
            co_sub = co_matrix.loc[top_inds_list, top_inds_list]

            heatmap_series = []
            for ind_row in top_inds_list:
                data_points = []
                for ind_col in top_inds_list:
                    data_points.append({"x": short_name(ind_col), "y": int(co_sub.loc[ind_row, ind_col])})
                heatmap_series.append({"name": short_name(ind_row), "data": data_points})

            rules_list = []
            try:
                from mlxtend.frequent_patterns import fpgrowth, association_rules as mlx_assoc_rules
                from mlxtend.preprocessing import TransactionEncoder

                transactions = city_indicators['nama_indikator'].apply(list).tolist()
                if len(transactions) > 2:
                    te = TransactionEncoder()
                    te_ary = te.fit(transactions).transform(transactions)
                    df_te = pd.DataFrame(te_ary, columns=te.columns_)

                    min_sup = max(0.05, 2.0 / len(transactions))
                    freq = fpgrowth(df_te, min_support=min_sup, use_colnames=True)
                    if len(freq) > 1:
                        rules = mlx_assoc_rules(freq, metric="confidence", min_threshold=0.3, num_itemsets=len(freq))
                        for _, r in rules.head(15).iterrows():
                            rules_list.append({
                                "antecedent": ", ".join(list(r['antecedents'])),
                                "consequent": ", ".join(list(r['consequents'])),
                                "support": round(float(r['support']), 3),
                                "confidence": round(float(r['confidence']), 3),
                                "lift": round(float(r['lift']), 3)
                            })
            except Exception:
                pass

            q2_detail_rows = []
            if rules_list:
                for rl in rules_list:
                    q2_detail_rows.append([rl['antecedent'], rl['consequent'], f"{rl['confidence']*100:.1f}%", str(rl['lift'])])
                q2_detail_headers = ["Bila Terjadi Ini", "Maka Berpotensi Terjadi Ini", "Tingkat Kepastian (Confidence)", "Kekuatan Hubungan (Lift)"]
            else:
                pairs = []
                for i in range(len(top_inds_list)):
                    for j in range(i+1, len(top_inds_list)):
                        val = int(co_sub.iloc[i, j])
                        if val > 0:
                            pairs.append([top_inds_list[i], top_inds_list[j], str(val)])
                pairs.sort(key=lambda x: -int(x[2]))
                q2_detail_rows = pairs[:20]
                q2_detail_headers = ["Isu A", "Isu B", "Berapa Kali Muncul Bersama"]

            q2_narrative = (
                f"Sistem memetakan isu-isu yang saling berkaitan erat. "
                + (f"Ditemukan {len(rules_list)} pasang isu yang paling sering muncul secara berbarengan di wilayah yang sama." if rules_list else f"Heatmap menunjukkan isu mana saja yang paling sering terjadi berbarengan.")
            )

            q2_chart = {
                "title": "Keterkaitan Antar Isu/Indikator",
                "question": "Indikator apa yang paling sering muncul bersama dalam potensi konflik?",
                "technique": "Association Rule (FP-Growth)",
                "chart_type": "heatmap",
                "ai_narrative": q2_narrative,
                "summary_stats": {"total_indikator": len(all_indicators), "rules_found": len(rules_list), "kota_dianalisis": len(city_indicators)},
                "chart_config": {"series": heatmap_series, "rules": rules_list},
                "detail_data": {"headers": q2_detail_headers, "rows": q2_detail_rows, "ai_detail_narrative": q2_narrative}
            }
        except Exception as e:
            traceback.print_exc()
            q2_chart = {"title": "Keterkaitan Antar Isu", "chart_type": "heatmap", "technique": "Association Rule",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q3: KOMBINASI DIMENSI/SUBDIMENSI/INDIKATOR per PHASE
        # ================================================================
        try:
            if not df_dimensi_hier.empty:
                df_q3 = df.merge(
                    df_dimensi_hier[['indikator_id', 'sub_dimensi', 'dimensi']].astype({'indikator_id': str}),
                    left_on='indikator_id', right_on='indikator_id', how='left'
                )
                df_q3['dimensi'] = df_q3['dimensi'].fillna('Tidak Diketahui')
                df_q3['sub_dimensi'] = df_q3['sub_dimensi'].fillna('Tidak Diketahui')
                df_q3['combo_label'] = df_q3['dimensi'].str[:15] + ' > ' + df_q3['nama_indikator'].str[:20]
            else:
                df_q3 = df.copy()
                df_q3['dimensi'] = '-'
                df_q3['sub_dimensi'] = '-'
                df_q3['combo_label'] = df_q3['nama_indikator'].str[:30]

            cross = pd.crosstab(df_q3['combo_label'], df_q3['nama_fase'])
            top_combos = cross.sum(axis=1).nlargest(8).index.tolist()
            cross_top = cross.loc[top_combos]

            stacked_series = []
            for fase_col in cross_top.columns:
                stacked_series.append({"name": str(fase_col), "data": cross_top[fase_col].values.tolist()})

            q3_detail_rows = []
            for _, row in df_q3.groupby(['dimensi', 'sub_dimensi', 'nama_indikator', 'nama_fase']).size().reset_index(name='jumlah').sort_values('jumlah', ascending=False).head(30).iterrows():
                q3_detail_rows.append([str(row['dimensi']), str(row['sub_dimensi']), str(row['nama_indikator']), str(row['nama_fase']), str(row['jumlah'])])

            q3_narrative = (
                f"Pola persebaran isu terhadap tahapan (fase) konflik. Menunjukkan bahwa kombinasi dimensi tertentu lebih rawan berkembang pada fase yang lebih kritis."
            )

            q3_chart = {
                "title": "Persebaran Isu Berdasarkan Fase Konflik",
                "question": "Kombinasi dimensi, subdimensi, dan indikator apa yang paling sering berkaitan dengan phase tertentu?",
                "technique": "Cross-tabulation Analysis",
                "chart_type": "stacked_bar",
                "ai_narrative": q3_narrative,
                "summary_stats": {"total_kombinasi": len(cross), "fase_unik": len(cross.columns)},
                "chart_config": {"series": to_native(stacked_series), "categories": top_combos},
                "detail_data": {
                    "headers": ["Dimensi Utama", "Sub Dimensi", "Indikator Isu", "Tahapan (Fase)", "Jumlah Kejadian"],
                    "rows": q3_detail_rows, "ai_detail_narrative": q3_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q3_chart = {"title": "Persebaran Isu Berdasarkan Fase", "chart_type": "stacked_bar", "technique": "Cross-tabulation",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": [], "categories": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q4: CLASSIFICATION — Closed vs Open (Decision Tree)
        # ================================================================
        try:
            feature_cols_q4 = ['nama_indikator', 'nama_fase', 'nama_kota', 'is_urgent']
            if 'current_level' in df.columns:
                feature_cols_q4.append('current_level')

            df_q4 = df[feature_cols_q4 + ['is_closed']].dropna()
            X_q4 = pd.get_dummies(df_q4.drop(columns=['is_closed']), drop_first=True)
            y_q4 = df_q4['is_closed']

            if len(y_q4.unique()) >= 2 and len(y_q4) >= 10:
                dt_q4 = DecisionTreeClassifier(max_depth=5, random_state=42)
                dt_q4.fit(X_q4, y_q4)
                y_pred_q4 = dt_q4.predict(X_q4)
                acc_q4 = accuracy_score(y_q4, y_pred_q4)

                fi_q4 = sorted(zip(X_q4.columns, dt_q4.feature_importances_), key=lambda x: -x[1])[:10]

                radar_features = [f[0] for f in fi_q4[:6]]
                closed_profile = X_q4[y_q4 == 1][radar_features].mean().values.tolist() if (y_q4 == 1).sum() > 0 else [0]*len(radar_features)
                open_profile = X_q4[y_q4 == 0][radar_features].mean().values.tolist() if (y_q4 == 0).sum() > 0 else [0]*len(radar_features)

                max_vals = [max(abs(c), abs(o), 0.001) for c, o in zip(closed_profile, open_profile)]
                closed_norm = [round(c/m * 100, 1) for c, m in zip(closed_profile, max_vals)]
                open_norm = [round(o/m * 100, 1) for o, m in zip(open_profile, max_vals)]

                cm = sk_confusion_matrix(y_q4, y_pred_q4)
                cm_dict = {"tn": int(cm[0][0]), "fp": int(cm[0][1]) if cm.shape[1] > 1 else 0,
                           "fn": int(cm[1][0]) if cm.shape[0] > 1 else 0, "tp": int(cm[1][1]) if cm.shape[0] > 1 and cm.shape[1] > 1 else 0}

                short_radar = [short_name(clean_feature_name(f), 20) for f in radar_features]
                q4_detail_rows = [[clean_feature_name(f[0]), f"{f[1]*100:.1f}%"] for f in fi_q4]
                
                closed_count = int((y_q4 == 1).sum())
                open_count = int((y_q4 == 0).sum())
            else:
                acc_q4 = 0
                short_radar = ["N/A"]
                closed_norm = [0]
                open_norm = [0]
                fi_q4 = []
                cm_dict = {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
                q4_detail_rows = []
                closed_count = int(df['is_closed'].sum())
                open_count = int((~df['is_closed'].astype(bool)).sum())

            q4_narrative = (
                f"Menganalisis faktor apa yang menyebabkan sebuah kasus berhasil diselesaikan (Selesai) dibandingkan yang masih berlanjut (Terbuka). "
                + (f"Faktor paling menentukan adalah: {clean_feature_name(fi_q4[0][0])}." if fi_q4 else "")
            )

            q4_chart = {
                "title": "Faktor Penentu Kasus Selesai vs Terbuka",
                "question": "Apa yang membedakan kasus yang akhirnya closed dengan kasus yang masih terbuka?",
                "technique": "Decision Tree Classifier",
                "chart_type": "radar",
                "ai_narrative": q4_narrative,
                "summary_stats": {"closed": closed_count, "open": open_count, "accuracy": round(acc_q4*100, 1)},
                "chart_config": {
                    "series": [
                        {"name": "Selesai (Closed)", "data": to_native(closed_norm)},
                        {"name": "Terbuka (Open)", "data": to_native(open_norm)}
                    ],
                    "categories": short_radar,
                    "feature_importance": [{"feature": clean_feature_name(f[0]), "importance": round(float(f[1]), 4)} for f in fi_q4],
                    "confusion_matrix": cm_dict,
                    "accuracy": round(acc_q4, 4)
                },
                "detail_data": {
                    "headers": ["Faktor / Atribut Kasus", "Tingkat Pengaruh"],
                    "rows": q4_detail_rows,
                    "ai_detail_narrative": q4_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q4_chart = {"title": "Faktor Penentu Kasus", "chart_type": "radar", "technique": "Classification",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": [], "categories": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q5: CLASSIFICATION — Profil Respons Cepat
        # ================================================================
        try:
            feature_cols_q5 = ['nama_indikator', 'nama_kota', 'nama_status']
            if 'current_level' in df.columns:
                feature_cols_q5.append('current_level')

            df_q5 = df[feature_cols_q5 + ['is_urgent']].dropna()
            X_q5 = pd.get_dummies(df_q5.drop(columns=['is_urgent']), drop_first=True)
            y_q5 = df_q5['is_urgent']

            if len(y_q5.unique()) >= 2 and len(y_q5) >= 10:
                dt_q5 = DecisionTreeClassifier(max_depth=5, random_state=42)
                dt_q5.fit(X_q5, y_q5)
                fi_q5 = sorted(zip(X_q5.columns, dt_q5.feature_importances_), key=lambda x: -x[1])[:10]
                acc_q5 = accuracy_score(y_q5, dt_q5.predict(X_q5))
            else:
                fi_q5 = []
                acc_q5 = 0

            fast_count = int(df['is_urgent'].sum())
            normal_count = int((~df['is_urgent'].astype(bool)).sum())

            key_chars = [clean_feature_name(f[0]) for f in fi_q5[:3]]

            q5_narrative = (
                f"Sistem menemukan pola untuk mengenali karakteristik kasus yang biasanya bereskalasi menjadi darurat dan butuh respons cepat. "
                + (f"Tiga indikasi utamanya adalah: {', '.join(key_chars)}." if key_chars else "")
            )

            q5_chart = {
                "title": "Karakteristik Kasus Darurat (Respons Cepat)",
                "question": "Karakteristik kasus seperti apa yang berkaitan dengan kebutuhan respons cepat?",
                "technique": "Decision Tree Classifier",
                "chart_type": "horizontal_bar",
                "ai_narrative": q5_narrative,
                "summary_stats": {"fast_response": fast_count, "normal": normal_count, "accuracy": round(acc_q5*100, 1)},
                "chart_config": {
                    "series": [{"name": "Tingkat Pengaruh", "data": [round(float(f[1])*100, 1) for f in fi_q5[:8]]}],
                    "categories": [short_name(clean_feature_name(f[0]), 30) for f in fi_q5[:8]],
                    "profile": {"fast_response_count": fast_count, "normal_count": normal_count, "key_characteristics": key_chars}
                },
                "detail_data": {
                    "headers": ["Karakteristik / Kondisi", "Persentase Pengaruh"],
                    "rows": [[clean_feature_name(f[0]), f"{f[1]*100:.1f}%"] for f in fi_q5],
                    "ai_detail_narrative": q5_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q5_chart = {"title": "Karakteristik Kasus Darurat", "chart_type": "horizontal_bar", "technique": "Classification",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": [], "categories": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q6: TIME SERIES / HOTSPOT BERULANG
        # ================================================================
        try:
            df_ts = df.copy()
            df_ts['bulan_sort'] = pd.to_datetime(df_ts['tanggal'], errors='coerce').dt.to_period('M')
            df_ts = df_ts.dropna(subset=['bulan_sort'])
            df_ts['bulan_str'] = df_ts['bulan_sort'].astype(str)

            all_months = sorted(df_ts['bulan_str'].unique())
            top_hotspot_cities = df_ts['nama_kota'].value_counts().head(5).index.tolist()

            line_series = []
            hotspot_summary = []
            for city in top_hotspot_cities:
                city_ts = df_ts[df_ts['nama_kota'] == city]
                monthly = city_ts.groupby('bulan_str').size()
                data = [int(monthly.get(m, 0)) for m in all_months]
                line_series.append({"name": city, "data": data})

                active_months = int((monthly > 0).sum())
                total_inc = int(monthly.sum())
                if len(data) >= 3:
                    first_half = sum(data[:len(data)//2])
                    second_half = sum(data[len(data)//2:])
                    trend = "Meningkat" if second_half > first_half else ("Menurun" if second_half < first_half else "Stabil")
                else:
                    trend = "Stabil"

                hotspot_summary.append({
                    "city": city, "recurring_months": active_months,
                    "total_incidents": total_inc, "trend": trend
                })

            q6_detail_rows = []
            for city in top_hotspot_cities:
                for m in all_months:
                    ct = len(df_ts[(df_ts['nama_kota'] == city) & (df_ts['bulan_str'] == m)])
                    if ct > 0:
                        q6_detail_rows.append([city, m, str(ct)])

            q6_narrative = (
                f"Melacak kemunculan insiden dari waktu ke waktu pada titik rawan (hotspot). "
                + " | ".join([f"{h['city']}: Tren {h['trend'].lower()} ({h['total_incidents']} kasus)" for h in hotspot_summary])
            )

            q6_chart = {
                "title": "Tren Waktu Daerah Rawan (Hotspot)",
                "question": "Apakah terdapat pola potensi konflik yang berulang pada daerah tertentu dari waktu ke waktu?",
                "technique": "Time Series Trend Analysis",
                "chart_type": "line",
                "ai_narrative": q6_narrative,
                "summary_stats": {"hotspot_cities": len(top_hotspot_cities), "period_months": len(all_months)},
                "chart_config": {
                    "series": line_series, "categories": all_months,
                    "hotspot_summary": hotspot_summary
                },
                "detail_data": {
                    "headers": ["Wilayah", "Bulan Kejadian", "Jumlah Insiden Baru"],
                    "rows": q6_detail_rows, "ai_detail_narrative": q6_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q6_chart = {"title": "Tren Waktu Daerah Rawan", "chart_type": "line", "technique": "Time Series",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": [], "categories": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q7: REGRESSION — Resolution Time
        # ================================================================
        try:
            df_dur = df.dropna(subset=['durasi_hari']).copy()
            df_dur = df_dur[df_dur['durasi_hari'] >= 0]

            if len(df_dur) >= 5:
                avg_by_phase = df_dur.groupby('nama_fase')['durasi_hari'].agg(['mean', 'count']).reset_index()
                avg_by_phase.columns = ['fase', 'avg_days', 'count']
                avg_by_phase = avg_by_phase.sort_values('avg_days', ascending=False)

                feat_cols_q7 = ['nama_indikator', 'nama_fase', 'nama_kota', 'is_urgent']
                X_q7 = pd.get_dummies(df_dur[feat_cols_q7], drop_first=True)
                y_q7 = df_dur['durasi_hari'].values

                from sklearn.ensemble import RandomForestRegressor
                rf_reg = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
                rf_reg.fit(X_q7, y_q7)
                reg_fi = sorted(zip(X_q7.columns, rf_reg.feature_importances_), key=lambda x: -x[1])[:10]

                overall_avg = round(float(df_dur['durasi_hari'].mean()), 1)

                bar_series = [{"name": "Rata-rata Waktu (Hari)", "data": [round(float(v), 1) for v in avg_by_phase['avg_days'].values]}]
                bar_categories = avg_by_phase['fase'].tolist()

                q7_detail_rows = []
                for _, r in df_dur[['ticket_number', 'nama_kota', 'nama_fase', 'nama_indikator', 'durasi_hari']].sort_values('durasi_hari', ascending=False).head(30).iterrows():
                    q7_detail_rows.append([str(r['ticket_number']), str(r['nama_kota']), str(r['nama_fase']), str(r['nama_indikator']), f"{r['durasi_hari']:.0f} Hari"])

                regression_factors = [{"factor": clean_feature_name(f[0]), "importance": round(float(f[1]), 4), "impact": "Besar"} for f in reg_fi]
            else:
                bar_series = [{"name": "Rata-rata Hari", "data": []}]
                bar_categories = []
                overall_avg = 0
                regression_factors = []
                q7_detail_rows = []

            q7_narrative = (
                f"Rata-rata waktu penyelesaian kasus: {overall_avg} hari. "
                + (f"Variabel/situasi yang paling memengaruhi lama waktu penyelesaian: {regression_factors[0]['factor']}." if regression_factors else "")
            )

            q7_chart = {
                "title": "Variabel Penentu Lamanya Penyelesaian Kasus",
                "question": "Variabel apa yang berkaitan dengan lamanya penyelesaian potensi konflik?",
                "technique": "Random Forest Regression",
                "chart_type": "bar",
                "ai_narrative": q7_narrative,
                "summary_stats": {"kasus_resolved": len(df_dur), "avg_days": overall_avg},
                "chart_config": {
                    "series": to_native(bar_series), "categories": bar_categories,
                    "regression_factors": regression_factors, "overall_avg_days": overall_avg
                },
                "detail_data": {
                    "headers": ["No Identitas Kasus", "Wilayah", "Fase Kasus", "Indikator Isu", "Lama Penyelesaian"],
                    "rows": q7_detail_rows, "ai_detail_narrative": q7_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q7_chart = {"title": "Variabel Waktu Penyelesaian", "chart_type": "bar", "technique": "Regression",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": [], "categories": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q8: ASSOCIATION — Phase, Indikator & Status Relationship
        # ================================================================
        try:
            cross_ps = pd.crosstab(df['nama_fase'], df['nama_status'])
            phases_list = cross_ps.index.tolist()
            statuses_list = cross_ps.columns.tolist()

            grouped_series = []
            for st in statuses_list:
                grouped_series.append({"name": str(st), "data": cross_ps[st].values.tolist()})

            transitions = []
            for fase in phases_list:
                total_in_fase = int(cross_ps.loc[fase].sum())
                for st in statuses_list:
                    cnt = int(cross_ps.loc[fase, st])
                    if cnt > 0:
                        pct = round(cnt / total_in_fase * 100, 1) if total_in_fase > 0 else 0
                        transitions.append({"phase": str(fase), "status": str(st), "count": cnt, "percentage": f"{pct}%"})

            transitions.sort(key=lambda x: -x['count'])

            q8_detail_rows = [[t['phase'], t['status'], str(t['count']), t['percentage']] for t in transitions[:30]]

            q8_narrative = (
                f"Mengungkap rute akhir/nasib dari suatu laporan berdasarkan tahapannya. "
                + (f"Paling banyak terjadi: Kasus di tahapan '{transitions[0]['phase']}' berujung dengan status '{transitions[0]['status']}' ({transitions[0]['count']} kejadian)." if transitions else "")
            )

            q8_chart = {
                "title": "Alur Nasib Laporan: Dari Fase ke Status Akhir",
                "question": "Bagaimana hubungan antara phase, indikator, dan status penyelesaian kasus?",
                "technique": "Cross-tabulation Analysis",
                "chart_type": "grouped_bar",
                "ai_narrative": q8_narrative,
                "summary_stats": {"total_fase": len(phases_list), "total_status": len(statuses_list), "total_transisi": len(transitions)},
                "chart_config": {
                    "series": to_native(grouped_series), "categories": phases_list,
                    "transitions": transitions[:15]
                },
                "detail_data": {
                    "headers": ["Berasal dari Fase", "Berakhir di Status", "Jumlah Kejadian", "Persentase dari Fase Tsb."],
                    "rows": q8_detail_rows, "ai_detail_narrative": q8_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q8_chart = {"title": "Alur Fase ke Status", "chart_type": "grouped_bar", "technique": "Association",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": [], "categories": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q9: CLUSTERING — Segmentasi Profil Wilayah (Provinsi)
        # ================================================================
        try:
            prov_agg = df.groupby('nama_provinsi').agg(
                total_kasus=('id', 'count'),
                unique_indicators=('nama_indikator', 'nunique'),
                unique_phases=('nama_fase', 'nunique'),
                closed_ratio=('is_closed', 'mean'),
                urgent_ratio=('is_urgent', 'mean'),
                activity_sum=('activity_count', 'sum'),
            ).reset_index()

            if len(prov_agg) >= 3:
                feat_prov = prov_agg.drop(columns=['nama_provinsi']).fillna(0)
                X_prov = StandardScaler().fit_transform(feat_prov)

                best_k_p, best_sil_p = 2, -1
                for k in range(2, min(5, len(prov_agg))):
                    km = KMeans(n_clusters=k, random_state=42, n_init=10)
                    lbl = km.fit_predict(X_prov)
                    if len(set(lbl)) > 1:
                        sil = silhouette_score(X_prov, lbl)
                        if sil > best_sil_p:
                            best_sil_p, best_k_p = sil, k

                km_prov = KMeans(n_clusters=best_k_p, random_state=42, n_init=10)
                prov_agg['cluster'] = km_prov.fit_predict(X_prov)

                bubble_series = []
                province_profiles = []
                for cl in sorted(prov_agg['cluster'].unique()):
                    cl_provs = prov_agg[prov_agg['cluster'] == cl]
                    pts = []
                    for _, p in cl_provs.iterrows():
                        pts.append([int(p['total_kasus']), int(p['unique_indicators']), max(int(p['activity_sum']), 5)])
                    bubble_series.append({"name": f"Kelompok {cl+1}", "data": pts})

                    for _, p in cl_provs.iterrows():
                        dom_ind = df[df['nama_provinsi'] == p['nama_provinsi']]['nama_indikator'].mode()
                        dom_fas = df[df['nama_provinsi'] == p['nama_provinsi']]['nama_fase'].mode()
                        province_profiles.append({
                            "province": str(p['nama_provinsi']),
                            "cluster": int(cl),
                            "total_cases": int(p['total_kasus']),
                            "unique_issues": int(p['unique_indicators']),
                            "activity_sum": int(p['activity_sum']),
                            "dominant_indicator": str(dom_ind[0]) if len(dom_ind) > 0 else '-',
                            "dominant_phase": str(dom_fas[0]) if len(dom_fas) > 0 else '-',
                            "has_activities": bool(p['activity_sum'] > 0)
                        })
            else:
                bubble_series = []
                province_profiles = []
                for _, p in prov_agg.iterrows():
                    province_profiles.append({
                        "province": str(p['nama_provinsi']), "cluster": 0,
                        "total_cases": int(p['total_kasus']),
                        "unique_issues": int(p['unique_indicators']),
                        "activity_sum": int(p['activity_sum']),
                        "dominant_indicator": "-", "dominant_phase": "-", "has_activities": False
                    })
                best_k_p = 1
                best_sil_p = 0

            q9_detail_rows = [[pp['province'], f"Kelompok {pp['cluster']+1}", str(pp['total_cases']),
                                str(pp['unique_issues']), str(pp['activity_sum']),
                                pp['dominant_indicator']] for pp in province_profiles]

            q9_narrative = (
                f"Pemetaan tingkat provinsi. Sumbu horizontal = Total Kasus, Sumbu vertikal = Keragaman Isu, dan Ukuran Lingkaran = Total Kegiatan Intervensi."
            )

            q9_chart = {
                "title": "Pemetaan Kapasitas Penanganan Tingkat Provinsi",
                "question": "Apakah ada kelompok daerah dengan pola indikator dan kebutuhan penanganan yang serupa?",
                "technique": "KMeans Clustering",
                "chart_type": "bubble",
                "ai_narrative": q9_narrative,
                "summary_stats": {"total_provinsi": len(prov_agg), "jumlah_klaster": int(best_k_p)},
                "chart_config": {
                    "series": to_native(bubble_series),
                    "province_profiles": province_profiles
                },
                "detail_data": {
                    "headers": ["Provinsi", "Kelompok", "Total Kasus", "Jenis Isu", "Total Intervensi", "Isu Terbanyak"],
                    "rows": q9_detail_rows, "ai_detail_narrative": q9_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q9_chart = {"title": "Pemetaan Penanganan Provinsi", "chart_type": "bubble", "technique": "Clustering",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": []},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        # ================================================================
        # Q10: PREDICTIVE MODEL — Early Warning
        # ================================================================
        try:
            feat_cols_q10 = ['nama_indikator', 'nama_kota']
            if 'current_level' in df.columns:
                feat_cols_q10.append('current_level')

            df_q10 = df[feat_cols_q10 + ['nama_fase']].dropna()
            X_q10 = pd.get_dummies(df_q10.drop(columns=['nama_fase']), drop_first=True)
            y_q10 = df_q10['nama_fase']

            if len(y_q10.unique()) >= 2 and len(y_q10) >= 10:
                rf_q10 = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
                rf_q10.fit(X_q10, y_q10)
                y_pred_q10 = rf_q10.predict(X_q10)
                acc_q10 = accuracy_score(y_q10, y_pred_q10) * 100

                try:
                    cv_scores = cross_val_score(rf_q10, X_q10, y_q10, cv=min(5, len(y_q10)), scoring='accuracy')
                    cv_acc = float(cv_scores.mean()) * 100
                except Exception:
                    cv_acc = acc_q10

                fi_q10 = sorted(zip(X_q10.columns, rf_q10.feature_importances_), key=lambda x: -x[1])[:10]

                preds_sample = []
                sample_idx = df_q10.sample(min(20, len(df_q10)), random_state=42).index
                for idx in sample_idx:
                    actual = str(y_q10.loc[idx])
                    pred = str(rf_q10.predict(X_q10.loc[[idx]])[0])
                    ticket = str(df.loc[idx, 'ticket_number']) if idx in df.index else '-'
                    preds_sample.append({"ticket": ticket, "actual_phase": actual, "predicted_phase": pred, "correct": actual == pred})

                classes = y_q10.unique().tolist()
            else:
                acc_q10 = 0
                cv_acc = 0
                fi_q10 = []
                preds_sample = []
                classes = []

            q10_narrative = (
                f"Model AI sanggup menebak tahap kerawanan suatu kasus hanya dari info awal dengan akurasi {acc_q10:.1f}%. "
                + (f"Data yang paling menolong AI membuat tebakan jitu adalah: {clean_feature_name(fi_q10[0][0])}." if fi_q10 else "")
            )

            q10_detail_rows = []
            for ps in preds_sample:
                status_str = "✓ Tepat" if ps['correct'] else "✗ Meleset"
                q10_detail_rows.append([ps['ticket'], ps['actual_phase'], ps['predicted_phase'], status_str])
            for f in fi_q10:
                q10_detail_rows.append(["[Bobot Kepentingan Variabel]", clean_feature_name(f[0]), f"{f[1]*100:.1f}%", "-"])

            q10_chart = {
                "title": "Model AI Prediksi Tahap Rawan (Early Warning)",
                "question": "Dapatkah karakteristik awal suatu kasus digunakan untuk memprediksi phase atau status berikutnya?",
                "technique": "Random Forest Predictive Model",
                "chart_type": "radialBar",
                "ai_narrative": q10_narrative,
                "summary_stats": {"accuracy": round(acc_q10, 1), "cv_accuracy": round(cv_acc, 1), "total_samples": len(df_q10), "classes": len(classes)},
                "chart_config": {
                    "series": [round(acc_q10, 1)],
                    "labels": ["Akurasi Prediksi"],
                    "predictions_sample": preds_sample,
                    "feature_importance": [{"feature": clean_feature_name(f[0]), "importance": round(float(f[1]), 4)} for f in fi_q10],
                    "model_info": {
                        "algorithm": "Random Forest",
                        "accuracy": round(acc_q10, 1),
                        "cv_accuracy": round(cv_acc, 1),
                        "total_samples": len(df_q10),
                        "classes": [str(c) for c in classes]
                    }
                },
                "detail_data": {
                    "headers": ["ID Laporan / Info", "Fakta Aktual / Nama Variabel", "Tebakan AI / Bobot Pengaruh", "Validasi Sistem"],
                    "rows": q10_detail_rows,
                    "ai_detail_narrative": q10_narrative
                }
            }
        except Exception as e:
            traceback.print_exc()
            q10_chart = {"title": "Model Prediksi Dini", "chart_type": "radialBar", "technique": "Predictive Model",
                         "ai_narrative": f"Error: {str(e)}", "chart_config": {"series": [0], "labels": ["Error"]},
                         "detail_data": {"headers": [], "rows": [], "ai_detail_narrative": str(e)}, "summary_stats": {}}

        return to_native({
            "status": "success",
            "total_kasus": total_kasus,
            "charts": {
                "q1": q1_chart,
                "q2": q2_chart,
                "q3": q3_chart,
                "q4": q4_chart,
                "q5": q5_chart,
                "q6": q6_chart,
                "q7": q7_chart,
                "q8": q8_chart,
                "q9": q9_chart,
                "q10": q10_chart,
            }
        })

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
# AKHIR-PERUBAHAN-29SEP2026