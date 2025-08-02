import streamlit as st
import pandas as pd
import numpy as np

# === Konfigurasi Aplikasi ===
st.set_page_config(page_title="Rekomendasi Apotek", layout="wide")
st.title("🏥 Multi Criteria Decision Making (MCDM) Pemilihan Apotek Kota Palangka Raya")

# === Upload Dataset ===
uploaded = st.file_uploader("Unggah file hasil skor aspek dan jarak (CSV)", type="csv")
if uploaded is not None:
    df = pd.read_csv(uploaded)

    # Input bobot kriteria
    st.sidebar.header("⚖️ Bobot Kriteria")
    bobot_pelayanan = st.sidebar.slider("Pelayanan dan Fasilitas", 0.0, 1.0, 0.45)
    bobot_ketersediaan = st.sidebar.slider("Ketersediaan Obat dan Harga", 0.0, 1.0, 0.25)
    bobot_jarak = st.sidebar.slider("Jarak", 0.0, 1.0, 0.30)

    total_bobot = bobot_pelayanan + bobot_ketersediaan + bobot_jarak
    if total_bobot != 1.0:
        st.sidebar.warning("Total bobot harus 1.0")

    tombol_hitung = st.button("🔍 Cari dan Hitung Rekomendasi")

    if tombol_hitung and total_bobot == 1.0:
        # Simpan bobot dalam list
        weights = [bobot_pelayanan, bobot_ketersediaan, bobot_jarak]

        # Ambil kolom untuk TOPSIS
        kriteria = ['Pelayanan dan Fasilitas', 'Ketersediaan Obat dan Harga', 'distance_value']
        df_kriteria = df[kriteria].copy()

        # Normalisasi matriks keputusan
        normal_matrix = df_kriteria / np.sqrt((df_kriteria**2).sum())
        weighted_matrix = normal_matrix * weights

        # Solusi ideal positif dan negatif
        ideal_pos = weighted_matrix.max()
        ideal_neg = weighted_matrix.min()

        # Hitung jarak ke solusi ideal positif dan negatif
        d_pos = np.sqrt(((weighted_matrix - ideal_pos) ** 2).sum(axis=1))
        d_neg = np.sqrt(((weighted_matrix - ideal_neg) ** 2).sum(axis=1))

        # Hitung nilai preferensi (closeness coefficient)
        cc = d_neg / (d_pos + d_neg)

        # Masukkan ke dataframe hasil
        df_topsis = df.copy()
        df_topsis['Topsis_score'] = cc
        df_topsis['rank'] = df_topsis['Topsis_score'].rank(ascending=False, method='min').astype(int)
        df_topsis = df_topsis.sort_values(by='Topsis_score', ascending=False)

        # Tampilkan hasil akhir (hanya kolom penting)
        df_tampil = df_topsis[[
            'destination',
            'Pelayanan dan Fasilitas', 'Insight Pelayanan',
            'Ketersediaan Obat dan Harga', 'Insight Ketersediaan',
            'distance_text',
            'Topsis_score', 'rank'
        ]].reset_index(drop=True)

        st.subheader("🏆 Rekomendasi Apotek Terbaik")
        st.dataframe(df_tampil, use_container_width=True)

        # Simpan ke session_state agar tetap tampil saat filter diganti
        st.session_state['df_tampil'] = df_tampil

# === Filter Berdasarkan Insight ===
if 'df_tampil' in st.session_state:
    df_tampil = st.session_state['df_tampil']

    st.markdown("### 🔍 Filter Hasil Rekomendasi Berdasarkan Aspek")
    filter_option = st.selectbox(
        "Pilih Filter:",
        ["Semua", "Pelayanan", "Ketersediaan"],
        key="filter_dropdown"
    )

    # Terapkan filter sesuai pilihan
    if filter_option == "Semua":
        df_filtered = df_tampil[
            (df_tampil["Insight Pelayanan"] == "Pelayanan sangat baik") &
            (df_tampil["Insight Ketersediaan"] == "Obat sangat lengkap harga terjangkau")
        ]
    elif filter_option == "Pelayanan":
        df_filtered = df_tampil[
            df_tampil["Insight Pelayanan"].isin([
                "Pelayanan sangat baik",
                "Pelayanan baik",
                "Pelayanan perlu ditingkatkan"
            ])
        ]
    elif filter_option == "Ketersediaan":
        df_filtered = df_tampil[
            df_tampil["Insight Ketersediaan"].isin([
                "Obat sangat lengkap harga terjangkau",
                "Obat cukup lengkap harga cukup terjangkau",
                "Ketersediaan atau harga perlu ditingkatkan"
            ])
        ]

    st.markdown("### 📋 Hasil Filter")
    st.dataframe(df_filtered, use_container_width=True)
