import streamlit as st
import pandas as pd
import numpy as np
import requests

# === Konfigurasi Aplikasi ===
st.set_page_config(page_title="Rekomendasi Apotek", layout="wide")
st.title("🏥 MULTI CRITERIA DECISION MAKING (MCDM) PEMILIHAN APOTEK KOTA PALANGKA RAYA")
st.write("Metode: **TOPSIS** berbasis **sentimen aspek** dan **jarak Google Maps**")

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
st.sidebar.title("⚖️ Tentukan Bobot Kriteria (Total = 100%)")

bobot_pelayanan = st.sidebar.number_input("Pelayanan (%)", 0, 100, step=1, value=33)
bobot_harga = st.sidebar.number_input("Harga (%)", 0, 100, step=1, value=33)
bobot_jarak = st.sidebar.number_input("Jarak (%)", 0, 100, step=1, value=34)

total_bobot = bobot_pelayanan + bobot_harga + bobot_jarak

if total_bobot != 100:
    st.sidebar.error(f"❌ Total bobot: {total_bobot}%. Harus pas 100%.")
    submit = False
else:
    st.sidebar.success("✅ Total bobot valid: 100%")
    submit = st.sidebar.button("🔍 Jalankan Rekomendasi")

# === Input Lokasi ===
alamat = st.text_input("📍 Masukkan alamat Anda:", placeholder="Contoh: Universitas Palangka Raya")
mode = st.selectbox("Pilih moda transportasi", ["driving", "two-wheeler", "walking"])


# === Fungsi Hitung Jarak Google Maps ===
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

# === Proses ===
if submit and alamat:
    with st.spinner("🔎 Mendeteksi lokasi..."):
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geo_res = requests.get(geocode_url, params={"address": alamat, "key": api_key}).json()

    if geo_res["status"] == "OK":
        location = geo_res["results"][0]["geometry"]["location"]
        origin = f"{location['lat']},{location['lng']}"
        st.success(f"✅ Lokasi ditemukan: {origin} (mode: {mode})")

        with st.spinner("📏 Menghitung jarak ke apotek..."):
            results = [get_distance_duration(origin, apotek, mode=mode, api_key=api_key) for apotek in apotek_list]
            df_jarak = pd.DataFrame(results)

        # === Load Data Sentimen ===
        df_sentimen = pd.read_csv("data_skor_sentimen_per_aspek_apotek.csv")
        df_pivot = df_sentimen.pivot_table(index='apotek', columns='Dominant_Aspect',
                                           values='skor_sentimen_positif', aggfunc='first').reset_index()
        df_pivot = df_pivot.rename(columns={"apotek": "destination"})

        # === Gabungkan Data ===
        df_all = pd.merge(df_jarak, df_pivot, on="destination", how="left")
        df_all = df_all.dropna(subset=["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"])

        if df_all.empty:
            st.warning("⚠️ Tidak ada apotek dengan data lengkap.")
        else:
            # === TOPSIS ===
            X = df_all[["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"]].to_numpy().astype(float)
            X_min = X.min(axis=0)
            X_max = X.max(axis=0)
            X_norm = (X - X_min) / (X_max - X_min)

            weights = np.array([
                bobot_pelayanan / 100,
                bobot_harga / 100,
                bobot_jarak / 100
            ])
            X_weighted = X_norm * weights

            ideal_pos = [np.max(X_weighted[:, 0]), np.max(X_weighted[:, 1]), np.min(X_weighted[:, 2])]
            ideal_neg = [np.min(X_weighted[:, 0]), np.min(X_weighted[:, 1]), np.max(X_weighted[:, 2])]

            D_pos = np.linalg.norm(X_weighted - ideal_pos, axis=1)
            D_neg = np.linalg.norm(X_weighted - ideal_neg, axis=1)
            preference = D_neg / (D_pos + D_neg)

            df_all["topsis_score"] = preference
            df_all["rank"] = df_all["topsis_score"].rank(ascending=False).astype(int)

            # === Tampilkan Hasil ===
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
