import streamlit as st
import pandas as pd
import numpy as np
import requests

# === Konfigurasi Aplikasi ===
st.set_page_config(page_title="Rekomendasi Apotek", layout="wide")
st.title("🏥 Sistem Pendukung Keputusan Pemilihan Apotek")
st.write("Metode yang digunakan: **TOPSIS** berbasis **sentimen aspek dan jarak dari Google Maps**.")

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

# === Sidebar: Pilihan Kepentingan Pengguna ===
st.sidebar.title("⚖️ Pilih Kepentingan Anda")

preset = st.sidebar.selectbox("Pilih prioritas rekomendasi:", [
    "⚖️ Seimbang",
    "🎯 Prioritaskan Pelayanan",
    "💸 Prioritaskan Harga",
    "🧭 Prioritaskan Jarak",
    "🛠️ Tentukan Sendiri"
])

# Atur bobot berdasarkan preset
if preset == "⚖️ Seimbang":
    bobot_pelayanan, bobot_harga, bobot_jarak = 33, 33, 34
elif preset == "🎯 Prioritaskan Pelayanan":
    bobot_pelayanan, bobot_harga, bobot_jarak = 60, 20, 20
elif preset == "💸 Prioritaskan Harga":
    bobot_pelayanan, bobot_harga, bobot_jarak = 20, 60, 20
elif preset == "🧭 Prioritaskan Jarak":
    bobot_pelayanan, bobot_harga, bobot_jarak = 20, 20, 60
elif preset == "🛠️ Tentukan Sendiri":
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        bobot_pelayanan = st.slider("Pelayanan (%)", 0, 100, 45, key="pelayanan")
    with col2:
        max_harga = 100 - bobot_pelayanan
        bobot_harga = st.slider("Harga (%)", 0, max_harga, 25, key="harga")
    with col3:
        bobot_jarak = 100 - bobot_pelayanan - bobot_harga
        st.markdown(f"**Jarak:** {bobot_jarak}%")
    if bobot_jarak < 0:
        st.sidebar.error("Total bobot tidak boleh melebihi 100%.")

# === Input Lokasi dan Mode ===
alamat = st.text_input("📍 Masukkan alamat Anda:", placeholder="Contoh: Universitas Palangka Raya")
mode = st.selectbox("Pilih moda transportasi", ["driving", "two-wheeler", "walking"])
submit = st.button("🔍 Cari dan Hitung Rekomendasi")

# === Fungsi hitung jarak ===
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

# === Eksekusi Jika Submit ===
if submit and alamat:
    with st.spinner("🔎 Mendeteksi lokasi..."):
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": alamat, "key": api_key}
        geo_res = requests.get(geocode_url, params=params).json()

        if geo_res["status"] == "OK":
            location = geo_res["results"][0]["geometry"]["location"]
            origin = f"{location['lat']},{location['lng']}"
            st.success(f"✅ Lokasi ditemukan: {origin} (mode: {mode})")

            # Hitung jarak ke semua apotek
            with st.spinner("📏 Menghitung jarak ke semua apotek..."):
                results = [get_distance_duration(origin, apotek, mode=mode, api_key=api_key) for apotek in apotek_list]
                df_jarak = pd.DataFrame(results)

            # Load dan olah data sentimen
            df_sentimen = pd.read_csv("data_skor_sentimen_per_aspek_apotek.csv")
            df_pivot = df_sentimen.pivot_table(index='apotek', columns='Dominant_Aspect',
                                               values='skor_sentimen_positif', aggfunc='first').reset_index()
            df_pivot = df_pivot.rename(columns={"apotek": "destination"})

            # Gabungkan jarak dan sentimen
            df_all = pd.merge(df_jarak, df_pivot, on="destination", how="left")
            df_all = df_all.dropna(subset=["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"])

            if df_all.empty:
                st.warning("⚠️ Tidak ada apotek dengan data lengkap untuk dihitung.")
            else:
                # === Perhitungan TOPSIS ===
                X = df_all[["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"]].to_numpy().astype(float)

                # Min-Max Normalisasi
                X_min = X.min(axis=0)
                X_max = X.max(axis=0)
                X_norm = (X - X_min) / (X_max - X_min)

                # Bobot
                weights = np.array([
                    bobot_pelayanan / 100,
                    bobot_harga / 100,
                    bobot_jarak / 100
                ])

                # Matriks terbobot
                X_weighted = X_norm * weights

                # Solusi ideal positif & negatif
                ideal_pos = [np.max(X_weighted[:, 0]), np.max(X_weighted[:, 1]), np.min(X_weighted[:, 2])]
                ideal_neg = [np.min(X_weighted[:, 0]), np.min(X_weighted[:, 1]), np.max(X_weighted[:, 2])]

                # Jarak ke solusi
                D_pos = np.linalg.norm(X_weighted - ideal_pos, axis=1)
                D_neg = np.linalg.norm(X_weighted - ideal_neg, axis=1)

                preference = D_neg / (D_pos + D_neg)

                # Tambahkan hasil ke DataFrame
                df_all["topsis_score"] = preference
                df_all["rank"] = df_all["topsis_score"].rank(ascending=False).astype(int)

                # === Tampilkan hasil ===
                st.markdown(f"""
                ### 📊 Rekomendasi Apotek Terbaik  
                **Bobot digunakan → Pelayanan: {bobot_pelayanan}%, Harga: {bobot_harga}%, Jarak: {bobot_jarak}%**
                """)

                st.dataframe(df_all.sort_values("topsis_score", ascending=False)[[
                    "rank", "destination", "Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga",
                    "distance_text", "topsis_score"
                ]].reset_index(drop=True), use_container_width=True)

        else:
            st.error(f"❌ Lokasi tidak ditemukan: {geo_res['status']}")
