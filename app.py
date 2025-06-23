import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- CONFIG
st.set_page_config(page_title="Sistem Rekomendasi Apotek", layout="centered")

# --- JUDUL UTAMA
st.title("🏥 Multi Criteria Decision Making (MCDM) Pemilihan Apotek Kota Palangka Raya")
st.markdown("Aplikasi ini menggunakan metode TOPSIS untuk memilih apotek berdasarkan sentimen dan jarak")

# --- SIDEBAR INPUT
with st.sidebar:
    st.header("📌 Input Lokasi & Preferensi")
    alamat = st.text_input("Masukkan Alamat Anda:", placeholder="Contoh: Universitas Palangka Raya")
    mode = st.selectbox("Pilih Moda Transportasi:", ["driving", "walking", "two_wheeler"])
    cari = st.button("📍 Proses Rekomendasi")

# --- API KEY & Data Apotek
API_KEY = "ISI_API_KEY_MU_DISINI"
apotek_list = [
    "Apotek Alkes Galaksi", "Apotek Alkes Kahayan Farma", "Apotek Alkes Karet",
    "Apotek Alkes Rajawali", "Apotek Alkes Sethadji", "Apotek Alkes Sisingamangaraja",
    "Apotek Alkes Barokah", "Apotek Daoni", "Apotek K-24 Rajawali Sejahtera", "Apotek Kahanjak Medika",
    "Apotek Kimia Farma Diponegoro", "Apotek New Life", "Apotek Perintis Alkestama",
    "Apotek Pontianak", "Apotek Segar"
]

# --- FUNGSI AMBIL KOORDINAT
def geocode_alamat(alamat):
    endpoint = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": alamat, "key": API_KEY}
    response = requests.get(endpoint, params=params).json()
    if response["status"] == "OK":
        loc = response["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    else:
        return None, None

# --- FUNGSI HITUNG JARAK
def get_distance_duration(origin, destination, mode="driving", api_key=""):
    endpoint = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {"origins": origin, "destinations": destination, "mode": mode, "key": api_key}
    response = requests.get(endpoint, params=params).json()

    if response["status"] != "OK" or response["rows"][0]["elements"][0]["status"] != "OK":
        return {"destination": destination, "distance_text": None, "distance_meters": np.nan}

    elemen = response["rows"][0]["elements"][0]
    return {
        "destination": destination,
        "distance_text": elemen["distance"]["text"],
        "distance_meters": elemen["distance"]["value"]
    }

# --- PROSES REKOMENDASI
if cari:
    if not alamat:
        st.warning("❗ Masukkan alamat terlebih dahulu.")
    else:
        st.info("🔄 Memproses lokasi dan jarak...")
        lat, lon = geocode_alamat(alamat)
        origin = f"{lat},{lon}"
        hasil_jarak = [get_distance_duration(origin, a, mode=mode, api_key=API_KEY) for a in apotek_list]
        df_jarak = pd.DataFrame(hasil_jarak)

        df_sentimen = pd.read_csv("data_skor_sentimen_per_aspek_apotek.csv")
        df_pivot = df_sentimen.pivot_table(index='apotek', columns='Dominant_Aspect',
                                           values='skor_sentimen_positif', aggfunc='first').reset_index()
        df_pivot = df_pivot.rename(columns={"apotek": "destination"})

        df = pd.merge(df_jarak, df_pivot, on="destination", how="left")
        df = df.dropna(subset=["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"])

        # --- TOPSIS
        X = df[["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"]].to_numpy()
        norm = np.linalg.norm(X, axis=0)
        X_norm = X / norm
        weights = np.array([0.45, 0.25, 0.30])
        X_weighted = X_norm * weights
        ideal_pos = [np.max(X_weighted[:, 0]), np.max(X_weighted[:, 1]), np.min(X_weighted[:, 2])]
        ideal_neg = [np.min(X_weighted[:, 0]), np.min(X_weighted[:, 1]), np.max(X_weighted[:, 2])]
        D_pos = np.linalg.norm(X_weighted - ideal_pos, axis=1)
        D_neg = np.linalg.norm(X_weighted - ideal_neg, axis=1)
        preference = D_neg / (D_pos + D_neg)

        df["topsis_score"] = preference
        df["rank"] = df["topsis_score"].rank(ascending=False).astype(int)

        # --- HASIL AKHIR
        st.success("✅ Rekomendasi Apotek:")
        st.dataframe(df.sort_values("topsis_score", ascending=False)[[
            "destination", "Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga",
            "distance_text", "topsis_score", "rank"
        ]])

        # --- VISUALISASI
        st.subheader("📊 Visualisasi Skor TOPSIS")
        fig, ax = plt.subplots()
        df_plot = df.sort_values("topsis_score", ascending=True)
        ax.barh(df_plot["destination"], df_plot["topsis_score"], color="skyblue")
        ax.set_xlabel("Skor TOPSIS")
        st.pyplot(fig)
