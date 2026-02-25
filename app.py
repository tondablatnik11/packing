import streamlit as st
import pandas as pd
import numpy as np
import io

# -----------------------------------------------------------------------------
# 1. KONFIGURACE STRÁNKY A CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Pro Warehouse Analytics",
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
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 55px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 6px 6px 0px 0px;
        font-weight: 600;
        font-size: 16px;
    }
    hr {
        margin-top: 1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOKALIZAČNÍ SLOVNÍK (CZ/EN)
# -----------------------------------------------------------------------------
TEXTS = {
    'CZ': {
        'title': '📦 Pro Warehouse Packing Analytics',
        'sidebar_title': '⚙️ Parametry Analýzy',
        'lang_select': '🌐 Jazyk / Language',
        'upload_file': '📁 Nahrát zdrojová data (CSV/XLSX)',
        'min_pieces': '🔍 Min. počet kusů (Odfiltrovat malé):',
        'filter_customer': '🏢 Filtrovat Zákazníky:',
        'tab_dash': '📊 Hlavní Dashboard',
        'tab_adv': '📈 Pokročilá Analýza',
        'tab_top': '🏆 TOP Extrémy',
        'tab_audit': '🔎 Transparentní Audit',
        'tab_export': '💾 Export do Excelu',
        'metric_orders': 'Zpracováno zakázek',
        'metric_pieces': 'Zabaleno kusů',
        'metric_weight': 'Celková tonáž (kg)',
        'metric_efficiency': 'Efektivita (ks/min)',
        'metric_items': 'Prům. typů položek / zakázku',
        'chart_cust_vol': 'Objem kusů dle Zákazníků',
        'chart_peak_hours': 'Pracovní špička (Objem dle hodiny začátku)',
        'chart_packaging': 'Spotřeba obalového materiálu (Ks)',
        'chart_shift': 'Výkon dle Směny / Skupiny',
        'chart_scatter': 'Korelace: Čas balení vs. Počet kusů (Detekce anomálií)',
        'top_longest': 'Nejdelší procesy balení (Čas)',
        'top_largest': 'Největší zakázky (Kusy)',
        'top_complex': 'Nejsložitější zakázky (Typy položek)',
        'top_heavy': 'Nejtěžší zakázky (Váha v kg)',
        'audit_desc': 'Automatický audit logiky na 5 náhodných vzorcích. Kontroluje matematiku na pozadí.',
        'audit_order': 'Detail výpočtu zakázky:',
        'export_desc': 'Kompletní zpracovaná data připravená pro controllingový reporting.',
        'btn_export': '📥 Stáhnout Controlling Report (.xlsx)',
        'no_data': 'Prosím, nahrajte soubor s daty v levém panelu pro zahájení analýzy.'
    },
    'EN': {
        'title': '📦 Pro Warehouse Packing Analytics',
        'sidebar_title': '⚙️ Analysis Parameters',
        'lang_select': '🌐 Jazyk / Language',
        'upload_file': '📁 Upload Source Data (CSV/XLSX)',
        'min_pieces': '🔍 Min. Pieces (Filter small orders):',
        'filter_customer': '🏢 Filter Customers:',
        'tab_dash': '📊 Main Dashboard',
        'tab_adv': '📈 Advanced Analytics',
        'tab_top': '🏆 TOP Extremes',
        'tab_audit': '🔎 Transparent Audit',
        'tab_export': '💾 Export to Excel',
        'metric_orders': 'Processed Orders',
        'metric_pieces': 'Packed Pieces',
        'metric_weight': 'Total Tonnage (kg)',
        'metric_efficiency': 'Efficiency (pcs/min)',
        'metric_items': 'Avg Item Types / Order',
        'chart_cust_vol': 'Piece Volume by Customer',
        'chart_peak_hours': 'Workload Peak (Volume by Start Hour)',
        'chart_packaging': 'Packaging Material Consumption (Pcs)',
        'chart_shift': 'Performance by Shift / Group',
        'chart_scatter': 'Correlation: Packing Time vs. Pieces (Anomaly Detection)',
        'top_longest': 'Longest Packing Processes (Time)',
        'top_largest': 'Largest Orders (Pieces)',
        'top_complex': 'Most Complex Orders (Item Types)',
        'top_heavy': 'Heaviest Orders (Weight in kg)',
        'audit_desc': 'Automated logic audit on 5 random samples. Verifies background math.',
        'audit_order': 'Calculation detail for order:',
        'export_desc': 'Complete processed data ready for controlling reporting.',
        'btn_export': '📥 Download Controlling Report (.xlsx)',
        'no_data': 'Please upload a data file in the left sidebar to start the analysis.'
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
# 4. FUNKCE PRO ZPRACOVÁNÍ DAT (VEKTORIZACE)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    
    # Bezpečný převod numerických sloupců
    num_cols = [
        'Number of pieces', 'Number of cartons', 'Number of pallets', 
        'Number of KLTs', 'Number of item types', 'Weight (kg)'
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Zpracování času balení (Process Time) na minuty
    if 'Process Time' in df.columns:
        time_strings = df['Process Time'].astype(str)
        pt_timedelta = pd.to_timedelta(time_strings, errors='coerce')
        df['Process_Minutes'] = pt_timedelta.dt.total_seconds() / 60.0
        df['Process_Minutes'] = df['Process_Minutes'].fillna(0)
    else:
        df['Process_Minutes'] = 0.0

    # Výpočet efektivity (kusy za minutu)
    if 'Number of pieces' in df.columns and 'Process_Minutes' in df.columns:
        df['Efficiency_Pcs_Per_Min'] = np.where(
            df['Process_Minutes'] > 0, 
            df['Number of pieces'] / df['Process_Minutes'], 
            0.0
        )
    else:
        df['Efficiency_Pcs_Per_Min'] = 0.0

    # Extrakce hodiny začátku pro analýzu špičky
    if 'START' in df.columns:
        # Některé excel formáty sem hodí datetime.time, jindy string. Ošetříme to:
        start_strings = df['START'].astype(str)
        # Ořízneme, pokud to obsahuje datum a čas
        start_strings = start_strings.str.split(' ').str[-1]
        try:
            df['Start_Hour'] = pd.to_datetime(start_strings, format='%H:%M:%S', errors='coerce').dt.hour
        except:
            df['Start_Hour'] = np.nan
            
    # Vyčištění sloupce zákazníka od NaN
    if 'CUSTOMER' in df.columns:
        df['CUSTOMER'] = df['CUSTOMER'].fillna('UNKNOWN').astype(str)

    return df

# -----------------------------------------------------------------------------
# 5. SIDEBAR A FILTROVÁNÍ
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
                    raw_df = pd.read_csv(uploaded_file, sep=',', encoding='utf-8')
                    if len(raw_df.columns) < 5: 
                         raw_df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
                except:
                    raw_df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
            else:
                raw_df = pd.read_excel(uploaded_file)
            
            st.session_state.raw_data = raw_df
            st.session_state.processed_data = process_data(raw_df)
            st.session_state.file_id = file_id
            
    except Exception as e:
        st.sidebar.error(f"Chyba při načítání: {e}")

# Pokud máme data, zobrazíme filtry
df_filtered = None
if st.session_state.processed_data is not None:
    df_all = st.session_state.processed_data
    
    # Filtr na kusy
    max_pieces = int(df_all.get('Number of pieces', [0]).max())
    min_pieces_filter = st.sidebar.slider(t['min_pieces'], 0, max_pieces, 0)
    
    # Filtr na zákazníka
    available_customers = []
    if 'CUSTOMER' in df_all.columns:
        available_customers = sorted(df_all['CUSTOMER'].unique().tolist())
    
    selected_customers = st.sidebar.multiselect(
        t['filter_customer'], 
        options=available_customers, 
        default=available_customers
    )
    
    # Aplikace filtrů přes masky
    mask = (df_all['Number of pieces'] >= min_pieces_filter)
    if available_customers:
        mask = mask & (df_all['CUSTOMER'].isin(selected_customers))
        
    df_filtered = df_all[mask].copy()

# -----------------------------------------------------------------------------
# 6. HLAVNÍ OBSAH (TABS)
# -----------------------------------------------------------------------------
st.title(t['title'])

if df_filtered is None or len(df_filtered) == 0:
    if st.session_state.processed_data is None:
        st.info(t['no_data'])
    else:
        st.warning("Žádná data neodpovídají zvoleným filtrům.")
else:
    df = df_filtered

    tab_dash, tab_adv, tab_top, tab_audit, tab_export = st.tabs([
        t['tab_dash'], t['tab_adv'], t['tab_top'], t['tab_audit'], t['tab_export']
    ])

    # --- ZÁLOŽKA 1: DASHBOARD ---
    with tab_dash:
        # Top Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        
        total_orders = len(df)
        total_pieces = int(df.get('Number of pieces', pd.Series([0])).sum())
        total_weight = round(df.get('Weight (kg)', pd.Series([0])).sum(), 1)
        avg_items = round(df.get('Number of item types', pd.Series([0])).mean(), 1)
        
        sum_mins = df.get('Process_Minutes', pd.Series([0])).sum()
        global_efficiency = round(total_pieces / sum_mins, 2) if sum_mins > 0 else 0

        m1.metric(t['metric_orders'], f"{total_orders:,}".replace(',', ' '))
        m2.metric(t['metric_pieces'], f"{total_pieces:,}".replace(',', ' '))
        m3.metric(t['metric_weight'], f"{total_weight:,.1f}".replace(',', ' '))
        m4.metric(t['metric_efficiency'], f"{global_efficiency}")
        m5.metric(t['metric_items'], f"{avg_items}")

        st.markdown("<hr>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader(t['chart_cust_vol'])
            if 'CUSTOMER' in df.columns:
                cust_vol = df.groupby('CUSTOMER', as_index=False)['Number of pieces'].sum()
                cust_vol = cust_vol.sort_values('Number of pieces', ascending=False).head(15)
                st.bar_chart(data=cust_vol, x='CUSTOMER', y='Number of pieces', color="#1f77b4")
        
        with c2:
            st.subheader(t['chart_peak_hours'])
            if 'Start_Hour' in df.columns:
                # Rozložení práce během dne
                hourly_vol = df.dropna(subset=['Start_Hour']).groupby('Start_Hour', as_index=False)['Number of pieces'].sum()
                hourly_vol['Start_Hour'] = hourly_vol['Start_Hour'].astype(int).astype(str) + ":00"
                st.bar_chart(data=hourly_vol, x='Start_Hour', y='Number of pieces', color="#ff7f0e")

    # --- ZÁLOŽKA 2: POKROČILÁ ANALÝZA ---
    with tab_adv:
        ac1, ac2 = st.columns(2)
        
        with ac1:
            st.subheader(t['chart_packaging'])
            # Sumarizace obalů
            pack_cols = ['Number of pallets', 'Number of cartons', 'Number of KLTs']
            pack_data = {"Obal": [], "Množství": []}
            for col in pack_cols:
                if col in df.columns:
                    val = df[col].sum()
                    if val > 0:
                        name = col.replace("Number of ", "").capitalize()
                        pack_data["Obal"].append(name)
                        pack_data["Množství"].append(val)
            
            if pack_data["Obal"]:
                pack_df = pd.DataFrame(pack_data)
                st.bar_chart(data=pack_df, x='Obal', y='Množství', color="#2ca02c")
            else:
                st.write("Nedostatek dat o obalech.")

        with ac2:
            st.subheader(t['chart_shift'])
            if 'Shift' in df.columns:
                shift_vol = df.groupby('Shift', as_index=False)['Number of pieces'].sum()
                st.bar_chart(data=shift_vol, x='Shift', y='Number of pieces', color="#d62728")
            else:
                st.write("Sloupec 'Shift' nenalezen.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader(t['chart_scatter'])
        st.write("Každý bod představuje jednu zakázku. Slouží k rychlému odhalení zakázek, které trvaly neúměrně dlouho na to, jak málo měly kusů.")
        if 'Process_Minutes' in df.columns and 'Number of pieces' in df.columns:
            st.scatter_chart(data=df, x='Number of pieces', y='Process_Minutes', size='Number of item types', color="#9467bd")

    # --- ZÁLOŽKA 3: TOP EXTRÉMY ---
    with tab_top:
        tc1, tc2 = st.columns(2)
        
        with tc1:
            st.subheader(t['top_longest'])
            cols_l = ['DN NUMBER (SAP)', 'CUSTOMER', 'Process Time', 'Number of pieces']
            st.dataframe(df.nlargest(10, 'Process_Minutes')[[c for c in cols_l if c in df.columns]], use_container_width=True)
            
            st.subheader(t['top_complex'])
            if 'Number of item types' in df.columns:
                cols_c = ['DN NUMBER (SAP)', 'CUSTOMER', 'Number of item types', 'Process_Minutes']
                st.dataframe(df.nlargest(10, 'Number of item types')[[c for c in cols_c if c in df.columns]], use_container_width=True)

        with tc2:
            st.subheader(t['top_largest'])
            cols_p = ['DN NUMBER (SAP)', 'CUSTOMER', 'Number of pieces', 'Efficiency_Pcs_Per_Min']
            st.dataframe(df.nlargest(10, 'Number of pieces')[[c for c in cols_p if c in df.columns]], use_container_width=True)
            
            st.subheader(t['top_heavy'])
            if 'Weight (kg)' in df.columns:
                cols_w = ['DN NUMBER (SAP)', 'CUSTOMER', 'Weight (kg)', 'Number of pallets']
                st.dataframe(df.nlargest(10, 'Weight (kg)')[[c for c in cols_w if c in df.columns]], use_container_width=True)

    # --- ZÁLOŽKA 4: AUDIT ---
    with tab_audit:
        st.info(t['audit_desc'])
        sample_size = min(5, len(df))
        sample_df = df.sample(sample_size, random_state=np.random.RandomState())
        
        if 'DN NUMBER (SAP)' in sample_df.columns:
            dn_numbers = sample_df['DN NUMBER (SAP)'].values
            pcs_arr = sample_df['Number of pieces'].values if 'Number of pieces' in sample_df.columns else [0]*sample_size
            mins_arr = sample_df['Process_Minutes'].values
            eff_arr = sample_df['Efficiency_Pcs_Per_Min'].values
            
            for dn, pcs, mins, eff in zip(dn_numbers, pcs_arr, mins_arr, eff_arr):
                with st.expander(f"{t['audit_order']} {dn}"):
                    st.write(f"- **Vstup:** Zakázka má hlášeno `{pcs}` kusů.")
                    st.write(f"- **Transformace času:** Vypočtený čas balení je `{mins:.2f}` minut.")
                    if mins > 0:
                        st.write(f"- **Matematika efektivity:** {pcs} / {mins:.2f} = `{eff:.2f}` kusů za minutu.")
                    else:
                        st.write(f"- **Matematika efektivity:** Čas je 0, aplikována ochrana proti dělení nulou -> `0` kusů za minutu.")
        else:
            st.warning("Sloupec 'DN NUMBER (SAP)' chybí.")

    # --- ZÁLOŽKA 5: EXPORT ---
    with tab_export:
        st.write(t['export_desc'])
        
        def generate_pro_excel(dataframe: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Ošetření časových objektů před exportem
                export_df = dataframe.drop(columns=['Start_Hour'], errors='ignore').copy()
                time_cols = ['Process Time', 'START', 'END', 'Process Time - cleaned (no break)', 'Effort Time']
                for c in time_cols:
                    if c in export_df.columns:
                        export_df[c] = export_df[c].astype(str)
                
                # Surová data
                export_df.to_excel(writer, sheet_name='Obohacena_Data', index=False)
                
                # Souhrn dle Zákazníků
                if 'CUSTOMER' in export_df.columns:
                    agg_funcs = {
                        'DN NUMBER (SAP)': 'count',
                        'Number of pieces': 'sum',
                        'Process_Minutes': 'sum',
                        'Weight (kg)': 'sum'
                    }
                    agg_funcs = {k: v for k, v in agg_funcs.items() if k in export_df.columns}
                    
                    if agg_funcs:
                        summary = export_df.groupby('CUSTOMER').agg(agg_funcs).reset_index()
                        summary.rename(columns={'DN NUMBER (SAP)': 'Zakazek'}, inplace=True)
                        if 'Process_Minutes' in summary.columns and 'Number of pieces' in summary.columns:
                            summary['Efektivita_Kusy_Min'] = np.where(
                                summary['Process_Minutes'] > 0,
                                summary['Number of pieces'] / summary['Process_Minutes'], 0
                            )
                        summary.to_excel(writer, sheet_name='Souhrn_Zakaznici', index=False)
                
                # Metodika
                pd.DataFrame({
                    'Parametr': ['Process_Minutes', 'Efficiency_Pcs_Per_Min', 'Start_Hour'],
                    'Význam': [
                        'Deklarovaný procesní čas převedený plně do minut.',
                        'Počet zabalených kusů za 1 minutu procesního času.',
                        'Extrahovaná hodina začátku balení (0-23) pro analýzu špiček.'
                    ]
                }).to_excel(writer, sheet_name='Slovnik_Pojmu', index=False)
                
            return output.getvalue()

        excel_data = generate_pro_excel(df)
        
        st.download_button(
            label=t['btn_export'],
            data=excel_data,
            file_name="Logistics_Controlling_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type='primary'
        )
