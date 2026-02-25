import streamlit as st
import pandas as pd
import numpy as np
import io

# -----------------------------------------------------------------------------
# 1. KONFIGURACE STRÁNKY A CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ultimate Warehouse Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #0f52ba !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        color: #4f4f4f !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 55px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 6px 6px 0px 0px;
        font-weight: 600;
        font-size: 15px;
    }
    hr {
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .stDataFrame {
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOKALIZAČNÍ SLOVNÍK (CZ/EN)
# -----------------------------------------------------------------------------
TEXTS = {
    'CZ': {
        'title': '📦 Ultimate Packing Analytics: Materiály & Obaly',
        'sidebar_title': '⚙️ Parametry Analýzy',
        'lang_select': '🌐 Jazyk',
        'upload_file': '📁 Nahrát zdrojová data (CSV/XLSX)',
        'min_pieces': '🔍 Min. počet kusů (Filtr):',
        'filter_customer': '🏢 Filtrovat Zákazníky:',
        'tab_dash': '📊 Přehled',
        'tab_mat': '🛠️ Materiály a Obaly',
        'tab_delay': '⚠️ Složitost a Zdržení',
        'tab_top': '🏆 TOP Tabulky',
        'tab_audit': '🔎 Audit Výpočtů',
        'tab_export': '💾 Export',
        'metric_orders': 'Zpracováno zakázek',
        'metric_pieces': 'Zabaleno kusů',
        'metric_weight': 'Celková tonáž (kg)',
        'metric_efficiency': 'Efektivita (ks/min)',
        'metric_effort': 'Prům. Effort Time (min)',
        'chart_mat_vol': 'Nejčastější Materiály dle objemu (ks)',
        'chart_pack_corr': 'Korelace: Váha vs. Počet obalů',
        'chart_pack_types': 'Nejpoužívanější specifické typy obalů (Text. hodnoty)',
        'delay_title': 'Vliv dodatečných úkonů na průměrný čas balení (Process Time)',
        'delay_desc': 'Porovnání průměrného času zakázky s daným příznakem vs. bez něj.',
        'audit_desc': 'Automatický audit logiky na 5 náhodných vzorcích.',
        'export_desc': 'Kompletní zpracovaná data s obohacenými výpočty a detailními metrikami obalů.',
        'btn_export': '📥 Stáhnout Detailní Report (.xlsx)',
        'no_data': 'Prosím, nahrajte soubor s daty v levém panelu pro zahájení analýzy.'
    },
    'EN': {
        'title': '📦 Ultimate Packing Analytics: Materials & Packaging',
        'sidebar_title': '⚙️ Parameters',
        'lang_select': '🌐 Language',
        'upload_file': '📁 Upload Source Data',
        'min_pieces': '🔍 Min. Pieces (Filter):',
        'filter_customer': '🏢 Filter Customers:',
        'tab_dash': '📊 Overview',
        'tab_mat': '🛠️ Materials & Packaging',
        'tab_delay': '⚠️ Complexity & Delays',
        'tab_top': '🏆 TOP Tables',
        'tab_audit': '🔎 Logic Audit',
        'tab_export': '💾 Export',
        'metric_orders': 'Processed Orders',
        'metric_pieces': 'Packed Pieces',
        'metric_weight': 'Total Tonnage (kg)',
        'metric_efficiency': 'Efficiency (pcs/min)',
        'metric_effort': 'Avg Effort Time (min)',
        'chart_mat_vol': 'Top Materials by Volume (pcs)',
        'chart_pack_corr': 'Correlation: Weight vs. Packaging Count',
        'chart_pack_types': 'Most used specific packaging types (Text values)',
        'delay_title': 'Impact of extra tasks on average packing time',
        'delay_desc': 'Comparison of average order time with the flag vs. without it.',
        'audit_desc': 'Automated logic audit on random samples.',
        'export_desc': 'Complete processed data with enriched packaging metrics.',
        'btn_export': '📥 Download Detailed Report (.xlsx)',
        'no_data': 'Please upload a data file.'
    }
}

# -----------------------------------------------------------------------------
# 3. SESSION STATE
# -----------------------------------------------------------------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'CZ'
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# -----------------------------------------------------------------------------
# 4. FUNKCE PRO ZPRACOVÁNÍ DAT (VEKTORIZACE & PARSOVÁNÍ)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    
    # Numerické sloupce
    num_cols = [
        'Number of pieces', 'Number of cartons', 'Number of pallets', 
        'Number of KLTs', 'Number of item types', 'Weight (kg)',
        'Full KLTs', 'Empty KLTs'
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Převod časů na minuty (Process Time a Effort Time)
    for t_col, out_col in [('Process Time', 'Process_Minutes'), ('Effort Time', 'Effort_Minutes')]:
        if t_col in df.columns:
            time_strings = df[t_col].astype(str)
            pt_timedelta = pd.to_timedelta(time_strings, errors='coerce')
            df[out_col] = pt_timedelta.dt.total_seconds() / 60.0
            df[out_col] = df[out_col].fillna(0)
        else:
            df[out_col] = 0.0

    # Efektivita
    if 'Number of pieces' in df.columns and 'Process_Minutes' in df.columns:
        df['Efficiency_Pcs_Per_Min'] = np.where(
            df['Process_Minutes'] > 0, 
            df['Number of pieces'] / df['Process_Minutes'], 
            0.0
        )
    else:
        df['Efficiency_Pcs_Per_Min'] = 0.0

    # Čištění textových sloupců zákazníka a materiálu
    for col in ['CUSTOMER', 'Material', 'OE/NOE', 'order type', 'del.type']:
        if col in df.columns:
            df[col] = df[col].fillna('UNKNOWN').astype(str)

    # Identifikace zpožďujících faktorů (převod na boolean masky)
    delay_cols = ['Scanning serial numbers', 'Reprinting labels', 'Difficult KLTs']
    for col in delay_cols:
        if col in df.columns:
            # Považujeme za True, pokud není prázdné/NaN a není to 'N' nebo '0'
            df[f'Flag_{col}'] = df[col].notna() & (~df[col].astype(str).str.upper().isin(['N', '0', 'NO', 'FALSE', '']))
        else:
            df[f'Flag_{col}'] = False

    return df

# -----------------------------------------------------------------------------
# 5. SIDEBAR
# -----------------------------------------------------------------------------
selected_lang = st.sidebar.radio(
    TEXTS[st.session_state.lang]['lang_select'],
    ['CZ', 'EN'],
    index=0 if st.session_state.lang == 'CZ' else 1,
    horizontal=True
)
if selected_lang != st.session_state.lang:
    st.session_state.lang = selected_lang
    st.rerun()

t = TEXTS[st.session_state.lang]

st.sidebar.title(t['sidebar_title'])
uploaded_file = st.sidebar.file_uploader(t['upload_file'], type=['csv', 'xlsx'], key='file_uploader_key')

if uploaded_file is not None:
    try:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if 'file_id' not in st.session_state or st.session_state.file_id != file_id:
            if uploaded_file.name.endswith('.csv'):
                try:
                    raw_df = pd.read_csv(uploaded_file, sep=',', encoding='utf-8', dtype=str)
                    if len(raw_df.columns) < 5: 
                         raw_df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', dtype=str)
                except:
                    raw_df = pd.read_csv(uploaded_file, sep=';', encoding='latin1', dtype=str)
            else:
                raw_df = pd.read_excel(uploaded_file, dtype=str)
            
            st.session_state.raw_data = raw_df
            st.session_state.processed_data = process_data(raw_df)
            st.session_state.file_id = file_id
            
    except Exception as e:
        st.sidebar.error(f"Chyba: {e}")

df_filtered = None
if st.session_state.processed_data is not None:
    df_all = st.session_state.processed_data
    max_pieces = int(df_all.get('Number of pieces', pd.Series([0])).max())
    min_pieces_filter = st.sidebar.slider(t['min_pieces'], 0, max_pieces, 0)
    
    available_customers = sorted(df_all['CUSTOMER'].unique().tolist()) if 'CUSTOMER' in df_all.columns else []
    selected_customers = st.sidebar.multiselect(t['filter_customer'], options=available_customers, default=available_customers)
    
    mask = (df_all['Number of pieces'] >= min_pieces_filter)
    if available_customers:
        mask = mask & (df_all['CUSTOMER'].isin(selected_customers))
    df_filtered = df_all[mask].copy()

# -----------------------------------------------------------------------------
# 6. HLAVNÍ OBSAH
# -----------------------------------------------------------------------------
st.title(t['title'])

if df_filtered is None or len(df_filtered) == 0:
    if st.session_state.processed_data is None:
        st.info(t['no_data'])
    else:
        st.warning("Žádná data neodpovídají filtrům.")
else:
    df = df_filtered

    tab_dash, tab_mat, tab_delay, tab_top, tab_audit, tab_export = st.tabs([
        t['tab_dash'], t['tab_mat'], t['tab_delay'], t['tab_top'], t['tab_audit'], t['tab_export']
    ])

    # --- ZÁLOŽKA 1: DASHBOARD ---
    with tab_dash:
        m1, m2, m3, m4, m5 = st.columns(5)
        total_orders = len(df)
        total_pieces = int(df.get('Number of pieces', pd.Series([0])).sum())
        total_weight = round(df.get('Weight (kg)', pd.Series([0])).sum(), 1)
        
        sum_mins = df.get('Process_Minutes', pd.Series([0])).sum()
        global_eff = round(total_pieces / sum_mins, 2) if sum_mins > 0 else 0
        avg_effort = round(df.get('Effort_Minutes', pd.Series([0])).mean(), 2)

        m1.metric(t['metric_orders'], f"{total_orders:,}".replace(',', ' '))
        m2.metric(t['metric_pieces'], f"{total_pieces:,}".replace(',', ' '))
        m3.metric(t['metric_weight'], f"{total_weight:,.1f}".replace(',', ' '))
        m4.metric(t['metric_efficiency'], f"{global_eff}")
        m5.metric(t['metric_effort'], f"{avg_effort}")

        st.markdown("<hr>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(t['chart_mat_vol'])
            if 'Material' in df.columns:
                mat_vol = df.groupby('Material', as_index=False)['Number of pieces'].sum().nlargest(10, 'Number of pieces')
                st.bar_chart(data=mat_vol, x='Material', y='Number of pieces', color="#1f77b4")
        
        with c2:
            st.subheader("Rozložení typů objednávek (Order Type / Del Type)")
            cols_type = [c for c in ['order type', 'del.type'] if c in df.columns]
            if cols_type:
                for col in cols_type:
                    type_dist = df[col].value_counts().reset_index()
                    type_dist.columns = [col, 'Počet']
                    # Očištění o UNKNOWN pro čistší graf
                    type_dist = type_dist[type_dist[col] != 'UNKNOWN']
                    st.write(f"**{col}**")
                    st.bar_chart(data=type_dist, x=col, y='Počet', color="#ff7f0e", height=200)

    # --- ZÁLOŽKA 2: MATERIÁLY A OBALY ---
    with tab_mat:
        mc1, mc2 = st.columns(2)
        
        with mc1:
            st.subheader("Průměrná spotřeba obalů dle Materiálu")
            if 'Material' in df.columns:
                pack_cols = [c for c in ['Number of cartons', 'Number of KLTs', 'Number of pallets'] if c in df.columns]
                if pack_cols:
                    mat_pack = df.groupby('Material')[pack_cols].mean().reset_index()
                    mat_pack['Total_Avg_Packs'] = mat_pack[pack_cols].sum(axis=1)
                    mat_pack = mat_pack.nlargest(10, 'Total_Avg_Packs')
                    st.dataframe(mat_pack, use_container_width=True)
        
        with mc2:
            st.subheader(t['chart_pack_types'])
            # Extrakce textových řetězců konkrétních obalů (např. CARTON-16) ze sloupců Cartons, KLT, Palety
            spec_cols = [c for c in ['Cartons', 'KLT', 'Palety'] if c in df.columns]
            if spec_cols:
                all_packs = pd.Series(dtype=str)
                for c in spec_cols:
                    # Vyfiltrujeme NaN a prázdné
                    valid_texts = df[df[c].notna() & (df[c] != 'NaN') & (df[c] != '')][c]
                    all_packs = pd.concat([all_packs, valid_texts])
                
                if not all_packs.empty:
                    # Rychlé value_counts na textových řetězcích (ukáže nejčastější kombinace obalů)
                    top_specific = all_packs.value_counts().head(10).reset_index()
                    top_specific.columns = ['Specifikace Obalu', 'Počet zakázek']
                    st.dataframe(top_specific, use_container_width=True)
                else:
                    st.write("Sloupce obalů neobsahují specifické textové popisy.")

        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.subheader(t['chart_pack_corr'])
        sc1, sc2 = st.columns(2)
        with sc1:
            if 'Weight (kg)' in df.columns and 'Number of pallets' in df.columns:
                st.write("**Váha vs. Počet Palet**")
                st.scatter_chart(data=df, x='Weight (kg)', y='Number of pallets', color="#2ca02c")
        with sc2:
            if 'Number of pieces' in df.columns and 'Number of cartons' in df.columns:
                st.write("**Kusy vs. Počet Kartonů**")
                st.scatter_chart(data=df, x='Number of pieces', y='Number of cartons', color="#d62728")

    # --- ZÁLOŽKA 3: SLOŽITOST A ZDRŽENÍ (DELAYS) ---
    with tab_delay:
        st.info(t['delay_title'])
        st.write(t['delay_desc'])
        
        delay_flags = [c for c in df.columns if c.startswith('Flag_')]
        if delay_flags and 'Process_Minutes' in df.columns:
            delay_data = []
            for flag in delay_flags:
                name = flag.replace('Flag_', '')
                # Průměrný čas s úkonem vs bez něj
                avg_with = df[df[flag] == True]['Process_Minutes'].mean()
                avg_without = df[df[flag] == False]['Process_Minutes'].mean()
                
                count_with = df[flag].sum()
                
                if not pd.isna(avg_with) and not pd.isna(avg_without):
                    diff = avg_with - avg_without
                    delay_data.append({
                        'Úkon / Komplikace': name,
                        'Počet případů': int(count_with),
                        'Prům. čas BEZ (min)': round(avg_without, 2),
                        'Prům. čas S (min)': round(avg_with, 2),
                        'Rozdíl (Zdržení v min)': round(diff, 2)
                    })
            
            if delay_data:
                delay_df = pd.DataFrame(delay_data).sort_values(by='Rozdíl (Zdržení v min)', ascending=False)
                st.dataframe(delay_df, use_container_width=True)
                
                # Grafický pohled na zdržení
                st.bar_chart(data=delay_df, x='Úkon / Komplikace', y='Rozdíl (Zdržení v min)', color="#e377c2")
            else:
                st.write("Nenalezeny dostatečné záznamy pro porovnání.")
                
        # Porovnání Process Time vs Effort Time
        if 'Process_Minutes' in df.columns and 'Effort_Minutes' in df.columns:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.subheader("Process Time vs. Effort Time (Identifikace neefektivity)")
            df['Time_Difference_Min'] = df['Effort_Minutes'] - df['Process_Minutes']
            
            diff_df = df.nlargest(10, 'Time_Difference_Min')
            cols_show = ['DN NUMBER (SAP)', 'Material', 'Process_Minutes', 'Effort_Minutes', 'Time_Difference_Min']
            cols_show = [c for c in cols_show if c in df.columns]
            
            st.write("TOP 10 zakázek s největším rozdílem mezi čistým a vynaloženým časem:")
            st.dataframe(diff_df[cols_show], use_container_width=True)

    # --- ZÁLOŽKA 4: TOP TABULKY ---
    with tab_top:
        tc1, tc2 = st.columns(2)
        with tc1:
            st.subheader("TOP 10 Nejpomalejších procesů (Kusy/Min)")
            # Filtrujeme nulovou efektivitu pro relevanci
            df_eff = df[df['Efficiency_Pcs_Per_Min'] > 0]
            cols_eff = ['DN NUMBER (SAP)', 'Material', 'Number of pieces', 'Process_Minutes', 'Efficiency_Pcs_Per_Min']
            st.dataframe(df_eff.nsmallest(10, 'Efficiency_Pcs_Per_Min')[[c for c in cols_eff if c in df.columns]], use_container_width=True)
            
        with tc2:
            st.subheader("TOP 10 Nejtěžších zakázek (Váha)")
            if 'Weight (kg)' in df.columns:
                cols_w = ['DN NUMBER (SAP)', 'Material', 'Weight (kg)', 'Number of pallets', 'Number of pieces']
                st.dataframe(df.nlargest(10, 'Weight (kg)')[[c for c in cols_w if c in df.columns]], use_container_width=True)

    # --- ZÁLOŽKA 5: AUDIT ---
    with tab_audit:
        st.info(t['audit_desc'])
        sample_size = min(5, len(df))
        sample_df = df.sample(sample_size, random_state=np.random.RandomState())
        
        if 'DN NUMBER (SAP)' in sample_df.columns:
            for _, row in sample_df.iterrows():
                dn = row['DN NUMBER (SAP)']
                with st.expander(f"Audit zakázky: {dn}"):
                    pcs = row.get('Number of pieces', 0)
                    mins = row.get('Process_Minutes', 0)
                    eff = row.get('Efficiency_Pcs_Per_Min', 0)
                    mat = row.get('Material', 'N/A')
                    
                    st.write(f"- **Materiál:** {mat}")
                    st.write(f"- **Vstupní čas (Process Time):** {row.get('Process Time', 'N/A')} -> převedeno na `{mins:.2f} min`")
                    st.write(f"- **Kusy:** `{pcs}`")
                    st.write(f"- **Efektivita (Matematika):** `{pcs} / {mins:.2f} = {eff:.2f} ks/min`")
                    
                    # Audit složitosti
                    flags_present = [c.replace('Flag_', '') for c in delay_flags if row.get(c, False)]
                    if flags_present:
                        st.write(f"- **Aktivní komplikace:** {', '.join(flags_present)}")
                    else:
                        st.write("- **Bez komplikací (běžný proces)**")
        else:
            st.warning("Nelze provést audit (chybí DN NUMBER).")

    # --- ZÁLOŽKA 6: EXPORT ---
    with tab_export:
        st.write(t['export_desc'])
        
        def generate_ultimate_excel(dataframe: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Ošetření časových objektů před exportem
                export_df = dataframe.copy()
                # Vyhození pomocných flagů pokud je nechceme v datech
                export_df = export_df.loc[:, ~export_df.columns.str.startswith('Flag_')]
                
                time_cols = ['Process Time', 'START', 'END', 'Process Time - cleaned (no break)', 'Effort Time']
                for c in time_cols:
                    if c in export_df.columns:
                        export_df[c] = export_df[c].astype(str)
                
                # List 1: Surová data
                export_df.to_excel(writer, sheet_name='Obohacena_Data', index=False)
                
                # List 2: Analýza Materiálů
                if 'Material' in export_df.columns:
                    mat_agg = {
                        'DN NUMBER (SAP)': 'count',
                        'Number of pieces': 'sum',
                        'Process_Minutes': 'mean',
                        'Weight (kg)': 'sum',
                        'Number of cartons': 'sum',
                        'Number of KLTs': 'sum',
                        'Number of pallets': 'sum'
                    }
                    mat_agg = {k: v for k, v in mat_agg.items() if k in export_df.columns}
                    if mat_agg:
                        mat_summary = export_df.groupby('Material').agg(mat_agg).reset_index()
                        mat_summary.to_excel(writer, sheet_name='Analyza_Materialu', index=False)

                # List 3: Slovník pojmů
                pd.DataFrame({
                    'Sloupec / Metrika': ['Process_Minutes', 'Effort_Minutes', 'Efficiency_Pcs_Per_Min', 'Time_Difference_Min'],
                    'Význam': [
                        'Procesní čas vyjádřený v desetinných minutách.',
                        'Celkový vynaložený čas v minutách.',
                        'Výkon balení: Počet kusů / Process_Minutes.',
                        'Rozdíl mezi Effort Time a Process Time (ztrátový čas).'
                    ]
                }).to_excel(writer, sheet_name='Metodika', index=False)
                
            return output.getvalue()

        excel_data = generate_ultimate_excel(df)
        
        st.download_button(
            label=t['btn_export'],
            data=excel_data,
            file_name="Ultimate_Packing_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type='primary'
        )
