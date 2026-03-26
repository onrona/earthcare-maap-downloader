# EarthCARE MAAP Downloader

Python script to search and download EarthCARE products from the ESA MAAP catalog using STAC queries and token-based authentication.

## What It Does

- Retrieves an `access token` from local credentials.
- Searches EarthCARE segments/products in the MAAP STAC catalog.
- Selects the product that covers a target date/time.
- Downloads one or more `.h5` products.
- Supports list-based or CSV-based input.

## Current Structure

- `maap_earthcare_downloader.py`: main script with authentication, search, and download logic.
- `download_initial_tests.ipynb`: initial catalog exploration notebook.
- `credentials.example.txt`: credentials template.

## Requirements

- Python 3.10 or newer is recommended.
- Valid MAAP/ESA credentials.

Basic installation:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Credentials Setup

1. Create a local credentials file from the template:

    ```bash
    cp credentials.example.txt credentials.txt
    ```

2. Fill in these values:

    ```txt
    OFFLINE_TOKEN=...
    CLIENT_ID=...
    CLIENT_SECRET=...
    ```

3. Review the `CREDENTIALS_FILE` constant in [maap_earthcare_downloader.py](/media/onel/D/repositories/earthcare-maap-downloader/maap_earthcare_downloader.py#L20). It currently points to an absolute path outside this repository. To use this repo as-is, update it to the actual location of your `credentials.txt`.

## Usage

Run the script:

```bash
python maap_earthcare_downloader.py
```

The script can run:

- With the default values defined in `__main__`.
- In interactive terminal mode.

## Example From Code

```python
from maap_earthcare_downloader import MAAPEarthCAREDownloader

downloader = MAAPEarthCAREDownloader()

results = downloader.download_products_by_time(
    product_type="ATL_FM__2A",
    frame="BA",
    date_hours=[
        "2024-08-15 13:53",
        "2025-07-28 00:32",
    ],
    input_mode="list",
    collection=None,
    search_minutes=12,
    output_dir="/tmp/earthcare-downloads",
    overwrite=False,
)

print(results)
```

## Accepted Date Formats

The script accepts several formats recognized by `python-dateutil`, for example:

- `2025-05-09 14:40`
- `2025-05-09T14:40:33Z`
- `20250509T144033Z`
- `09/05/2025 14:40`

## Main Dependencies

- `requests`
- `python-dateutil`
- `tqdm`

## Output And Logs

- Downloads are saved to the directory configured in `output_dir`.
- The script writes logs to `maap_download.log`.

## Notes

- The repository currently contains a tracked `credentials.txt`. That is not recommended if it contains real secrets.
- `.gitignore` helps prevent new local credential copies, logs, and accidental download outputs from being added to the repository.
- If you want Git to stop tracking `credentials.txt`, you need to remove it from the Git index explicitly.
