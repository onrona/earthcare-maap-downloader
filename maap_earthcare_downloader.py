
######################################################################################################
#%%
import csv
import logging
import re
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Iterable
from dateutil import parser as dateutil_parser
import requests

try:
    from tqdm import tqdm  # type: ignore[import-not-found]
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

######################################################################################################

# --- Path to credentials.txt --- 
CREDENTIALS_FILE = Path("/media/onel/D/repositories/earthcare-data-downloader/platform_change_to_maap/credentials.txt")   # Insert the .txt path

# --- Constants ---
BASE_DATA_URL = "https://catalog.maap.eo.esa.int/data/earthcare-pdgs-01/EarthCARE/"

CATALOG_URL = "https://catalog.maap.eo.esa.int/catalogue/"

EC_COLLECTIONS = [
    "EarthCAREL1Validated_MAAP",
    "EarthCAREL2Validated_MAAP",
    "JAXAL2Validated_MAAP",
    "EarthCAREL1InstChecked_MAAP",
    "EarthCAREL2InstChecked_MAAP",
    "JAXAL2InstChecked_MAAP",
    "EarthCAREL01L1Products_MAAP",
    "EarthCAREL2Products_MAAP",
    "EarthCAREXMETL1DProducts10_MAAP",
    "JAXAL2Products_MAAP",
    "EarthCAREOrbitData_MAAP",
    "EarthCAREAuxiliary_MAAP",
    ]

# contain more EarthCARE products (inst checked / validated / products).

EARTHCARE_COLLECTIONS = [
    "EarthCAREL2InstChecked_MAAP",
    "EarthCAREL2Validated_MAAP",
    "EarthCAREL2Products_MAAP",
    "EarthCAREL1InstChecked_MAAP",
    "EarthCAREL1Validated_MAAP",
    "EarthCAREL01L1Products_MAAP",
    "EarthCAREOrbitData_MAAP",
    "EarthCAREAuxiliary_MAAP",
    ]

# Maximum margin for the last segment when there is no "next start".
DEFAULT_SEGMENT_MAX = timedelta(minutes=12)

# HTTP Retry Configuration
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.5  # Exponential backoff: 1.5^n seconds
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}  # Temporary HTTP errors
RETRYABLE_EXCEPTIONS = (requests.Timeout, requests.ConnectionError)

######################################################################################################

#%%
# ----- Credential and token management Class-----
class CredentialsToken:
    """Simple class to hold credentials and token."""
    def __init__(self, 
                 credentials_file: Path = CREDENTIALS_FILE,
                 base_data_url: str = BASE_DATA_URL, 
                 catalog_url: str = CATALOG_URL, 
                 ec_collections: list[str] = EC_COLLECTIONS, 
                 earthcare_collections: list[str] = EARTHCARE_COLLECTIONS, 
                 segment_max: timedelta = DEFAULT_SEGMENT_MAX
                 ):
        
        self.credentials_file = credentials_file
        self.base_data_url = base_data_url
        self.catalog_url = catalog_url
        self.ec_collections = ec_collections
        self.earthcare_collections = earthcare_collections
        self.segment_max = segment_max

        self.creds = self._load_credentials()
        self.token = self._get_token()

    def _load_credentials(self) -> dict:
        """Read key-value pairs from a credentials file into a dictionary."""
        creds = {}
        if not self.credentials_file.exists():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
        with open(self.credentials_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                creds[key.strip()] = value.strip()
        return creds
    
    def _get_token(self) -> str:
        """Use OFFLINE_TOKEN to fetch a short-lived access token with retry logic."""
        creds = self.creds

        OFFLINE_TOKEN = creds.get("OFFLINE_TOKEN")
        CLIENT_ID = creds.get("CLIENT_ID")
        CLIENT_SECRET = creds.get("CLIENT_SECRET")

        if not all([OFFLINE_TOKEN, CLIENT_ID, CLIENT_SECRET]):
            raise ValueError("Missing OFFLINE_TOKEN, CLIENT_ID, or CLIENT_SECRET in credentials file")

        url = "https://iam.maap.eo.esa.int/realms/esa-maap/protocol/openid-connect/token"
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": OFFLINE_TOKEN,
            "scope": "offline_access openid"
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()

                response_json = response.json()
                access_token = response_json.get('access_token')

                if not access_token:
                    raise RuntimeError("Failed to retrieve access token from IAM response")

                return access_token
            except RETRYABLE_EXCEPTIONS as exc:
                if attempt < MAX_RETRIES:
                    wait_time = BACKOFF_FACTOR ** (attempt - 1)
                    print(f"Token request timeout (attempt {attempt}/{MAX_RETRIES}), retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    raise
            except requests.HTTPError as exc:
                if exc.response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    wait_time = BACKOFF_FACTOR ** (attempt - 1)
                    print(f"Token request HTTP {exc.response.status_code} (attempt {attempt}/{MAX_RETRIES}), retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    raise

######################################################################################################

# ----- MAAP Downloader Class with STAC search and product finding ----- 
class MAAPEarthCAREDownloader:

    def __init__(
        self,
        credentials_token: CredentialsToken | None = None,
        log_file: str | Path = "maap_download.log",
        logger_name: str = "MAAPEarthCAREDownloader",
    ):

        credentials_token = credentials_token or CredentialsToken()

        self.token = credentials_token.token
        self.base_data_url = credentials_token.base_data_url
        self.catalog_url = credentials_token.catalog_url
        self.ec_collections = credentials_token.ec_collections
        self.earthcare_collections = credentials_token.earthcare_collections
        self.segment_max = credentials_token.segment_max

        self.logger = self._setup_logger(log_file, logger_name)

    @staticmethod
    def _setup_logger(log_file: str | Path, logger_name: str) -> logging.Logger:
        """Create a file logger once and reuse it for this class."""
        logger = logging.getLogger(logger_name)
        if logger.handlers:
            return logger

        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(Path(log_file), encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.propagate = False
        return logger

    def _stac_search(
        self,
        collections: list[str],
        cql_filter: str,
        dt_start: str,
        dt_end: str,
        limit: int = 5,
    ) -> list[dict]:
        """Run STAC search with automatic retry on temporary failures."""
        url = f"{self.catalog_url.rstrip('/')}/search"
        payload = {
            "collections": collections,
            "filter-lang": "cql2-text",
            "filter": cql_filter,
            "datetime": f"{dt_start}/{dt_end}",
            "limit": limit,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data.get("features", [])
            except RETRYABLE_EXCEPTIONS as exc:
                if attempt < MAX_RETRIES:
                    wait_time = BACKOFF_FACTOR ** (attempt - 1)
                    self.logger.debug(
                        "STAC search timeout (attempt %d/%d), retry in %.1fs: %s",
                        attempt, MAX_RETRIES, wait_time, exc,
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error("STAC search failed after %d attempts", MAX_RETRIES)
                    raise
            except requests.HTTPError as exc:
                if exc.response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    wait_time = BACKOFF_FACTOR ** (attempt - 1)
                    self.logger.debug(
                        "STAC search HTTP %d (attempt %d/%d), retry in %.1fs",
                        exc.response.status_code, attempt, MAX_RETRIES, wait_time,
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(
                        "STAC search HTTP %d (non-retryable or max attempts reached)",
                        exc.response.status_code,
                    )
                    raise

    def _extract_start_time(self, item_id: str) -> datetime | None:
        """Extract acquisition start time from item ID like ..._YYYYMMDDTHHMMSSZ_...."""
        m = re.search(r"_(\d{8}T\d{6}Z)_", item_id)
        if not m:
            return None
        return datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)

    def _choose_asset_href(self, stac_item: dict) -> str | None:
        """Pick preferred downloadable URL from item assets."""
        assets = stac_item.get("assets", {})
        for _, asset in assets.items():
            href = asset.get("href", "")
            if href.lower().endswith(".h5"):
                return href
        for _, asset in assets.items():
            href = asset.get("href", "")
            if href:
                return href
        return None

    def _detect_collection(self, product_type: str, frame: str, target: datetime) -> str | None:
        """Find which collection contains the requested EarthCARE product around target time."""
        window_start = (target - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        window_end = (target + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        cql_filter = (
            f"productType = '{product_type}' and "
            f"version = '{frame}' and "
            "platform = 'EarthCARE'"
        )

        for collection in self.earthcare_collections:
            try:
                features = self._stac_search(
                    collections=[collection],
                    cql_filter=cql_filter,
                    dt_start=window_start,
                    dt_end=window_end,
                    limit=1,
                )
                if features:
                    return collection
            except Exception as exc:
                self.logger.debug("Collection detection failed for %s: %s", collection, exc)
                continue
        return None

    def load_date_hours(
        self,
        date_hours: Iterable[str] | None = None,
        input_mode: str = "list",
        csv_path: str | Path | None = None,
        date_column: str = "date_hour",
    ) -> list[str]:
        """Load date-hour targets from a list (default) or from CSV file column."""
        input_mode = input_mode.strip().lower()
        if input_mode not in {"list", "csv"}:
            raise ValueError("input_mode must be 'list' or 'csv'.")

        if input_mode == "list":
            if date_hours is None:
                raise ValueError("For input_mode='list', provide date_hours.")

            cleaned = [str(dt).strip() for dt in date_hours if str(dt).strip()]
            if not cleaned:
                raise ValueError("date_hours is empty after cleaning.")
            return cleaned

        if csv_path is None:
            raise ValueError("For input_mode='csv', provide csv_path.")

        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        with csv_file.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or date_column not in reader.fieldnames:
                raise ValueError(
                    f"Column '{date_column}' not found in CSV. "
                    f"Available columns: {reader.fieldnames}"
                )

            cleaned = []
            for row in reader:
                value = (row.get(date_column) or "").strip()
                if value:
                    cleaned.append(value)

        if not cleaned:
            raise ValueError(f"CSV '{csv_file}' has no valid values in column '{date_column}'.")

        return cleaned

    def _parse_datetime(self, dt_input) -> datetime:
        """
        Convert dt_input to UTC datetime. Accepts:
        - datetime with tzinfo  -> returned as is
        - datetime without tzinfo -> assumed UTC
        - str in any format recognizable by dateutil:
                '2025-05-09 14:40:33'
                '2025-05-09T14:40:33Z'
                '20250509T144033Z'
                '09/05/2025 14:40'
                ... etc.
        """
        if isinstance(dt_input, datetime):
            if dt_input.tzinfo is None:
                return dt_input.replace(tzinfo=timezone.utc)
            return dt_input

        if isinstance(dt_input, str):
            # Compact format without separators: 20250509T144033Z
            dt_input = re.sub(r'^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z?$',
                            r'\1-\2-\3T\4:\5:\6Z', dt_input)
            dt = dateutil_parser.parse(dt_input)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        raise TypeError(f"Cannot convert '{dt_input}' to datetime.")

    def search_segments_from_catalog(
        self,
        product_type: str,
        frame: str,
        target_time,
        collection: str | None = None,
        search_minutes: int = 6,
    ) -> list[dict]:
        """Return candidate segments around target time from STAC (no direct /data listing)."""
        target = self._parse_datetime(target_time)

        chosen_collection = collection or self._detect_collection(product_type, frame, target)
        if not chosen_collection:
            raise RuntimeError(
                "Not detected collection for the given productType/frame near the requested time. "
                "Please provide the collection parameter manually."
            )

        window_start = (target - timedelta(minutes=search_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        window_end = (target + timedelta(minutes=search_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

        cql_filter = (
            f"productType = '{product_type}' and "
            f"version = '{frame}' and "
            "platform = 'EarthCARE'"
        )
        features = self._stac_search(
            collections=[chosen_collection],
            cql_filter=cql_filter,
            dt_start=window_start,
            dt_end=window_end,
            limit=5,
        )

        segments = []
        for item in features:
            item_id = item.get("id", "")
            start = self._extract_start_time(item_id)
            if not start:
                continue
            segments.append(
                {
                    "id": item_id,
                    "start_time": start,
                    "href": self._choose_asset_href(item),
                    "collection": chosen_collection,
                }
            )

        segments.sort(key=lambda x: x["start_time"])
        return segments

    def find_product_by_time(
        self,
        product_type: str,
        frame: str,
        target_time,
        collection: str | None = None,
        search_minutes: int = 6,
    ) -> dict | None:
        """
            Given a point in time (any format), returns the segment that contains it
            using STAC start times and inferred variable duration.

            Main rule:
                - start_i <= target < start_(i+1)
            and for the last segment:
                - start_last <= target < start_last + DEFAULT_SEGMENT_MAX

        Parameters:
            product_type : e.g. 'ATL_FM__2A' or 'MSI_COP_2A'
            frame        : e.g. 'BA', 'E'
            target_time  : datetime, or str in any readable format
                        e.g. '2025-05-09 14:40', '20250509T144033Z'

        Example:
            product = find_product_by_time("ATL_FM__2A", "BA", "2025-02-03 23:40")
            download_product(product["url"], "/tmp/output.h5")
        """
        target = self._parse_datetime(target_time)
        segments = self.search_segments_from_catalog(
            product_type=product_type,
            frame=frame,
            target_time=target,
            collection=collection,
            search_minutes=search_minutes,
        )

        if not segments:
            self.logger.warning("No STAC segments found for target_time=%s", target.isoformat())
            return None

        # Variable intervals inferred with the next start_time.
        for idx, seg in enumerate(segments):
            start = seg["start_time"]
            if idx < len(segments) - 1:
                end = segments[idx + 1]["start_time"]
            else:
                end = start + self.segment_max

            if start <= target < end:
                result = {
                    "name": seg["id"],
                    "url": seg["href"],
                    "start_time": start,
                    "end_time": end,
                    "collection": seg["collection"],
                }
                self.logger.info(
                    "Product found | name=%s | collection=%s | start=%s | end=%s",
                    result["name"],
                    result["collection"],
                    result["start_time"],
                    result["end_time"],
                )
                return result

        self.logger.warning(
            "No segment exactly covers target=%s within the search window.",
            target.isoformat(),
        )
        for seg in segments:
            self.logger.info("Available segment | start=%s | id=%s", seg["start_time"], seg["id"])
        return None

    def download_product(self, product_url: str, output_filename: str | Path):
        """Download a file with automatic retry on temporary HTTP errors."""
        output_path = Path(output_filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headers = {"Authorization": f"Bearer {self.token}"}

        self.logger.info("Downloading product | url=%s | output=%s", product_url, output_path)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with requests.get(
                    product_url, headers=headers, stream=True, timeout=120
                ) as r:
                    r.raise_for_status()
                    with output_path.open("wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                self.logger.info("Download complete | output=%s", output_path)
                return output_path
            except RETRYABLE_EXCEPTIONS as exc:
                if output_path.exists():
                    output_path.unlink()  # Clean up incomplete file
                if attempt < MAX_RETRIES:
                    wait_time = BACKOFF_FACTOR ** (attempt - 1)
                    self.logger.warning(
                        "Download timeout (attempt %d/%d), retry in %.1fs: %s",
                        attempt, MAX_RETRIES, wait_time, exc,
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error("Download failed after %d attempts", MAX_RETRIES)
                    raise
            except requests.HTTPError as exc:
                if output_path.exists():
                    output_path.unlink()  # Clean up incomplete file
                if exc.response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    wait_time = BACKOFF_FACTOR ** (attempt - 1)
                    self.logger.warning(
                        "Download HTTP %d (attempt %d/%d), retry in %.1fs",
                        exc.response.status_code, attempt, MAX_RETRIES, wait_time,
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(
                        "Download HTTP %d (non-retryable or max attempts reached)",
                        exc.response.status_code,
                    )
                    raise

    def download_products_by_time(
        self,
        product_type: str,
        frame: str,
        date_hours: Iterable[str] | None = None,
        input_mode: str = "list",
        csv_path: str | Path | None = None,
        date_column: str = "date_hour",
        collection: str | None = None,
        search_minutes: int = 6,
        output_dir: str | Path = "/home/onel/Downloads",
        overwrite: bool = False,
    ) -> dict:
        """Download products in batch from list/csv date-time inputs with progress and logging."""
        targets = self.load_date_hours(
            date_hours=date_hours,
            input_mode=input_mode,
            csv_path=csv_path,
            date_column=date_column,
        )

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "downloaded": [],
            "not_found": [],
            "errors": [],
            "skipped": [],
        }

        for date_hour in tqdm(targets, desc="Downloading files", unit="file"):
            try:
                product = self.find_product_by_time(
                    product_type=product_type,
                    frame=frame,
                    target_time=date_hour,
                    collection=collection,
                    search_minutes=search_minutes,
                )
            except Exception as exc:
                self.logger.exception("Search error for date_hour=%s: %s", date_hour, exc)
                results["errors"].append({"date_hour": date_hour, "error": str(exc)})
                continue

            if not product:
                self.logger.warning("No product found for date_hour=%s", date_hour)
                results["not_found"].append({"date_hour": date_hour})
                continue

            output_file = out_dir / f"{product['name']}.h5"
            if output_file.exists() and not overwrite:
                self.logger.info("Skipping existing file (overwrite=False): %s", output_file)
                results["skipped"].append(
                    {
                        "date_hour": date_hour,
                        "name": product["name"],
                        "output": str(output_file),
                    }
                )
                continue

            try:
                self.download_product(product["url"], output_file)
                results["downloaded"].append(
                    {
                        "date_hour": date_hour,
                        "name": product["name"],
                        "output": str(output_file),
                    }
                )
            except Exception as exc:
                self.logger.exception("Download error for date_hour=%s: %s", date_hour, exc)
                results["errors"].append({"date_hour": date_hour, "error": str(exc)})

        self.logger.info(
            "Batch finished | downloaded=%s | skipped=%s | not_found=%s | errors=%s",
            len(results["downloaded"]),
            len(results["skipped"]),
            len(results["not_found"]),
            len(results["errors"]),
        )
        return results

#%%
#%%
if __name__ == "__main__":

    downloader = MAAPEarthCAREDownloader()

    # Current values (fallback if the user does not want to enter data)
    default_product_type = "ATL_FM__2A"
    default_frame = "BA"
    default_dates_to_download = [
        "2024-08-15 13:53",
        "2025-07-28 00:32",
    ]
    default_collection = None
    default_search_minutes = 12
    default_output_dir = "/home/onel/Downloads"
    default_overwrite = False

    # Suggested options for menu
    product_type_options = [
    # ATLID level 1b
    'ATL_NOM_1B',
    'ATL_DCC_1B',
    'ATL_CSC_1B',
    'ATL_FSC_1B',
    # MSI level 1b
    'MSI_NOM_1B',
    'MSI_BBS_1B',
    'MSI_SD1_1B',
    'MSI_SD2_1B',
    # BBR level 1b
    'BBR_NOM_1B',
    'BBR_SNG_1B',
    'BBR_SOL_1B',
    'BBR_LIN_1B',
    # CPR level 1b  #@ JAXA product
    'CPR_NOM_1B',   #@ JAXA product
    # MSI level 1c
    'MSI_RGR_1C',
    # level 1d
    'AUX_MET_1D',
    'AUX_JSG_1D',
    # ATLID level 2a
    'ATL_FM__2A',
    'ATL_AER_2A',
    'ATL_ICE_2A',
    'ATL_TC__2A',
    'ATL_EBD_2A',
    'ATL_CTH_2A',
    'ATL_ALD_2A',
    # MSI level 2a
    'MSI_CM__2A',
    'MSI_COP_2A',
    'MSI_AOT_2A',
    # CPR level 2a
    'CPR_FMR_2A',
    'CPR_CD__2A',
    'CPR_TC__2A',
    'CPR_CLD_2A',
    'CPR_APC_2A',
    # ATLID-MSI level 2b
    'AM__MO__2B',
    'AM__CTH_2B',
    'AM__ACD_2B',
    # ATLID-CPR level 2b
    'AC__TC__2B',
    # BBR-MSI-(ATLID) level 2b
    'BM__RAD_2B',
    'BMA_FLX_2B',
    # ATLID-CPR-MSI level 2b
    'ACM_CAP_2B',
    'ACM_COM_2B',
    'ACM_RT__2B',
    # ATLID-CPR-MSI-BBR
    'ALL_DF__2B',
    'ALL_3D__2B',
    # Orbit data    #@ Orbit files in Auxiliary data collection 
    'MPL_ORBSCT',   #@ orbit scenario file 
    'AUX_ORBPRE',   #@ predicted orbit file
    'AUX_ORBRES',   #@ restituted/reconstructed orbit file
]
    frame_options = ["AB", "AC", "AD", "AE", "AF", "BA", "BB", "BC", "BD"]

    def choose_from_menu(title: str, options: list[str], allow_empty: bool = False) -> str | None:
        print(f"\n{title}")

        labels = [f"{i}. {opt}" for i, opt in enumerate(options, start=1)]
        if len(labels) > 12:
            columns = 3
            rows = (len(labels) + columns - 1) // columns
            col_width = max(len(label) for label in labels) + 4
            for row in range(rows):
                cells = []
                for col in range(columns):
                    idx = row + (col * rows)
                    if idx < len(labels):
                        cells.append(labels[idx].ljust(col_width))
                print("  " + "".join(cells).rstrip())
        else:
            for label in labels:
                print(f"  {label}")

        if allow_empty:
            print("  0. Auto/default")

        while True:
            raw = input("Select a number: ").strip()
            if allow_empty and raw == "0":
                return None
            if raw.isdigit():
                idx = int(raw)
                if 1 <= idx <= len(options):
                    return options[idx - 1]
            print("Invalid selection. Try again.")

    def ask_dates() -> list[str]:
        print("\nEnter target dates.")
        print("Accepted formats (examples):")
        print("  - 2025-05-09 14:40")
        print("  - 2025-05-09T14:40:33Z")
        print("  - 20250509T144033Z")
        print("  - 09/05/2025 14:40")
        print("You can enter multiple dates separated by commas on a single line.")
        print("If left empty, the default dates in the code will be used.")

        raw = input("Dates: ").strip()
        if not raw:
            return default_dates_to_download

        dates = [x.strip() for x in raw.split(",") if x.strip()]
        return dates if dates else default_dates_to_download

    def ask_int_with_default(prompt: str, default_value: int) -> int:
        raw = input(f"{prompt} [{default_value}]: ").strip()
        if not raw:
            return default_value
        if raw.isdigit():
            return int(raw)
        print("Invalid value, the default will be used.")
        return default_value

    def ask_yes_no_with_default(prompt: str, default_value: bool) -> bool:
        default_txt = "y" if default_value else "n"
        raw = input(f"{prompt} [y/n, default={default_txt}]: ").strip().lower()
        if not raw:
            return default_value
        return raw in {"y", "yes", "s", "si", "sí"}

    interactive = ask_yes_no_with_default(
        "Do you want to enter parameters via terminal?",
        default_value=False
    )

    if not interactive:
        # Current behavior
        downloader.download_products_by_time(
            product_type=default_product_type,
            frame=default_frame,
            date_hours=default_dates_to_download,
            input_mode="list",
            csv_path=None,
            date_column="date_hour",
            collection=default_collection,
            search_minutes=default_search_minutes,
            output_dir=default_output_dir,
            overwrite=default_overwrite,
        )
    else:
        product_type = choose_from_menu("Select product_type:", product_type_options) or default_product_type
        frame = choose_from_menu("Select frame:", frame_options) or default_frame
        dates_to_download = ask_dates()

        collection_options = EARTHCARE_COLLECTIONS[:]  # actual script options
        collection = choose_from_menu(
            "Select collection (or 0 for auto-detection):",
            collection_options,
            allow_empty=True
        )

        search_minutes = ask_int_with_default("search_minutes", default_search_minutes)

        output_dir_raw = input(f"output_dir [{default_output_dir}]: ").strip()
        output_dir = output_dir_raw if output_dir_raw else default_output_dir

        overwrite = ask_yes_no_with_default("Overwrite existing files?", default_overwrite)

        downloader.download_products_by_time(
            product_type=product_type,
            frame=frame,
            date_hours=dates_to_download,
            input_mode="list",
            csv_path=None,
            date_column="date_hour",
            collection=collection,   # None = auto-detection
            search_minutes=search_minutes,
            output_dir=output_dir,
            overwrite=overwrite,
        )



#%%
"""if __name__ == "__main__":

    downloader = MAAPEarthCAREDownloader()

    
    dates_to_download = [
        "2024-08-15 13:53",
        "2025-07-28 00:32",
    ]

    downloader.download_products_by_time(
        product_type="ATL_FM__2A",
        frame="BA",
        date_hours=dates_to_download,
        input_mode="list",  # Use "csv" and csv_path="/path/file.csv" to load from file.
        csv_path=None,
        date_column="date_hour",
        collection=None,
        search_minutes=12,
        output_dir="/home/onel/Downloads",
        overwrite=False,
    )"""
#%%
