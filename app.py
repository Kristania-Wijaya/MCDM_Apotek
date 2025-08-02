import streamlit as st
import pandas as pd
import numpy as np
import requests

# === Konfigurasi Aplikasi ===
st.set_page_config(page_title="Rekomendasi Apotek", layout="wide")
st.title("🏥 Multi Criteria Decision Making (MCDM) Pemilihan Apotek Kota Palangka Raya")

# === Daftar Apotek ===
apotek_list = [
    "Apotek Alkes Galaksi", "Apotek Alkes Kahayan Farma", "Apotek Alkes Karet",
    "Apotek Alkes Rajawali", "Apotek Alkes Sethadji", "Apotek Alkes Sisingamangaraja",
    "Apotek Alkes Barokah", "Apotek Daoni", "Apotek K-24 Rajawali Sejahtera", "Apotek Kahanjak Medika",
    "Apotek Kimia Farma Diponegoro Palangka Raya", "Apotek New Life", "Apotek Perintis Alkestama",
    "Apotek Pontianak Palangka Raya", "Apotek Segar Palangka Raya"
]

# === Fungsi Hitung Jarak Google Maps ===
def hitung_jarak_dengan_google_maps_api(origin, destination, api_key, mode='driving'):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&mode={mode}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    try:
        distance = data['rows'][0]['elements'][0]['distance']['value'] / 1000  # km
        distance_text = data['rows'][0]['elements'][0]['distance']['text']
        return distance, distance_text
    except:
        return np.nan, "Gagal menghitung"

# === Input Pengguna ===
st.sidebar.header("📍 Lokasi Pengguna & Transportasi")
alamat_user = st.sidebar.text_input("Masukkan Alamat Anda", "Universitas Palangka Raya")
transportasi = st.sidebar.selectbox("Pilih Moda Transportasi", ['driving', 'walking', 'bicycling'])

# === Load Data Apotek & Skor Aspek ===
df = pd.read_csv("data_skor_sentimen_per_aspek_apotek.csv")
api_key = "AIzaSyBqMqXOO-8ZrsSPMQXMeUVYmG-zDHnKeL0"  # Ganti dengan API Key milikmu

# === Hitung Jarak Apotek dari Lokasi User ===
with st.spinner("Menghitung jarak ke apotek..."):
    jarak_list = []
    jarak_text_list = []
    for _, row in df.iterrows():
        destination = f"{row['lat']},{row['lng']}"
        jarak, jarak_text = hitung_jarak_dengan_google_maps_api(alamat_user, destination, api_key, transportasi)
        jarak_list.append(jarak)
        jarak_text_list.append(jarak_text)

df["Jarak (km)"] = jarak_list
df["distance_text"] = jarak_text_list
df = df.dropna(subset=["Jarak (km)"])

# === Normalisasi dan Pembobotan (TOPSIS) ===
st.sidebar.header("⚖️ Bobot Kriteria")
bobot_pelayanan = st.sidebar.slider("Bobot Pelayanan & Fasilitas", 0.0, 1.0, 0.45)
bobot_ketersediaan = st.sidebar.slider("Bobot Ketersediaan Obat & Harga", 0.0, 1.0, 0.25)
bobot_jarak = st.sidebar.slider("Bobot Jarak", 0.0, 1.0, 0.30)

# Validasi total bobot = 1.0
total_bobot = bobot_pelayanan + bobot_ketersediaan + bobot_jarak
if total_bobot != 1.0:
    st.sidebar.warning("Total bobot harus 1.0! Harap sesuaikan.")
    st.stop()

# Matriks Kriteria
X = df[["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "Jarak (km)"]].values.astype(float)

# Normalisasi
R = X / np.sqrt((X**2).sum(axis=0))

# Bobot
W = np.array([bobot_pelayanan, bobot_ketersediaan, bobot_jarak])
V = R * W

# Solusi Ideal Positif dan Negatif
ideal_pos = [np.max(V[:, 0]), np.max(V[:, 1]), np.min(V[:, 2])]
ideal_neg = [np.min(V[:, 0]), np.min(V[:, 1]), np.max(V[:, 2])]

# Hitung Jarak ke Solusi Ideal
D_plus = np.sqrt(((V - ideal_pos)**2).sum(axis=1))
D_minus = np.sqrt(((V - ideal_neg)**2).sum(axis=1))

# Hitung Nilai Preferensi (Skor TOPSIS)
topsis_score = D_minus / (D_plus + D_minus)
df["Topsis_score"] = topsis_score
df["rank"] = df["Topsis_score"].rank(ascending=False, method="min").astype(int)

# === Tampilkan Hasil ===
st.subheader("🏅 Rekomendasi Apotek Terbaik Berdasarkan TOPSIS")
df_tampil = df[[
    "destination", "Pelayanan dan Fasilitas", "Insight Pelayanan",
    "Ketersediaan Obat dan Harga", "Insight Ketersediaan",
    "distance_text", "Topsis_score", "rank"
]].sort_values(by="rank")

st.dataframe(df_tampil, use_container_width=True)

# === Filter Berdasarkan Aspek Mutu ===
st.subheader("🎯 Filter Berdasarkan Aspek Mutu")

opsi_filter = st.selectbox(
    "Pilih kategori yang ingin difokuskan:",
    ["Semua", "Pelayanan", "Ketersediaan"],
    index=0
)

# Buat salinan data awal
filtered_df = df_tampil.copy()

if opsi_filter == "Semua":
    filtered_df = filtered_df[
        (filtered_df["Insight Pelayanan"] == "Pelayanan sangat baik") &
        (filtered_df["Insight Ketersediaan"] == "Obat sangat lengkap harga terjangkau")
    ]
elif opsi_filter == "Pelayanan":
    filtered_df = filtered_df[
        filtered_df["Insight Pelayanan"].isin([
            "Pelayanan sangat baik", "Pelayanan baik", "Pelayanan perlu ditingkatkan"
        ])
    ]
elif opsi_filter == "Ketersediaan":
    filtered_df = filtered_df[
        filtered_df["Insight Ketersediaan"].isin([
            "Obat sangat lengkap harga terjangkau",
            "Obat cukup lengkap harga cukup terjangkau",
            "Ketersediaan atau harga perlu ditingkatkan"
        ])
    ]

# Tampilkan hasil filter
st.markdown(f"**Menampilkan {len(filtered_df)} apotek berdasarkan filter: `{opsi_filter}`**")
st.dataframe(filtered_df, use_container_width=True)
