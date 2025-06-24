import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- Judul ---
st.title("🏥 Multi Criteria Decision Making (MCDM) Pemilihan Apotek Kota Palangka Raya")
st.write("Aplikasi ini menggunakan metode TOPSIS untuk memilih apotek berdasarkan sentimen dan jarak.")

# --- API Key dan Mode ---
api_key = "AIzaSyBqMqXOO-8ZrsSPMQXMeUVYmG-zDHnKeL0"  # Ganti dengan key-mu

# --- Input Lokasi Pengguna ---
alamat = st.text_input("📍Masukkan alamat:")

mode = st.selectbox("Pilih moda transportasi", ["driving", "two-wheeler", "walking"])

cari = st.button("Cari dan Hitung Rekomendasi")

if cari and alamat:
    st.write(f"Mencari lokasi: {alamat}")
    
    # --- Geocode lokasi asal ---
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": alamat, "key": api_key}
    geo_res = requests.get(geocode_url, params=params).json()

    if geo_res["status"] == "OK":
        lokasi_asal = geo_res["results"][0]["geometry"]["location"]
        origin = f"{lokasi_asal['lat']},{lokasi_asal['lng']}"
        st.success(f"Lokasi ditemukan: {origin}")

        # --- Data Apotek ---
        apotek_list = [
            "Apotek Alkes Galaksi", "Apotek Alkes Kahayan Farma", "Apotek Alkes Karet",
            "Apotek Alkes Rajawali", "Apotek Alkes Sethadji", "Apotek Alkes Sisingamangaraja",
            "Apotek Alkes Barokah", "Apotek Daoni", "Apotek K-24 Rajawali Sejahtera", "Apotek Kahanjak Medika",
            "Apotek Kimia Farma Diponegoro", "Apotek New Life", "Apotek Perintis Alkestama",
            "Apotek Pontianak", "Apotek Segar"
        ]

        # --- Hitung jarak tiap apotek ---
        distance_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        results = []
        for apotek in apotek_list:
            params = {
                "origins": origin,
                "destinations": apotek,
                "mode": mode,
                "key": api_key
            }
            res = requests.get(distance_url, params=params).json()
            if res["status"] == "OK" and res["rows"][0]["elements"][0]["status"] == "OK":
                ele = res["rows"][0]["elements"][0]
                results.append({
                    "destination": apotek,
                    "distance_text": ele["distance"]["text"],
                    "distance_meters": ele["distance"]["value"]
                })

        df_jarak = pd.DataFrame(results)

        # --- Load data sentimen ---
        df_sentimen = pd.read_csv("data_skor_sentimen_per_aspek_apotek.csv")
        df_pivot = df_sentimen.pivot_table(index='apotek', columns='Dominant_Aspect',
                                           values='skor_sentimen_positif', aggfunc='first').reset_index()
        df_pivot = df_pivot.rename(columns={"apotek": "destination"})

        # --- Gabungkan ---
        df_all = pd.merge(df_jarak, df_pivot, on="destination", how="left")
        df_all = df_all.dropna(subset=["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"])

        # --- TOPSIS ---
        X = df_all[["Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga", "distance_meters"]].to_numpy().astype(float)
        norm = np.linalg.norm(X, axis=0)
        X_norm = X / norm
        weights = np.array([0.45, 0.25, 0.30])  # [Pelayanan, Ketersediaan & Harga, Jarak]
        X_weighted = X_norm * weights
        ideal_pos = [np.max(X_weighted[:, 0]), np.max(X_weighted[:, 1]), np.min(X_weighted[:, 2])]
        ideal_neg = [np.min(X_weighted[:, 0]), np.min(X_weighted[:, 1]), np.max(X_weighted[:, 2])]
        D_pos = np.linalg.norm(X_weighted - ideal_pos, axis=1)
        D_neg = np.linalg.norm(X_weighted - ideal_neg, axis=1)
        preference = D_neg / (D_pos + D_neg)

        df_all["topsis_score"] = preference
        df_all["rank"] = df_all["topsis_score"].rank(ascending=False).astype(int)

        st.subheader("Hasil Rekomendasi Apotek")
        st.dataframe(df_all.sort_values("topsis_score", ascending=False)[[
            "destination", "Pelayanan dan Fasilitas", "Ketersediaan Obat dan Harga",
            "distance_text", "topsis_score", "rank"
        ]])
    else:
        st.error("Alamat tidak ditemukan.")
