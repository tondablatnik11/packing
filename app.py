import streamlit as st
import pandas as pd
import numpy as np
import io

# -----------------------------------------------------------------------------
# 1. KONFIGURACE STRÁNKY A CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Warehouse Packing Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Jemné moderní CSS pro vylepšení vzhledu metrik a celkového UI
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #1f77b4 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        color: #555555 !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOKALIZAČNÍ SLOVNÍK (CZ/EN)
# -----------------------------------------------------------------------------
TEXTS = {
    'CZ': {
        'title': '📦 Analýza balení v logistickém skladu',
        'sidebar_title': '⚙️ Konfigurace',
        'lang_select': '🌐 Zvolte jazyk',
        'upload_file': '📁 Nahrajte datový soubor (CSV/XLSX)',
        'min_pieces': '🔍 Minimální počet kusů k analýze:',
        'tab_dash': '📊 Dashboard',
        'tab_top': '🏆 TOP Tabulky',
        'tab_audit': '🔎 Transparentní Audit',
        'tab_export': '💾 Export Výsledků',
        'metric_orders': 'Celkem zakázek',
        'metric_pieces': 'Zabaleno kusů celkem',
        'metric_avg_time': 'Průměrný čas balení (min)',
        'metric_efficiency': 'Efektivita (ks / min)',
        'chart_cust_vol': 'Objem kusů dle zákazníků',
        'top_longest': 'Nejdelší procesy balení (TOP 10)',
        'top_largest': 'Největší zakázky podle objemu kusů (TOP 10)',
        'audit_desc': 'Tato sekce náhodně vybere 5 zakázek a transparentně krok za krokem vysvětlí, jak se vypočítaly jejich metriky. Otestuje logiku bez nutnosti otevírat kód.',
        'audit_order': 'Zakázka (DN NUMBER):',
        'audit_step1': 'Krok 1: Extrakce surových dat',
        'audit_step2': 'Krok 2: Transformace času',
        'audit_step3': 'Krok 3: Výpočet efektivity',
        'export_desc': 'Stáhněte si zpracovaná a obohacená data včetně souhrnných statistik do Excelu s více listy.',
        'btn_export': '📥 Stáhnout kompletní report v Excelu',
        'export_success': 'Report úspěšně připraven!',
        'no_data': 'Prosím, nahrajte soubor s daty v levém panelu pro zahájení analýzy.'
    },
    'EN': {
        'title': '📦 Logistics Warehouse Packing Analysis',
        'sidebar_title': '⚙️ Configuration',
        'lang_select': '🌐 Select Language',
        'upload_file': '📁 Upload Data File (CSV/XLSX)',
        'min_pieces': '🔍 Minimum pieces to analyze:',
        'tab_dash': '📊 Dashboard',
        'tab_top': '🏆 TOP Tables',
        'tab_audit': '🔎 Transparent Audit',
        'tab_export': '💾 Export Results',
        'metric_orders': 'Total Orders',
        'metric_pieces': 'Total Pieces Packed',
        'metric_avg_time': 'Avg Packing Time (min)',
        'metric_efficiency': 'Efficiency (pcs / min)',
        'chart_cust_vol': 'Volume of pieces by Customer',
        'top_longest': 'Longest packing processes (TOP 10)',
        'top_largest': 'Largest orders by piece volume (TOP 10)',
        'audit_desc': 'This section randomly selects 5 orders and transparently explains step-by-step how their metrics were calculated. It verifies the logic without looking at the code.',
        'audit_order': 'Order (DN NUMBER):',
        'audit_step1': 'Step 1: Raw data extraction',
        'audit_step2': 'Step 2: Time transformation',
        'audit_step3': 'Step 3: Efficiency calculation',
        'export_desc': 'Download processed and enriched data including summary statistics into a multi-sheet Excel file.',
        'btn_export': '📥 Download full Excel report',
        'export_success': 'Report successfully prepared!',
        'no_data': 'Please upload a data file in the left sidebar to start the analysis.'
    }
}

# -----------------------------------------------------------------------------
# 3. SPRÁVA STAVU A LOKALIZACE (SESSION STATE)
# -----------------------------------------------------------------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'CZ'
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

# -----------------------------------------------------------------------------
# 4. FUNKCE PRO ZPRACOVÁNÍ DAT (ČISTÁ VEKTORIZACE)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vysoce optimalizovaná funkce pro čištění a obohacení dat.
    Používá vektorizované operace, vyhýbá se apply/iterrows.
    """
    df = df.copy()
    
    # 1. Čištění názvů sloupců (odstranění zbytečných mezer)
    df.columns = df.columns.str.strip()
    
    # 2. Vektorizovaný převod 'Process Time' na sekundy a minuty
    # Předpoklad: formát HH:MM:SS
    # Chyby převádíme na NaT (Not a Time), následně na 0 sekund
    if 'Process Time' in df.columns:
        # Převedeme na timedelta
        pt_timedelta = pd.to_timedelta(df['Process Time'], errors='coerce')
        # Získáme celkové sekundy a převedeme na minuty
        df['Process_Minutes'] = pt_timedelta.dt.total_seconds() / 60.0
        df['Process_Minutes'] = df['Process_Minutes'].fillna(0)
    else:
        df['Process_Minutes'] = 0.0

    # 3. Zajištění numerických datových typů pro klíčové sloupce
    num_cols = ['Number of pieces', 'Number of cartons', 'Number of pallets', 'Weight (kg)']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 4. Výpočet efektivity (kusy za minutu) pomocí rychlé numpy vektorizace (np.where)
    # Zabráníme dělení nulou
    if 'Number of pieces' in df.columns and 'Process_Minutes' in df.columns:
        df['Efficiency_Pcs_Per_Min'] = np.where(
            df['Process_Minutes'] > 0, 
            df['Number of pieces'] / df['Process_Minutes'], 
            0.0
        )
    else:
        df['Efficiency_Pcs_Per_Min'] = 0.0

    # 5. Výpočet objemové zátěže (Váha na kus)
    if 'Weight (kg)' in df.columns and 'Number of pieces' in df.columns:
        df['Weight_Per_Piece_kg'] = np.where(
            df['Number of pieces'] > 0,
            df['Weight (kg)'] / df['Number of pieces'],
            0.0
        )
        
    return df

# -----------------------------------------------------------------------------
# 5. SIDEBAR - UI KONFIGURACE A NAHRÁVÁNÍ
# -----------------------------------------------------------------------------
st.sidebar.title(TEXTS[st.session_state.lang]['sidebar_title'])

# Změna jazyka 
selected_lang = st.sidebar.radio(
    TEXTS[st.session_state.lang]['lang_select'],
    ['CZ', 'EN'],
    index=0 if st.session_state.lang == 'CZ' else 1,
    horizontal=True
)
# Okamžitá aktualizace jazyka bez nutnosti ztratit data
if selected_lang != st.session_state.lang:
    st.session_state.lang = selected_lang
    st.rerun()

t = TEXTS[st.session_state.lang]

# File Uploader s definovaným key pro session state
uploaded_file = st.sidebar.file_uploader(t['upload_file'], type=['csv', 'xlsx'], key='file_uploader_key')

if uploaded_file is not None:
    try:
        # Načtení dat pouze pokud ještě nejsou v session state nebo byl nahrán nový soubor
        # K identifikaci změn použijeme název a velikost
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if 'file_id' not in st.session_state or st.session_state.file_id != file_id:
            if uploaded_file.name.endswith('.csv'):
                # Pokusíme se načíst CSV s ohledem na různé oddělovače
                try:
                    raw_df = pd.read_csv(uploaded_file, sep=',', encoding='utf-8')
                    if len(raw_df.columns) < 5: # Pravděpodobně špatný oddělovač
                         raw_df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
                except:
                    raw_df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
            else:
                raw_df = pd.read_excel(uploaded_file)
            
            st.session_state.raw_data = raw_df
            st.session_state.processed_data = process_data(raw_df)
            st.session_state.file_id = file_id
            
    except Exception as e:
        st.sidebar.error(f"Chyba při načítání souboru: {e}")

# Filtrování pomocí slideru (Data nejsou ztracena, pouze se nad nimi vytvoří maska)
min_pieces_filter = 0
if st.session_state.processed_data is not None:
    max_pieces = int(st.session_state.processed_data.get('Number of pieces', [0]).max())
    min_pieces_filter = st.sidebar.slider(t['min_pieces'], 0, max_pieces, 0)

# -----------------------------------------------------------------------------
# 6. HLAVNÍ OBSAH APLIKACE (TABS)
# -----------------------------------------------------------------------------
st.title(t['title'])

if st.session_state.processed_data is None:
    st.info(t['no_data'])
else:
    # Získání dat z paměti a aplikace dynamického filtru
    df_all = st.session_state.processed_data
    df = df_all[df_all['Number of pieces'] >= min_pieces_filter].copy()

    # Vytvoření záložek (Tabs)
    tab_dash, tab_top, tab_audit, tab_export = st.tabs([
        t['tab_dash'], t['tab_top'], t['tab_audit'], t['tab_export']
    ])

    # --- ZÁLOŽKA 1: DASHBOARD ---
    with tab_dash:
        # Metriky (columns)
        m1, m2, m3, m4 = st.columns(4)
        total_orders = len(df)
        total_pieces = int(df.get('Number of pieces', pd.Series([0])).sum())
        avg_time = round(df.get('Process_Minutes', pd.Series([0])).mean(), 2)
        
        # Ošetření případu nulových minut pro efektivitu (vectorized sum)
        sum_mins = df.get('Process_Minutes', pd.Series([0])).sum()
        global_efficiency = round(total_pieces / sum_mins, 2) if sum_mins > 0 else 0

        m1.metric(label=t['metric_orders'], value=f"{total_orders:,}".replace(',', ' '))
        m2.metric(label=t['metric_pieces'], value=f"{total_pieces:,}".replace(',', ' '))
        m3.metric(label=t['metric_avg_time'], value=f"{avg_time} min")
        m4.metric(label=t['metric_efficiency'], value=f"{global_efficiency} ks/m")

        st.markdown("---")

        # Grafy
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader(t['chart_cust_vol'])
            if 'CUSTOMER' in df.columns:
                # Groupby jako nejefektivnější způsob agregace
                cust_vol = df.groupby('CUSTOMER', as_index=False)['Number of pieces'].sum()
                cust_vol = cust_vol.sort_values(by='Number of pieces', ascending=False).head(10)
                st.bar_chart(data=cust_vol, x='CUSTOMER', y='Number of pieces')
        
        with col_chart2:
            st.subheader("Objem zabalených kusů v čase")
            if 'DATE' in df.columns:
                date_vol = df.groupby('DATE', as_index=False)['Number of pieces'].sum()
                st.line_chart(data=date_vol, x='DATE', y='Number of pieces')

    # --- ZÁLOŽKA 2: TOP TABULKY ---
    with tab_top:
        t1, t2 = st.columns(2)
        
        with t1:
            st.subheader(t['top_longest'])
            # Použijeme zrychlené nlargest pro top N hodnot
            longest = df.nlargest(10, 'Process_Minutes')
            cols_to_show = ['DN NUMBER (SAP)', 'CUSTOMER', 'Process Time', 'Process_Minutes', 'Number of pieces']
            cols_available = [c for c in cols_to_show if c in longest.columns]
            st.dataframe(longest[cols_available], use_container_width=True)
            
        with t2:
            st.subheader(t['top_largest'])
            largest = df.nlargest(10, 'Number of pieces')
            cols_to_show_2 = ['DN NUMBER (SAP)', 'CUSTOMER', 'Number of pieces', 'Number of cartons', 'Efficiency_Pcs_Per_Min']
            cols_available_2 = [c for c in cols_to_show_2 if c in largest.columns]
            st.dataframe(largest[cols_available_2], use_container_width=True)

    # --- ZÁLOŽKA 3: TRANSPARENTNÍ AUDIT ---
    with tab_audit:
        st.info(t['audit_desc'])
        
        if len(df) > 0:
            # Vybíráme náhodných až 5 záznamů
            sample_size = min(5, len(df))
            sample_df = df.sample(sample_size, random_state=np.random.RandomState())
            
            # Efektivní iterace přes malé množství dat (zip over arrays je nejrychlejší pro Python smyčky)
            if 'DN NUMBER (SAP)' in sample_df.columns:
                dn_numbers = sample_df['DN NUMBER (SAP)'].values
                process_times = sample_df['Process Time'].values if 'Process Time' in sample_df.columns else ["N/A"] * sample_size
                pieces_arr = sample_df['Number of pieces'].values if 'Number of pieces' in sample_df.columns else [0] * sample_size
                minutes_arr = sample_df['Process_Minutes'].values
                eff_arr = sample_df['Efficiency_Pcs_Per_Min'].values
                
                for i, (dn, ptime, pcs, mins, eff) in enumerate(zip(dn_numbers, process_times, pieces_arr, minutes_arr, eff_arr)):
                    with st.expander(f"{t['audit_order']} {dn}"):
                        st.markdown(f"**{t['audit_step1']}**")
                        st.write(f"- Načtená data z Excelu/CSV: `Process Time` = **{ptime}**, `Počet kusů` = **{pcs}**")
                        
                        st.markdown(f"**{t['audit_step2']}**")
                        st.write(f"- Modul `pandas.to_timedelta` převedl čas na celkové vteřiny a vydělil 60.")
                        st.write(f"- Výsledek (uloženo v df['Process_Minutes']): **{mins:.2f} minut**")
                        
                        st.markdown(f"**{t['audit_step3']}**")
                        if mins > 0:
                            st.write(f"- Aplikována vektorizovaná funkce: `np.where(minuty > 0, kusy / minuty, 0)`")
                            st.write(f"- Výpočet: {pcs} / {mins:.2f} = **{eff:.2f} ks/min**")
                        else:
                            st.write(f"- Čas balení je 0 nebo chybí. Logika zamezila dělení nulou přes `np.where`.")
                            st.write(f"- Nastavena efektivita: **0 ks/min**")
            else:
                st.warning("Sloupec 'DN NUMBER (SAP)' nenalezen pro spuštění auditu.")

    # --- ZÁLOŽKA 4: EXPORT VÝSLEDKŮ ---
    with tab_export:
        st.write(t['export_desc'])
        
        # Funkce pro generování Excelu do paměti (bez uložení na disk)
        def generate_excel(dataframe: pd.DataFrame) -> bytes:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 1. List: Surová, ale obohacená data
                dataframe.to_excel(writer, sheet_name='Obohacena_Data', index=False)
                
                # 2. List: Agregovaný souhrn dle Zákazníka (Customer)
                if 'CUSTOMER' in dataframe.columns:
                    summary = dataframe.groupby('CUSTOMER').agg(
                        Celkem_Zakazek=('DN NUMBER (SAP)', 'count'),
                        Celkem_Kusu=('Number of pieces', 'sum'),
                        Prumerny_Cas_Min=('Process_Minutes', 'mean')
                    ).reset_index()
                    summary.to_excel(writer, sheet_name='Souhrn_Zakaznici', index=False)
                
                # 3. List: Metodika
                pd.DataFrame({
                    'Metrika': ['Process_Minutes', 'Efficiency_Pcs_Per_Min'],
                    'Popis': ['Čas balení převedený na desetinné minuty.', 'Počet kusů dělený Process_Minutes.']
                }).to_excel(writer, sheet_name='Metodika', index=False)
                
            processed_data = output.getvalue()
            return processed_data

        excel_data = generate_excel(df)
        
        # Tlačítko pro stažení
        st.download_button(
            label=t['btn_export'],
            data=excel_data,
            file_name="Analýza_Balení_Export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type='primary'
        )
