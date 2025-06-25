import streamlit as st
import pandas as pd
import numpy as np
import requests

# === Konfigurasi Aplikasi ===
st.set_page_config(page_title="Rekomendasi Apotek", layout="wide")
st.title("🏥 Multi Criteria Decission Making (MCDM) Pemilihan Apotek Kota Palangka Raya")
st.write("Metode yang digunakan: TOPSIS berbasis sentimen aspek dan jarak dari Google Maps API.")

# === API Key Google Maps ===
api_key = "AIzaSyBqMqXOO-8ZrsSPMQXMeUVYmG-zDHnKeL0"  # Ganti dengan milikmu

# === Data Apotek ===
apotek_list = [
    "Apotek Alkes Galaksi", "Apotek Alkes Kahayan Farma", "Apotek Alkes Karet",
    "Apotek Alkes Rajawali", "Apotek Alkes Sethadji", "Apotek Alkes Sisingamangaraja",
    "Apotek Alkes Barokah", "Apotek Daoni", "Apotek K-24 Rajawali Sejahtera", "Apotek Kahanjak Medika",
    "Apotek Kimia Farma Diponegoro Palangka Raya", "Apotek New Life", "Apotek Perintis Alkestama",
    "Apotek Pontianak Palangka Raya", "Apotek Segar"
]

# === Sidebar: Bobot Kriteria ===
st.sidebar.title("⚖️ Pengaturan Bobot Kriteria")
bobot_mode = st.sidebar.radio("Pilih metode bobot:", ["Gunakan default", "Tentukan sendiri"])

if bobot_mode == "Gunakan default":
    bobot_pelayanan = 45
    bobot_harga = 25
    bobot_jarak = 30
    total_bobot = 100
    valid_bobot = True
    st.sidebar.markdown(f"""
    **Bobot default:**
    - Pelayanan dan Fasilitas: {bobot_pelayanan}%
    - Ketersediaan Obat dan Harga: {bobot_harga}%
    - Jarak: {bobot_jarak}%
    """)
else:
    bobot_pelayanan = st.sidebar.slider("Pelayanan dan Fasilitas (%)", 0, 100, 33)
    bobot_harga = st.sidebar.slider("Ketersediaan Obat dan Harga (%)", 0, 100, 33)
    bobot_jarak = st.sidebar.slider("Jarak (%)", 0, 100, 34)
    total_bobot = bobot_pelayanan + bobot_harga + bobot_jarak

    if total_bobot != 100:
        st.sidebar.error(f"❌ Total bobot harus 100%, sekarang: {total_bobot}%")
        valid_bobot = False
    else:
        st.sidebar.success("✅ Total bobot valid: 100%")
        valid_bobot = True

# === Input Lokasi ===
alamat = st.text_input("📍 Masukkan alamat Anda:", placeholder="Contoh: Universitas Palangka Raya")
mode = st.selectbox("Pilih moda transportasi", ["driving", "two-wheeler", "walking"])
submit = st.button("🔍 Cari dan Hitung Rekomendasi") if valid_bobot else None

# === Fungsi: Jarak dari Google Maps ===
def get_distance_duration(origin_latlon, destination, mode="driving", api_key=""):
    endpoint = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin_latlon,
        "destinations": destination,
        "mode": mode,
        "key": api_key
    }
    response = requests.get(endpoint, params=params)
    data = response.json()

    if data["status"] != "OK" or data["rows"][0]["elements"][0]["status"] != "OK":
        return {"destination": destination, "distance_text": None, "distance_meters": np.nan}

    element = data["rows"][0]["elements"][0]
    return {
        "destination": destination,
        "distance_text": element["distance"]["text"],
        "distance_meters": element["distance"]["value"]
    }

# === Proses Perhitungan TOPSIS ===
if submit and alamat:
    with st.spinner("🔎 Mendeteksi lokasi..."):
        geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": alamat, "key": api_key}
        geo_res = requests.get(geo_url, params=params).json()

        if geo_res["status"] == "OK":
            location = geo_res["results"][0]["geometry"]["location"]
            origin = f"{location['lat']},{location['lng']}"
            st.success(f"✅ Lokasi ditemukan: {origin} (mode: {mode})")

            # Hitung Jarak
            with st.spinner("📏 Menghitung jarak ke semua apotek..."):
                results = [get_distance_duration(origin, apotek, mode=mode, api_key=api_key) for apotek in apotek_list]
                df_jarak = pd.DataFrame(results)

            # Load Sentimen
            df_sentimen = pd.read_csv("data_skor_sentimen_per_aspek_apotek.csv")

            # Hitung skor total ulasan per apotek
            df_sentimen["total_ulasan"] = df_sentimen["jumlah_positif"] + df_sentimen["jumlah_negatif"]
            df_sentimen["skor_total"] = df_sentimen["jumlah_positif"] / df_sentimen["total_ulasan"]

            # Ambil rata-rata skor total per apotek
            df_skor_total = df_sentimen.groupby("apotek")["skor_total"].mean().reset_index()
            df_skor_total = df_skor_total.rename(columns={"apotek": "destination", "skor_total": "Skor Sentimen Keseluruhan"})

            # Pivot skor aspek
            df_pivot = df_sentimen.pivot_table(index='apotek', columns='Dominant_Aspect',
                                               values='skor_sentimen_positif', aggfunc='first').reset_index()
            df_pivot = df_pivot.rename(columns={"apotek": "destination"})

            # Gabung semua data
            df_all = pd.merge(df_jarak, df_pivot, on="destination", how="left")
            df_all = pd.merge(df_all, df_skor_total, on="destination", how="left")
            df_all = df_all.dropna(subset=["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"])

            if df_all.empty:
                st.warning("⚠️ Tidak ada apotek dengan data lengkap.")
            else:
                # Matriks Keputusan
                X = df_all[["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"]].to_numpy().astype(float)

                # Normalisasi
                X_norm = X / np.sqrt((X**2).sum(axis=0))

                # Bobot
                weights = np.array([
                    bobot_pelayanan / 100,
                    bobot_harga / 100,
                    bobot_jarak / 100
                ])

                # Matriks Terbobot
                X_weighted = X_norm * weights

                # Solusi Ideal
                ideal_pos = [
                    np.max(X_weighted[:, 0]),
                    np.max(X_weighted[:, 1]),
                    np.min(X_weighted[:, 2])
                ]
                ideal_neg = [
                    np.min(X_weighted[:, 0]),
                    np.min(X_weighted[:, 1]),
                    np.max(X_weighted[:, 2])
                ]

                # Jarak ke solusi ideal
                D_pos = np.linalg.norm(X_weighted - ideal_pos, axis=1)
                D_neg = np.linalg.norm(X_weighted - ideal_neg, axis=1)
                preference = D_neg / (D_pos + D_neg)

                # Tambah skor dan ranking
                df_all["topsis_score"] = preference
                df_all["rank"] = df_all["topsis_score"].rank(ascending=False).astype(int)

                # Ubah nama kolom untuk tampilan akhir
                df_display = df_all.rename(columns={
                    "rank": "Rank",
                    "destination": "Destination",
                    "distance_text": "Jarak",
                    "Skor Sentimen Keseluruhan": "Skor Sentimen",
                    "topsis_score": "Nilai Topsis"
                })

                # Tampilkan hasil
                st.subheader("📊 Rekomendasi Apotek Terbaik")
                st.caption(f"Bobot digunakan → Pelayanan: {bobot_pelayanan}%, Harga: {bobot_harga}%, Jarak: {bobot_jarak}%")

                st.dataframe(df_display.sort_values("Nilai Topsis", ascending=False)[[
                    "Rank", "Destination", "Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga",
                    "Jarak", "Skor Sentimen", "Nilai Topsis"
                ]].reset_index(drop=True), use_container_width=True)

        else:
            st.error(f"❌ Lokasi tidak ditemukan: {geo_res['status']}")
