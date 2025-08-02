import streamlit as st
import pandas as pd
import numpy as np

# === Konfigurasi Aplikasi ===
st.set_page_config(page_title="Rekomendasi Apotek", layout="wide")
st.title("🏥 Multi Criteria Decision Making (MCDM) Pemilihan Apotek Kota Palangka Raya")

# === Upload Dataset ===
uploaded = st.file_uploader("Unggah file hasil skor aspek dan jarak (CSV)", type="csv")

# === Simpan file ke session_state ===
if uploaded is not None:
    st.session_state.uploaded = uploaded
if 'uploaded' in st.session_state:
    df = pd.read_csv(st.session_state.uploaded)

    # === Input Bobot dan Simpan ke session_state ===
    st.sidebar.header("⚖️ Bobot Kriteria")
    bobot_pelayanan = st.sidebar.slider("Pelayanan dan Fasilitas", 0.0, 1.0, 0.45)
    bobot_ketersediaan = st.sidebar.slider("Ketersediaan Obat dan Harga", 0.0, 1.0, 0.25)
    bobot_jarak = st.sidebar.slider("Jarak", 0.0, 1.0, 0.30)

    total_bobot = bobot_pelayanan + bobot_ketersediaan + bobot_jarak
    if total_bobot != 1.0:
        st.sidebar.warning("Total bobot harus 1.0")

    tombol_hitung = st.button("🔍 Cari dan Hitung Rekomendasi")

    if tombol_hitung and total_bobot == 1.0:
        weights = [bobot_pelayanan, bobot_ketersediaan, bobot_jarak]
        kriteria = ['Pelayanan dan Fasilitas', 'Ketersediaan Obat dan Harga', 'distance_value']
        df_kriteria = df[kriteria].copy()

        normal_matrix = df_kriteria / np.sqrt((df_kriteria**2).sum())
        weighted_matrix = normal_matrix * weights

        ideal_pos = weighted_matrix.max()
        ideal_neg = weighted_matrix.min()

        d_pos = np.sqrt(((weighted_matrix - ideal_pos) ** 2).sum(axis=1))
        d_neg = np.sqrt(((weighted_matrix - ideal_neg) ** 2).sum(axis=1))

        cc = d_neg / (d_pos + d_neg)

        df_topsis = df.copy()
        df_topsis['Topsis_score'] = cc
        df_topsis['rank'] = df_topsis['Topsis_score'].rank(ascending=False, method='min').astype(int)
        df_topsis = df_topsis.sort_values(by='Topsis_score', ascending=False)

        df_tampil = df_topsis[[
            'destination',
            'Pelayanan dan Fasilitas', 'Insight Pelayanan',
            'Ketersediaan Obat dan Harga', 'Insight Ketersediaan',
            'distance_text',
            'Topsis_score', 'rank'
        ]].reset_index(drop=True)

        # Simpan ke session_state
        st.session_state.df_tampil = df_tampil

# === Tampilkan Hasil & Filter ===
if 'df_tampil' in st.session_state:
    df_tampil = st.session_state.df_tampil

    st.subheader("🏆 Rekomendasi Apotek Terbaik")
    st.dataframe(df_tampil, use_container_width=True)

    # === Filter Berdasarkan Insight ===
    st.markdown("### 🔍 Filter Hasil Rekomendasi Berdasarkan Aspek")
    filter_option = st.selectbox(
        "Pilih Filter:",
        ["Semua", "Pelayanan", "Ketersediaan"],
        key="filter_dropdown"
    )

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
