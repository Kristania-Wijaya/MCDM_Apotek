import streamlit as st
import pandas as pd
import numpy as np
import requests

# === Konfigurasi Aplikasi ===
st.set_page_config(page_title="Rekomendasi Apotek", layout="wide")
st.title("🏥 Multi Criteria Decision Making (MCDM) Pemilihan Apotek Kota Palangka Raya")

# === Fungsi TOPSIS ===
def topsis(df, weights, benefit_criteria):
    X = df.values
    norm_X = X / np.sqrt((X**2).sum(axis=0))
    weighted_X = norm_X * weights
    ideal_best = np.max(weighted_X, axis=0) if benefit_criteria else np.min(weighted_X, axis=0)
    ideal_worst = np.min(weighted_X, axis=0) if benefit_criteria else np.max(weighted_X, axis=0)
    d_positive = np.sqrt(((weighted_X - ideal_best)**2).sum(axis=1))
    d_negative = np.sqrt(((weighted_X - ideal_worst)**2).sum(axis=1))
    scores = d_negative / (d_positive + d_negative)
    return scores

# === Input Data Sentimen dan Jarak ===
df_all = pd.read_csv("skor_sentimen_per_aspek_apotek.csv")
df_all["distance_km"] = df_all["distance_text"].str.replace(" km", "").str.replace(",", ".").astype(float)

# === Sidebar Input ===
st.sidebar.header("🔍 Filter Pencarian Apotek")

api_key = st.secrets["api_key"] if "api_key" in st.secrets else st.sidebar.text_input("🔑 Masukkan Google Maps API Key")

alamat = st.sidebar.text_input("📍 Masukkan Lokasi Anda")
mode = st.sidebar.selectbox("🚗 Pilih Moda Transportasi", ["driving", "walking", "bicycling", "transit"])
aspek_filter = st.sidebar.multiselect("🎯 Pilih Aspek Prioritas", ["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga"], default=["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga"])
submit = st.sidebar.button("🔎 Cari dan Hitung Rekomendasi")

# === Fungsi Menampilkan Hasil Berdasarkan Filter Aspek ===
def tampilkan_rekomendasi(df_tampil, judul):
    st.subheader(judul)
    st.dataframe(df_tampil[["nama_apotek", "alamat", "pelayanan_fasilitas", "ketersediaan_harga", "distance_km", "peringkat"]])

# === Jika Submit Ditekan ===
if submit and alamat:
    with st.spinner("🔎 Mendeteksi lokasi..."):
        geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": alamat, "key": api_key}
        geo_res = requests.get(geo_url, params=params).json()

        if geo_res["status"] == "OK":
            location = geo_res["results"][0]["geometry"]["location"]
            origin = f"{location['lat']},{location['lng']}"
            st.success(f"✅ Lokasi ditemukan: {origin} (mode: {mode})")

            # Hitung TOPSIS jika semua aspek dipilih
            if set(aspek_filter) == {"Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga"}:
                st.markdown("### 🔢 Hasil Rekomendasi Apotek Menyeluruh (TOPSIS)")
                df_topsis = df_all.copy()
                data_topsis = df_topsis[["pelayanan_fasilitas", "ketersediaan_harga", "distance_km"]]
                weights = np.array([0.45, 0.25, 0.30])  # bobot default
                benefit_criteria = [True, True, False]
                df_topsis["peringkat"] = topsis(data_topsis, weights, benefit_criteria)
                df_topsis = df_topsis.sort_values(by="peringkat", ascending=False)
                tampilkan_rekomendasi(df_topsis, "🏥 Rekomendasi Apotek Terbaik Secara Menyeluruh")

            # Jika hanya Pelayanan dipilih
            elif aspek_filter == ["Pelayanan dan Fasilitas"]:
                st.markdown("### 🧑‍⚕️ Rekomendasi Berdasarkan Pelayanan dan Fasilitas Terbaik")
                df_pelayanan = df_all.sort_values(by="pelayanan_fasilitas", ascending=False)
                df_pelayanan["peringkat"] = df_pelayanan["pelayanan_fasilitas"]
                tampilkan_rekomendasi(df_pelayanan, "Apotek dengan Pelayanan dan Fasilitas Terbaik")

            # Jika hanya Ketersediaan dipilih
            elif aspek_filter == ["Ketersediaan Obat dan Harga"]:
                st.markdown("### 💊 Rekomendasi Berdasarkan Ketersediaan Obat dan Harga")
                df_ketersediaan = df_all.sort_values(by="ketersediaan_harga", ascending=False)
                df_ketersediaan["peringkat"] = df_ketersediaan["ketersediaan_harga"]
                tampilkan_rekomendasi(df_ketersediaan, "Apotek dengan Ketersediaan Obat Terlengkap")

            # Jika tidak memilih apapun
            else:
                st.warning("⚠️ Silakan pilih minimal satu aspek untuk memfilter.")
        else:
            st.error("❌ Lokasi tidak ditemukan. Silakan masukkan alamat yang valid.")
