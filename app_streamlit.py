#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filename: app_streamlit.py
Author: Onrona Functions
Created: 2025-11-20
Version: 1.0
Description:
    Streamlit web application for EarthCARE Data Downloader.
    Allows users to download EarthCARE products through a modern web interface.
"""

import sys
import os
import csv
import io
import shutil
import tempfile
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path

# make sure local package directory is first on path; prevents older PyPI
# version from being imported when deployed to Streamlit Cloud.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
import streamlit as st

# Import the MAAP downloader classes
from maap_earthcare_downloader import CredentialsToken, MAAPEarthCAREDownloader

# Page configuration
st.set_page_config(
    page_title="EarthCARE MAAP Downloader",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark mode CSS - Professional styling inspired by modern web design
dark_css = """
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    :root {
        --primary-dark: #0f1419;
        --secondary-dark: #1a2332;
        --tertiary-dark: #252d3d;
        --accent-blue: #00b4d8;
        --accent-purple: #7209b7;
        --accent-pink: #f72585;
        --text-primary: #e0e7ff;
        --text-secondary: #a0aec0;
        --border-color: #2d3748;
    }
    
    body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%) !important;
        color: var(--text-primary) !important;
    }
    
    [data-testid="stMainBlockContainer"] {
        background-color: transparent !important;
        color: var(--text-primary) !important;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2332 0%, #252d3d 100%) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    
    [data-testid="stSidebarContent"] {
        background: transparent !important;
    }
    
    .stMarkdown {
        color: var(--text-primary) !important;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #00d9ff !important;
        text-shadow: 0 0 10px rgba(0, 217, 255, 0.3) !important;
    }
    
    .stMarkdown p {
        color: var(--text-primary) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 2px solid var(--border-color) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button {
        background-color: transparent !important;
        color: var(--text-secondary) !important;
        border: none !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #00d9ff !important;
        border-bottom: 3px solid #00d9ff !important;
        background: rgba(0, 217, 255, 0.1) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1em;
        font-weight: bold;
        color: inherit !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    textarea {
        background-color: #252d3d !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    textarea:focus {
        border-color: #00d9ff !important;
        box-shadow: 0 0 10px rgba(0, 217, 255, 0.2) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00b4d8 0%, #00d9ff 100%) !important;
        color: #0f1419 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        padding: 12px 24px !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 30px rgba(0, 217, 255, 0.3) !important;
    }
    
    /* Containers and expanders */
    [data-testid="stExpander"] {
        background-color: #1a2332 !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stExpander"] > div > button {
        background-color: transparent !important;
        color: var(--text-primary) !important;
    }
    
    [data-testid="stExpander"] > div > button:hover {
        background-color: rgba(0, 217, 255, 0.1) !important;
    }
    
    /* Info/Error/Warning messages */
    .stInfo, [data-testid="stStatusWidget"] {
        background-color: rgba(0, 180, 216, 0.15) !important;
        border-left: 4px solid #00d9ff !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }
    
    .stWarning, [data-testid="stWarning"] {
        background-color: rgba(255, 184, 28, 0.15) !important;
        border-left: 4px solid #ffb81c !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }
    
    .stError, [data-testid="stError"] {
        background-color: rgba(247, 37, 133, 0.15) !important;
        border-left: 4px solid #f72585 !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }
    
    .stSuccess, [data-testid="stSuccess"] {
        background-color: rgba(0, 217, 255, 0.15) !important;
        border-left: 4px solid #00d9ff !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }
    
    /* Data frames */
    [data-testid="dataframeContainer"] {
        background-color: #1a2332 !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0f1419;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00d9ff;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .stMarkdown h1 {
            font-size: 1.8em !important;
        }
    }
</style>
"""

st.markdown(dark_css, unsafe_allow_html=True)


def parse_credentials_text(file_text: str) -> dict[str, str]:
    """Parse a credentials file with KEY=VALUE lines."""
    credentials = {}
    for raw_line in file_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        credentials[key.strip()] = value.strip()
    return credentials


def detect_csv_delimiter(file_bytes: bytes) -> str | None:
    """Best-effort delimiter detection for uploaded CSV files."""
    sample = file_bytes[:4096].decode("utf-8", errors="ignore")
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return None


def auto_detect_columns(columns: list[str]) -> tuple[str | None, str | None]:
    """Guess date and time columns from common names."""
    normalized = {col: col.strip().lower() for col in columns}

    date_keywords = ["date", "fecha", "day", "yyyy-mm-dd"]
    time_keywords = ["time", "hora", "hh:mm", "utc"]

    detected_date = next(
        (col for col, lower in normalized.items() if any(key in lower for key in date_keywords)),
        columns[0] if columns else None,
    )
    detected_time = next(
        (col for col, lower in normalized.items() if any(key in lower for key in time_keywords)),
        None,
    )
    return detected_date, detected_time


def format_date_hour(selected_date: date, selected_time: dt_time) -> str:
    """Return a date-hour string accepted by the downloader."""
    return f"{selected_date.isoformat()} {selected_time.strftime('%H:%M:%S')}"


def split_date_hour_text(raw_text: str) -> list[str]:
    """Split a text area with comma/newline/semicolon separated date-hour values."""
    if not raw_text:
        return []
    normalized = raw_text.replace(";", "\n").replace(",", "\n")
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def unique_preserving_order(values: list[str]) -> list[str]:
    """Remove duplicates while keeping the user-entered order."""
    seen = set()
    cleaned = []
    for value in values:
        if value not in seen:
            cleaned.append(value)
            seen.add(value)
    return cleaned


def parse_time_list(raw_text: str) -> tuple[list[dt_time], list[str]]:
    """Parse HH:MM style time values for range generation."""
    values = split_date_hour_text(raw_text)
    parsed = []
    invalid = []

    for value in values:
        parsed_time = None
        for fmt in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
            try:
                parsed_time = datetime.strptime(value, fmt).time()
                break
            except ValueError:
                continue

        if parsed_time is None:
            invalid.append(value)
        else:
            parsed.append(parsed_time)

    return parsed, invalid


def build_range_targets(
    selected_range: date | tuple[date, ...],
    times_for_each_day: list[dt_time],
) -> list[str]:
    """Build one target per selected date and time in the inclusive date range."""
    if isinstance(selected_range, tuple):
        if len(selected_range) == 0:
            return []
        start_date = selected_range[0]
        end_date = selected_range[-1]
    else:
        start_date = selected_range
        end_date = selected_range

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    targets = []
    current_date = start_date
    while current_date <= end_date:
        for selected_time in times_for_each_day:
            targets.append(format_date_hour(current_date, selected_time))
        current_date += timedelta(days=1)

    return targets


# Title and description
st.markdown("# EarthCARE MAAP Downloader")
st.markdown("""
Download EarthCARE data products from the ESA MAAP catalog through a Streamlit interface.
""")

# ============================================================================
# SIDEBAR - CREDENTIALS AND CONFIGURATION
# ============================================================================

st.sidebar.markdown("## 🔐 MAAP Credentials")
st.sidebar.caption("Upload a credentials file or enter the values manually.")

uploaded_credentials_file = st.sidebar.file_uploader(
    "Upload credentials file:",
    type=["txt"],
    help="Expected keys: OFFLINE_TOKEN, CLIENT_ID, CLIENT_SECRET"
)

if uploaded_credentials_file is not None:
    try:
        uploaded_credentials_text = uploaded_credentials_file.getvalue().decode("utf-8")
        uploaded_credentials = parse_credentials_text(uploaded_credentials_text)
        current_signature = (
            uploaded_credentials_file.name,
            len(uploaded_credentials_text),
        )

        if st.session_state.get("credentials_file_signature") != current_signature:
            field_mapping = {
                "offline_token": "OFFLINE_TOKEN",
                "client_id": "CLIENT_ID",
                "client_secret": "CLIENT_SECRET",
            }
            loaded_count = 0
            for state_key, credential_key in field_mapping.items():
                if uploaded_credentials.get(credential_key):
                    st.session_state[state_key] = uploaded_credentials[credential_key]
                    loaded_count += 1

            st.session_state["credentials_file_signature"] = current_signature

            if loaded_count == 3:
                st.sidebar.success("Credentials file loaded successfully.")
            elif loaded_count > 0:
                st.sidebar.warning("The file was loaded, but some credential keys are missing.")
            else:
                st.sidebar.error("No valid credential entries were found in the uploaded file.")
    except Exception as exc:
        st.sidebar.error(f"Could not read the credentials file: {exc}")

offline_token = st.sidebar.text_input(
    "Offline Token:",
    type="password",
    placeholder="Paste your MAAP offline token",
    key="offline_token"
)

client_id = st.sidebar.text_input(
    "Client ID:",
    placeholder="Your MAAP client ID",
    key="client_id"
)

client_secret = st.sidebar.text_input(
    "Client Secret:",
    type="password",
    placeholder="Your MAAP client secret",
    key="client_secret"
)

st.sidebar.caption("Credentials are only used during the current session.")

# Collections
collections = {
    'Auto-detect from catalog': None,
    'EarthCARE L1 Products (Cal/Val Users)': 'EarthCAREL1InstChecked_MAAP',
    'EarthCARE L1 Products (Validated)': 'EarthCAREL1Validated_MAAP',
    'EarthCARE L2 Products (Cal/Val Users)': 'EarthCAREL2InstChecked_MAAP',
    'EarthCARE L2 Products (Validated)': 'EarthCAREL2Validated_MAAP',
    'EarthCARE L2 Products (Commissioning)': 'EarthCAREL2Products_MAAP',
    'EarthCARE Auxiliary Data': 'EarthCAREAuxiliary_MAAP',
    'EarthCARE Orbit Data': 'EarthCAREOrbitData_MAAP',
    'JAXA L2 Products (Cal/Val Users)': 'JAXAL2InstChecked_MAAP',
    'JAXA L2 Products (Validated)': 'JAXAL2Validated_MAAP',
    'JAXA L2 Products (Commissioning)': 'JAXAL2Products_MAAP'
}

# Product categories
product_categories = {
    'ATLID Level 1B': ['ATL_NOM_1B', 'ATL_DCC_1B', 'ATL_CSC_1B', 'ATL_FSC_1B'],
    'MSI Level 1B': ['MSI_NOM_1B', 'MSI_BBS_1B', 'MSI_SD1_1B', 'MSI_SD2_1B'],
    'BBR Level 1B': ['BBR_NOM_1B', 'BBR_SNG_1B', 'BBR_SOL_1B', 'BBR_LIN_1B'],
    'CPR Level 1B': ['CPR_NOM_1B'],
    'MSI Level 1C': ['MSI_RGR_1C'],
    'Auxiliary Level 1D': ['AUX_MET_1D', 'AUX_JSG_1D'],
    'ATLID Level 2A': ['ATL_FM__2A', 'ATL_AER_2A', 'ATL_ICE_2A', 'ATL_TC__2A', 
                      'ATL_EBD_2A', 'ATL_CTH_2A', 'ATL_ALD_2A'],
    'MSI Level 2A': ['MSI_CM__2A', 'MSI_COP_2A', 'MSI_AOT_2A'],
    'CPR Level 2A': ['CPR_FMR_2A', 'CPR_CD__2A', 'CPR_TC__2A', 'CPR_CLD_2A', 'CPR_APC_2A'],
    'Level 2B Combined': ['AM__MO__2B', 'AM__CTH_2B', 'AM__ACD_2B', 'AC__TC__2B',
                         'BM__RAD_2B', 'BMA_FLX_2B', 'ACM_CAP_2B', 'ACM_COM_2B',
                         'ACM_RT__2B', 'ALL_DF__2B', 'ALL_3D__2B'],
    'Orbit Data': ['MPL_ORBSCT', 'AUX_ORBPRE', 'AUX_ORBRES']
}

# Frames / baselines available in the MAAP catalog
baselines = ['AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ',
             'BA', 'BB', 'BC', 'BD']

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Configuration")

collection_name = st.sidebar.selectbox(
    "Collection:",
    list(collections.keys()),
    index=0,
    key="collection_select"
)
collection_id = collections[collection_name]

baseline_options = ["Manual entry", "No baseline / code default"] + baselines
baseline_mode = st.sidebar.selectbox(
    "Frame / Baseline:",
    baseline_options,
    index=0,
    key="baseline_mode_select",
    help="Write a custom frame, choose a known frame, or leave it empty so the downloader does not filter by version."
)

if baseline_mode == "Manual entry":
    baseline_manual = st.sidebar.text_input(
        "Custom baseline:",
        value=st.session_state.get("baseline_manual_value", "BA"),
        key="baseline_manual_value",
        help="Example: BA. Leave empty to let the downloader search without a version filter."
    ).strip()
    baseline = baseline_manual.upper() if baseline_manual else None
elif baseline_mode == "No baseline / code default":
    baseline = None
else:
    baseline = baseline_mode

if baseline is None:
    st.sidebar.caption("Baseline: none selected. The downloader will use its default/no-version search behavior.")
else:
    st.sidebar.caption(f"Baseline in use: {baseline}")

# ============================================================================
# MAIN CONTENT - TABS
# ============================================================================
tab1, tab2, tab3 = st.tabs(["Download", "Information", "FAQ"])

with tab1:
    # Create two columns for file upload
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Date-Time Targets")
        input_method = st.radio(
            "Choose how to define the date-times to download:",
            ["CSV file", "Calendar range", "Manual date-times"],
            horizontal=True,
            key="date_input_method"
        )

        uploaded_file = None
        range_targets = []
        manual_targets = []

        if input_method == "CSV file":
            uploaded_file = st.file_uploader(
                "Upload your CSV file with dates and times",
                type=['csv'],
                help="The file must contain columns with date and time. They will be detected automatically."
            )

            # Show preview if file is uploaded
            if uploaded_file is not None:
                try:
                    uploaded_bytes = uploaded_file.getvalue()
                    preview_delimiter = detect_csv_delimiter(uploaded_bytes)
                    df_preview = pd.read_csv(
                        io.BytesIO(uploaded_bytes),
                        nrows=5,
                        sep=preview_delimiter or None,
                        engine="python"
                    )
                    st.info(f"File loaded: **{uploaded_file.name}**")
                    st.markdown("**Preview (first 5 rows):**")
                    st.dataframe(df_preview, width='stretch')

                    csv_columns = df_preview.columns.tolist()
                except Exception as e:
                    st.error(f"❌ Error reading file: {e}")
                    csv_columns = []
        elif input_method == "Calendar range":
            selected_date_range = st.date_input(
                "Date range:",
                value=(date.today(), date.today()),
                help="The range is inclusive. One target will be generated for each selected time of each day."
            )
            range_times_text = st.text_area(
                "Times for each day (UTC):",
                value="00:00:00",
                height=90,
                help="Enter one or more times as HH:MM, HH:MM:SS, or HH:MM:SS.sss. Use one per line or comma-separated."
            )
            parsed_times, invalid_times = parse_time_list(range_times_text)
            if invalid_times:
                st.warning(f"These times could not be parsed and will be ignored: {', '.join(invalid_times)}")
            range_targets = build_range_targets(selected_date_range, parsed_times)

            if range_targets:
                st.markdown("**Generated target date-times:**")
                st.dataframe(pd.DataFrame({"date_hour": range_targets}), width='stretch', hide_index=True)
            else:
                st.info("Select a valid date range and at least one time.")
        else:
            if "manual_date_targets" not in st.session_state:
                st.session_state["manual_date_targets"] = []

            manual_col1, manual_col2 = st.columns(2)
            with manual_col1:
                manual_date = st.date_input("Date:", value=date.today(), key="manual_date_picker")
            with manual_col2:
                manual_time = st.time_input("Time (UTC):", value=dt_time(0, 0, 0), key="manual_time_picker")

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if st.button("Add date-time", width='stretch'):
                    new_target = format_date_hour(manual_date, manual_time)
                    st.session_state["manual_date_targets"] = unique_preserving_order(
                        st.session_state["manual_date_targets"] + [new_target]
                    )
            with action_col2:
                if st.button("Clear manual list", width='stretch'):
                    st.session_state["manual_date_targets"] = []

            manual_text = st.text_area(
                "Manual target list:",
                value="\n".join(st.session_state["manual_date_targets"]),
                height=160,
                help="You can edit this list directly. Accepted formats are the same as the CSV-derived values."
            )
            manual_targets = unique_preserving_order(split_date_hour_text(manual_text))
            st.session_state["manual_date_targets"] = manual_targets

            if manual_targets:
                st.dataframe(pd.DataFrame({"date_hour": manual_targets}), width='stretch', hide_index=True)
    
    with col2:
        st.markdown("### Product Selection")
        
        category = st.selectbox(
            "Product Category:",
            list(product_categories.keys()),
            key="category_select"
        )
        
        products_in_category = product_categories.get(category, [])
        selected_product = st.selectbox(
            "Product:",
            products_in_category,
            key="product_select"
        )

        # st.info(
        #     f"Baseline: **{baseline if baseline else 'None / code default'}**. "
        #     "Change it from the sidebar."
        # )
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col_adv1, col_adv2 = st.columns(2)

        if uploaded_file is not None:
            current_bytes = uploaded_file.getvalue()
            detected_delimiter = detect_csv_delimiter(current_bytes)
            try:
                csv_preview = pd.read_csv(
                    io.BytesIO(current_bytes),
                    nrows=5,
                    sep=detected_delimiter or None,
                    engine="python"
                )
                csv_columns = csv_preview.columns.tolist()
            except Exception:
                csv_columns = []
        else:
            csv_columns = []
            detected_delimiter = None

        detected_date_col, detected_time_col = auto_detect_columns(csv_columns)

        with col_adv1:
            if csv_columns:
                date_index = csv_columns.index(detected_date_col) if detected_date_col in csv_columns else 0
                date_column = st.selectbox(
                    "Date column:",
                    csv_columns,
                    index=date_index,
                    help="Column containing the date or full datetime"
                )

                time_options = ['None'] + csv_columns
                time_index = time_options.index(detected_time_col) if detected_time_col in time_options else 0
                time_column = st.selectbox(
                    "Time column (optional):",
                    time_options,
                    index=time_index,
                    help="Optional column containing the time component"
                )
                if time_column == 'None':
                    time_column = None
            else:
                date_column = None
                time_column = None
                st.info("Upload a CSV file to select the date and time columns")

            override_files = st.checkbox(
                "Override existing files",
                value=False,
                help="If enabled, files will be downloaded again even if they already exist"
            )

        with col_adv2:
            delimiter_options = {
                'Auto-detect': None,
                'Comma (,)': ',',
                'Semicolon (;)': ';',
                'Tab': '\t',
                'Pipe (|)': '|'
            }
            delimiter_labels = list(delimiter_options.keys())
            default_delimiter_label = next(
                (label for label, value in delimiter_options.items() if value == detected_delimiter),
                'Auto-detect'
            )
            csv_delimiter_label = st.selectbox(
                "CSV separator:",
                delimiter_labels,
                index=delimiter_labels.index(default_delimiter_label)
            )
            csv_delimiter = delimiter_options[csv_delimiter_label]

            search_minutes = st.slider(
                "Search window (minutes):",
                min_value=3,
                max_value=30,
                value=6,
                help="Time window around each target date to search in the MAAP catalog"
            )

            st.markdown("**Download Information:**")
            st.info("""
            📥 Files will be downloaded to a temporary folder.
            After completion, you can download all retrieved files as a ZIP archive.
            """)
    
    # Validation and download button
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        if st.button("START DOWNLOAD", type="primary", width='stretch'):
            errors = []

            if not offline_token.strip():
                errors.append("❌ MAAP offline token required")
            if not client_id.strip():
                errors.append("❌ Client ID required")
            if not client_secret.strip():
                errors.append("❌ Client secret required")
            if uploaded_file is None and not range_targets and not manual_targets:
                errors.append("❌ CSV file or target dates required")
            if uploaded_file is not None and not date_column:
                errors.append("❌ Select a valid date column")

            if errors:
                st.error("\n".join(errors))
            else:
                log_container = st.container(border=True)
                status_placeholder = log_container.status("Initializing MAAP download...", expanded=True)
                log_placeholder = status_placeholder.empty()

                progress_col = st.columns(1)[0]
                with progress_col:
                    st.markdown("**Download Progress**")
                    progress_bar = st.progress(0)
                    progress_text = st.empty()

                logs = []
                started_at = datetime.now()

                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        credentials_path = os.path.join(temp_dir, 'credentials.txt')
                        with open(credentials_path, 'w', encoding='utf-8') as f:
                            f.write(f"OFFLINE_TOKEN={offline_token.strip()}\n")
                            f.write(f"CLIENT_ID={client_id.strip()}\n")
                            f.write(f"CLIENT_SECRET={client_secret.strip()}\n")

                        download_dir = os.path.join(temp_dir, 'downloads')
                        os.makedirs(download_dir, exist_ok=True)

                        logs.append("Authenticating with MAAP...")
                        credentials = CredentialsToken(credentials_file=Path(credentials_path))
                        downloader = MAAPEarthCAREDownloader(credentials_token=credentials)

                        logs.append(f"Collection: {collection_name}")
                        logs.append(f"Product: {selected_product} | Frame: {baseline}")

                        if uploaded_file is not None:
                            csv_temp_path = os.path.join(temp_dir, uploaded_file.name)
                            with open(csv_temp_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())

                            targets = downloader.load_date_hours(
                                input_mode="csv",
                                csv_path=csv_temp_path,
                                date_column=date_column,
                                time_column=time_column,
                                csv_delimiter=csv_delimiter,
                            )
                        elif len(range_targets) > 0:
                            targets = downloader.load_date_hours(
                                input_mode="list",
                                date_hours=range_targets
                            )
                        else:
                            targets = downloader.load_date_hours(
                                input_mode="list",
                                date_hours=manual_targets
                            )
                        
                        
                        total_entries = len(targets)
                        results = {
                            "downloaded": [],
                            "not_found": [],
                            "errors": [],
                            "skipped": [],
                        }

                        for idx, date_hour in enumerate(targets, start=1):
                            print(date_hour, type(date_hour))
                            progress_bar.progress((idx - 1) / max(total_entries, 1))
                            progress_text.markdown(f"Processing {idx}/{total_entries}: {date_hour}")

                            try:
                                product = downloader.find_product_by_time(
                                    product_type=selected_product,
                                    frame=baseline,
                                    target_time=date_hour,
                                    collection=collection_id,
                                    search_minutes=search_minutes,
                                )

                                if not product:
                                    logs.append(f"⚠️ No file found for {date_hour}")
                                    results["not_found"].append({"date_hour": date_hour})
                                else:
                                    output_file = Path(download_dir) / f"{product['name']}.h5"
                                    if output_file.exists() and not override_files:
                                        logs.append(f"⏭️ Skipped existing file: {product['name']}")
                                        results["skipped"].append(
                                            {
                                                "date_hour": date_hour,
                                                "name": product["name"],
                                                "output": str(output_file),
                                            }
                                        )
                                    else:
                                        downloader.download_product(product["url"], output_file)
                                        logs.append(f"✅ Downloaded: {product['name']}")
                                        results["downloaded"].append(
                                            {
                                                "date_hour": date_hour,
                                                "name": product["name"],
                                                "output": str(output_file),
                                            }
                                        )
                            except Exception as exc:
                                logs.append(f"❌ Error for {date_hour}: {exc}")
                                results["errors"].append({"date_hour": date_hour, "error": str(exc)})

                            with log_placeholder.container():
                                for log in logs[-12:]:
                                    st.write(log)

                        progress_bar.progress(1.0)
                        progress_text.markdown(
                            f"✅ 100% - {len(results['downloaded'])}/{total_entries} files downloaded"
                        )

                        elapsed = str(datetime.now() - started_at).split('.')[0]

                        if results["errors"]:
                            status_placeholder.update(label="⚠️ Download finished with some errors", state="warning")
                        else:
                            status_placeholder.update(label="✅ Download completed", state="complete")

                        if os.listdir(download_dir):
                            st.markdown("---")

                            zip_path = os.path.join(temp_dir, 'earthcare_downloads.zip')
                            shutil.make_archive(zip_path.replace('.zip', ''), 'zip', download_dir)

                            with open(zip_path, 'rb') as f:
                                st.download_button(
                                    label="📥 Download Files (ZIP)",
                                    data=f.read(),
                                    file_name=f"earthcare_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                    mime="application/zip",
                                    width='stretch'
                                )

                            st.markdown("### Detailed Summary")

                            summary_data = {
                                'Metric': [
                                    'Entries processed',
                                    'Files downloaded',
                                    'Files not found',
                                    'Files skipped',
                                    'Files with errors',
                                    'Total time'
                                ],
                                'Value': [
                                    total_entries,
                                    len(results['downloaded']),
                                    len(results['not_found']),
                                    len(results['skipped']),
                                    len(results['errors']),
                                    elapsed
                                ]
                            }
                            st.dataframe(pd.DataFrame(summary_data), width='stretch', hide_index=True)
                        else:
                            status_placeholder.update(label="⚠️ No files were downloaded", state="warning")
                            st.warning("⚠️ No files were downloaded. Check your CSV values, frame, and collection.")

                except Exception as e:
                    status_placeholder.update(label="❌ Download error", state="error")
                    progress_bar.progress(0)
                    progress_text.markdown("❌ Download failed")

                    logs.append(f"❌ Error: {str(e)}")

                    with log_placeholder.container():
                        for log in logs[-12:]:
                            st.write(log)

                    st.error(f"**Error during download:**\n\n{str(e)}")

with tab2:
    st.markdown("""
    ### 📋 General Information
    
    **EarthCARE MAAP Downloader** allows you to easily download EarthCARE data products
    from the ESA MAAP catalog automatically.
    
    ### Features
    
    - **Automatic downloads** from the MAAP catalog
    - **Automatic detection** of CSV files (separator, date, time)
    - **Multiple collections** available
    - **Baseline filtering**
    - **Override option** for existing files
    - **ZIP download** of all files
    
    ### User Guide
    
    1. **Credentials**: Enter your MAAP offline token, client ID, and client secret
    2. **CSV File**: Upload your file with dates and times
    3. **Product**: Select the category and specific product
    4. **Start**: Click "Start Download"
    5. **Results**: Download files as ZIP
    
    ### CSV File Requirements
    
    Your CSV file must contain:
    - A **date** column (format: yyyy-mm-dd)
    - A **time** column (format: hh:mm:ss.sss)
    
    The system will automatically detect these columns by looking for:
    - Names like: "date", "fecha", "day", etc.
    - Names like: "time", "hora", "hh:mm:ss.sss", etc.
    
    Example of valid CSV:
    ```
    date,time,extra
    2024-01-15,12:30:45.123,data
    2024-01-16,14:15:30.456,data
    ```
    
    ### 🔗 Useful Links
    
    - [ESA MAAP Portal](https://catalog.maap.eo.esa.int/)
    - [EarthCARE Mission](https://www.esa.int/Applications/Observing_the_Earth/EarthCARE)
    - [EarthCARE Documentation](https://www.esa.int/Applications/Observing_the_Earth/EarthCARE)
    """)

with tab3:
    st.markdown("""
    ### Frequently Asked Questions
    
    #### What are the CSV file requirements?
    The file must have:
    - A date column in YYYY-MM-DD format
    - A time column in HH:MM:SS.SSS format
    - Any separator (comma, semicolon, tab) is automatically detected
    
    #### Do I need to install anything?
    No, everything works in the browser. You only need:
    - MAAP credentials
    - Your CSV file
    - Internet connection
    
    #### How long does a download take?
    It depends on:
    - Number of entries in your CSV
    - Product availability
    - File sizes
    
    Typically takes between minutes to hours.
    
    #### Where can I get MAAP credentials?
    Use your ESA MAAP account and generate the required token and client credentials.
    
    #### What if a download fails?
    - Verify your credentials
    - Check your CSV format
    - Try with a single product
    - Check your internet connection
    
    #### Can I download multiple products?
    Currently one at a time. If you need multiple:
    - Run the app several times with different products
    - Or use the desktop application
    
    #### What happens to my password?
    - Only used to authenticate against MAAP
    - Not stored on the server
    - Session is anonymous
    
    #### Is there a download limit?
    Depends on your OADS account. Check their terms of service.
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #a0aec0; font-size: 0.85em;'>
    <p>EarthCARE Data Downloader • Powered by <a href='https://streamlit.io/' style='color: #00d9ff;'>Streamlit</a></p>
    <p>For issues or suggestions, contact the development team.</p>
</div>
""", unsafe_allow_html=True)
