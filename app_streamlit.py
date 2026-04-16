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

import sys, os
# make sure local package directory is first on path; prevents older PyPI
# version from being imported when deployed to Streamlit Cloud.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import tempfile
import shutil

# Import the downloader class
from earthcare_downloader import EarthCareDownloader
from aux_data import aux_dict_L1, aux_dict_L2

# Page configuration
st.set_page_config(
    page_title="EarthCARE Data Downloader",
    page_icon="🌍",
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

# Title and description
st.markdown("# EarthCARE Data Downloader")
st.markdown("""
Download EarthCARE data products from OADS easily and quickly.
""")

# ============================================================================
# SIDEBAR - CREDENTIALS AND CONFIGURATION
# ============================================================================

st.sidebar.markdown("## 🔐 OADS Credentials")

username = st.sidebar.text_input(
    "OADS Username:",
    placeholder="Your OADS username",
    key="username"
)

password = st.sidebar.text_input(
    "OADS Password:",
    type="password",
    placeholder="Your OADS password",
    key="password"
)

# Collections
collections = {
    'EarthCARE L1 Products (Cal/Val Users)': 'EarthCAREL1InstChecked',
    'EarthCARE L1 Products (Validated)': 'EarthCAREL1Validated',
    'EarthCARE L2 Products (Cal/Val Users)': 'EarthCAREL2InstChecked',
    'EarthCARE L2 Products (Validated)': 'EarthCAREL2Validated',
    'EarthCARE L2 Products (Commissioning)': 'EarthCAREL2Products',
    'EarthCARE Auxiliary Data': 'EarthCAREAuxiliary',
    'EarthCARE Orbit Data': 'EarthCAREOrbitData',
    'JAXA L2 Products (Cal/Val Users)': 'JAXAL2InstChecked',
    'JAXA L2 Products (Validated)': 'JAXAL2Validated',
    'JAXA L2 Products (Commissioning)': 'JAXAL2Products'
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

# Baselines
baselines = ['Auto-detect', 'AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ',
            'BA', 'BB', 'BC', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ']

# Combine baseline dictionaries
all_baselines = {**aux_dict_L1, **aux_dict_L2}

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Configuration")

collection_name = st.sidebar.selectbox(
    "Collection:",
    list(collections.keys()),
    index=0,
    key="collection_select"
)
collection_id = collections[collection_name]

# ============================================================================
# MAIN CONTENT - TABS
# ============================================================================
tab1, tab2, tab3 = st.tabs(["Download", "Information", "FAQ"])

with tab1:
    # Create two columns for file upload
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### CSV File")
        uploaded_file = st.file_uploader(
            "Upload your CSV file with dates and times",
            type=['csv'],
            help="The file must contain columns with date and time. They will be detected automatically."
        )
        
        # Show preview if file is uploaded
        if uploaded_file is not None:
            try:
                df_preview = pd.read_csv(uploaded_file, nrows=5)
                st.info(f"File loaded: **{uploaded_file.name}**")
                st.markdown("**Preview (first 5 rows):**")
                st.dataframe(df_preview, use_container_width=True)
                
                # Get all column names for orbit selection
                csv_columns = df_preview.columns.tolist()
            except Exception as e:
                st.error(f"❌ Error reading file: {e}")
                csv_columns = []
    
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
        
        # Get available baselines for this product
        available_baselines = ['Auto-detect']
        if selected_product in all_baselines:
            available_baselines.extend(all_baselines[selected_product])
        
        baseline = st.selectbox(
            "Baseline:",
            available_baselines,
            key="baseline_select",
            help="Auto-detect will automatically select the most common baseline"
        )
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col_adv1, col_adv2 = st.columns(2)
        
        with col_adv1:
            if uploaded_file is not None and csv_columns:
                orbit_column = st.selectbox(
                    "Orbit Number Column:",
                    ['None'] + csv_columns,
                    help="Select if your CSV contains orbit information"
                )
                if orbit_column == 'None':
                    orbit_column = None
            else:
                orbit_column = None
                st.info("Upload a CSV file to see available columns")
            
            override_files = st.checkbox(
                "Override existing files",
                value=False,
                help="If enabled, will download files again even if they already exist"
            )
        
        with col_adv2:
            verbose_mode = st.checkbox(
                "Verbose output",
                value=False,
                help="Shows detailed information during processing"
            )
            
            st.markdown("**Download Information:**")
            st.info(f"""
            📥 Files will be downloaded to a temporary folder.
            You can download all files as ZIP after completion.
            """)
    
    # Validation and download button
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        if st.button("START DOWNLOAD", type="primary", use_container_width=True):
            # Validate inputs
            errors = []
            
            if not username.strip():
                errors.append("❌ OADS username required")
            if not password.strip():
                errors.append("❌ OADS password required")
            if uploaded_file is None:
                errors.append("❌ CSV file required")
            
            if errors:
                st.error("\n".join(errors))
            else:
                # Create a placeholder for logs
                log_container = st.container(border=True)
                status_placeholder = log_container.status("Initializing download...", expanded=True)
                log_placeholder = status_placeholder.empty()
                
                # Add progress indicator
                progress_col = st.columns(1)[0]
                with progress_col:
                    st.markdown("**Download Progress**")
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                # stop flag
                if 'cancel' not in st.session_state:
                    st.session_state.cancel = False
                if st.button("⏹️ Stop download", key="stop_button"):
                    st.session_state.cancel = True

                def stop_check():
                    return st.session_state.get('cancel', False)
                
                logs = []
                
                try:
                    with status_placeholder:
                        # Save uploaded file to temporary location
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # Save CSV temp file
                            csv_temp_path = os.path.join(temp_dir, uploaded_file.name)
                            with open(csv_temp_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())
                            
                            # Create download directory
                            download_dir = os.path.join(temp_dir, 'downloads')
                            os.makedirs(download_dir, exist_ok=True)
                            
                            # Create downloader instance
                            logs.append(f"Connecting as: {username}")
                            
                            baseline_filter = baseline if baseline != 'Auto-detect' else None
                            
                            downloader = EarthCareDownloader(
                                username=username.strip(),
                                password=password.strip(),
                                collection=collection_id,
                                baseline=baseline_filter,
                                verbose=verbose_mode
                            )
                    
                            logs.append(f"Collection: {collection_id}")
                            logs.append(f"Product: {selected_product} | Baseline: {baseline}")
                            
                            # Update log display
                            with log_placeholder.container():
                                for log in logs:
                                    st.write(log)
                            
                            # Read CSV to count entries
                            try:
                                df_check = pd.read_csv(csv_temp_path)
                                total_entries = len(df_check)
                            except:
                                total_entries = 1
                            
                            # Progress tracker used by the downloader callback
                            class ProgressTracker:
                                def __init__(self):
                                    self.processed = 0
                                    self.downloaded = 0
                                    self.total = total_entries
                                
                                def update(self, processed, downloaded):
                                    # called by download_from_csv for every file and entry
                                    self.processed = processed
                                    self.downloaded = downloaded
                                    
                                    if self.total > 0:
                                        # Calculate percentage based on downloaded files
                                        files_pct = min(int((self.downloaded / self.total) * 100), 100)
                                        progress_bar.progress(files_pct / 100.0)
                                        progress_text.markdown(f"{files_pct}% - {self.downloaded}/{self.total} files")
                                    if stop_check():
                                        progress_text.markdown("Cancelled")
                            
                            tracker = ProgressTracker()
                            
                            # Update progress
                            progress_bar.progress(0)
                            progress_text.markdown("0% - Connecting to OADS...")
                            
                            summary = downloader.download_from_csv(
                                csv_file_path=csv_temp_path,
                                products=[selected_product],
                                download_directory=download_dir,
                                orbit_column=orbit_column,
                                override=override_files,
                                progress_callback=tracker.update,
                                stop_callback=stop_check
                            )
                            
                            # Update final progress
                            if stop_check():
                                progress_text.markdown(f"⚠️ Cancelled at {len(summary['downloaded_files'])}/{total_entries} files")
                                status_placeholder.update(label="⚠️ Download cancelled", state="warning")
                            else:
                                progress_bar.progress(1.0)
                                progress_text.markdown(f"✅ 100% - {len(summary['downloaded_files'])}/{total_entries} files")
                                logs.append(f"🎉 Download completed!")
                            
                            # Update log display
                            with log_placeholder.container():
                                for log in logs:
                                    st.write(log)
                            
                            status_placeholder.update(label="✅ Download completed", state="complete")
                            
                            # Show download button if files were downloaded
                            if os.listdir(download_dir):
                                st.markdown("---")
                                
                                # Create ZIP file
                                zip_path = os.path.join(temp_dir, 'earthcare_downloads.zip')
                                shutil.make_archive(
                                    zip_path.replace('.zip', ''),
                                    'zip',
                                    download_dir
                                )
                                
                                with open(zip_path, 'rb') as f:
                                    st.download_button(
                                        label="📥 Download Files (ZIP)",
                                        data=f.read(),
                                        file_name=f"earthcare_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                        mime="application/zip",
                                        use_container_width=True
                                    )
                                
                                # Show summary table
                                st.markdown("### Detailed Summary")
                                
                                summary_data = {
                                    'Metric': ['Entries processed', 'Files downloaded', 'Files skipped', 'Files failed', 'Total time'],
                                    'Value': [
                                        f"{summary['processed_entries']}/{summary['total_entries']}",
                                        len(summary['downloaded_files']),
                                        len(summary['skipped_files']),
                                        len(summary['failed_files']),
                                        summary['execution_time']
                                    ]
                                }
                                st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
                            else:
                                st.warning("⚠️ No files were downloaded. Check your search parameters.")
                
                except Exception as e:
                    status_placeholder.update(label="❌ Download error", state="error")
                    progress_bar.progress(0)
                    progress_text.markdown("❌ Download failed")
                    
                    logs.append(f"❌ Error: {str(e)}")
                    
                    with log_placeholder.container():
                        for log in logs:
                            st.write(log)
                    
                    st.error(f"**Error during download:**\n\n{str(e)}")

with tab2:
    st.markdown("""
    ### 📋 General Information
    
    **EarthCARE Data Downloader** allows you to easily download EarthCARE data products
    from the OADS catalog (ESA Open Access Data Service) automatically.
    
    ### Features
    
    - **Automatic downloads** from OADS
    - **Automatic detection** of CSV files (separator, date, time)
    - **Multiple collections** available
    - **Baseline filtering**
    - **Override option** for existing files
    - **ZIP download** of all files
    
    ### User Guide
    
    1. **Credentials**: Enter your OADS username and password
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
    
    - [OADS Portal](https://eocat.esa.int/)
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
    - OADS credentials
    - Your CSV file
    - Internet connection
    
    #### How long does a download take?
    It depends on:
    - Number of entries in your CSV
    - Product availability
    - File sizes
    
    Typically takes between minutes to hours.
    
    #### Where can I get OADS credentials?
    Register at [OADS](https://eocat.esa.int/) with your ESA account.
    
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
    - Only sent to OADS for authentication
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
