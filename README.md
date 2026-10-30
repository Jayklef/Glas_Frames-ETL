# Glass Frames ETL

A Python ETL pipeline that extracts eyeglass listings from FramesDirect, cleans the data with pandas, and loads the results into PostgreSQL.

The pipeline uses reusable functions for extraction, transformation, database configuration, and loading.

## Features

- Extracts product listings across a configurable number of pages.
- Collects brand, product name, price, color, and displayed rating.
- Converts prices from strings to numeric values.
- Separates color descriptions from color codes.
- Replaces missing-data placeholders with null values.
- Removes rows with no usable product details.
- Loads cleaned data into PostgreSQL.
- Prompts for the database password at runtime.
- Uses a database transaction when loading data.

## Technology Stack

| Technology     | Purpose                                |
| -------------- | -------------------------------------- |
| Python         | Pipeline implementation                |
| Requests       | HTTP requests                          |
| Beautiful Soup | HTML parsing and extraction            |
| pandas         | Data cleaning and transformation       |
| SQLAlchemy     | Database engine and SQL integration    |
| Psycopg 3      | PostgreSQL driver                      |
| PostgreSQL     | Data storage                           |
| pgAdmin        | Optional database management interface |

## Pipeline Overview

1. **Extract:** Request catalogue pages and parse product listings.
2. **Transform:** Clean missing values, convert prices, and separate color codes.
3. **Load:** Write the cleaned DataFrame to PostgreSQL.

The default configuration requests pages 1 through 20. It does not automatically discover the total number of pages.

## Project Structure

```text
Glas_Frames-ETL/
├── glass_frames.py       # Function-based ETL script
├── glass_frames.ipynb    # Exploratory notebook
├── README.md            # Project documentation
└── .gitignore           # Files excluded from version control
```

The local `venv/` directory should not be committed.

## Requirements

- Python 3.12, as used during development
- A running PostgreSQL server
- A PostgreSQL user with permission to connect and create tables
- Internet access to retrieve catalogue pages

pgAdmin is optional; the Python pipeline connects directly to PostgreSQL.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Jayklef/Glas_Frames-ETL.git
cd Glas_Frames-ETL
```

### 2. Create a virtual environment

On macOS or Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

On macOS or Linux:

```bash
./venv/bin/python -m pip install requests beautifulsoup4 pandas sqlalchemy "psycopg[binary]"
```

On Windows:

```powershell
.\venv\Scripts\python.exe -m pip install requests beautifulsoup4 pandas sqlalchemy "psycopg[binary]"
```

Using the virtual environment's Python explicitly ensures packages are installed in the same environment that runs the script.

The package name is `beautifulsoup4`, while its Python import is `bs4`.

## PostgreSQL Setup

### 1. Start PostgreSQL

Ensure the PostgreSQL server is running.

### 2. Create the database

Connect to an existing database such as `postgres` using pgAdmin's Query Tool or `psql`, then run:

```sql
CREATE DATABASE "glass_framesDB";
```

The quotes preserve the uppercase `DB` in the database name.

The pipeline creates the destination table during loading; you do not need to create the table manually.

### 3. Configure the connection

The `connect_to_database()` function uses these defaults:

| Setting  | Default              |
| -------- | -------------------- |
| Driver   | `postgresql+psycopg` |
| Host     | `localhost`          |
| Port     | `5432`               |
| Database | `glass_framesDB`     |
| Username | `postgres`           |
| Password | Requested at runtime |

Update the function if your PostgreSQL server uses different settings:

```python
def connect_to_database():
    connection_url = URL.create(
        drivername="postgresql+psycopg",
        username="postgres",
        password=getpass("Enter your PostgreSQL password: "),
        host="localhost",
        port=5432,
        database="glass_framesDB"
    )

    return create_engine(
        connection_url,
        connect_args={"connect_timeout": 10}
    )
```

`getpass()` prompts for the password without displaying it during normal terminal use.

Do not commit database passwords to the repository.

## Running the Pipeline

From the project directory, run:

```bash
./venv/bin/python glass_frames.py
```

On Windows:

```powershell
.\venv\Scripts\python.exe glass_frames.py
```

Enter your PostgreSQL password when prompted.

Example output:

```text
Extracting page 1...
Extracting page 2...
...
Extracting page 20...
Enter your PostgreSQL password:
Loaded <number_of_rows> rows.
```

The row count depends on the listings returned and the rows retained during transformation.

### Change the number of pages

Update the call at the bottom of the script:

```python
if __name__ == "__main__":
    clean_glass_df = run_etl(total_pages=20)

    print(clean_glass_df.head())
    print(f"Total cleaned rows: {len(clean_glass_df)}")
```

For example, use `total_pages=2` for a smaller initial run.

Keep execution in this block rather than also calling each stage elsewhere in the script. Otherwise, the pipeline may run twice.

## Function Reference

| Function                               | Responsibility                                      | Returns           |
| -------------------------------------- | --------------------------------------------------- | ----------------- |
| `extract_glasses(total_pages=20)`      | Requests pages and extracts product fields          | Raw DataFrame     |
| `transform_glasses(glass_df)`          | Cleans the extracted data                           | Cleaned DataFrame |
| `connect_to_database()`                | Configures the SQLAlchemy engine                    | Engine            |
| `load_glasses(clean_glass_df, engine)` | Writes the data to PostgreSQL                       | Nothing           |
| `run_etl(total_pages=20)`              | Coordinates the pipeline and disposes of the engine | Cleaned DataFrame |

### Run individual stages

For exploration or debugging, the functions can be imported without running the full pipeline, provided execution is protected by the `__main__` block.

```python
from glass_frames import (
    extract_glasses,
    transform_glasses,
    connect_to_database,
    load_glasses
)

glass_df = extract_glasses(total_pages=2)
clean_glass_df = transform_glasses(glass_df)

print(clean_glass_df.head())
```

Load the result separately:

```python
engine = connect_to_database()

try:
    load_glasses(clean_glass_df, engine)
finally:
    engine.dispose()
```

## Extracted Fields

| Field           | Description                                           | Example                   |
| --------------- | ----------------------------------------------------- | ------------------------- |
| `brand_name`    | Brand shown in the listing                            | `Oakley`                  |
| `product_name`  | Product or model name                                 | `Airdrop`                 |
| `product_price` | Displayed price before cleaning                       | `$227`                    |
| `color`         | Color description and code before cleaning            | `Satin Black (OX8046-01)` |
| `rating`        | Count of extracted solid star icons, or fallback text | `5 Stars`                 |

## Transformation Rules

### Missing values

These extraction placeholders become pandas missing values:

- `Unknown Brand`
- `Unknown Product`
- `Unknown Price`
- `Unknown Color`
- Empty strings

Missing values are loaded as SQL `NULL`.

### Prices

The transformation:

1. Removes `$`.
2. Removes thousands separators.
3. Converts the result to `float64`.
4. Converts unparseable prices to missing values.

Example:

```text
"$1,250.50" → 1250.50
```

PostgreSQL stores the price as `NUMERIC(10, 2)`.

The DataFrame uses floating-point values during transformation. For stricter financial processing, a future improvement is to use decimal values throughout.

### Colors

The color is split at the last `" ("`, without regex.

Example:

```text
"Satin Black (OX8046-01)"
```

Becomes:

```text
color:      Satin Black
color_code: OX8046-01
```

If no color code is present, `color_code` remains missing.

### Ratings

Ratings remain text, such as:

```text
5 Stars
No Reviews
```

The extraction counts solid star icons. It does not currently interpret half stars or extract review counts.

`No Reviews` is a fallback when no solid stars are found; it is not independently verified evidence that a product has no reviews.

### Empty product rows

A row is removed only when all of these fields are missing:

- `brand_name`
- `product_name`
- `product_price`
- `color`

Partially populated rows are retained.

## Destination Table

The pipeline writes to:

```text
glass_framesDB.public.glass_frames
```

| Column          | PostgreSQL type  |
| --------------- | ---------------- |
| `brand_name`    | `TEXT`           |
| `product_name`  | `TEXT`           |
| `product_price` | `NUMERIC(10, 2)` |
| `color`         | `TEXT`           |
| `rating`        | `TEXT`           |
| `color_code`    | `TEXT`           |

The price type is explicitly configured. Other column types are inferred by pandas and SQLAlchemy.

The pandas index is excluded with `index=False`.

## Load Behavior

The current implementation uses:

```python
if_exists="replace"
```

**Every successful load drops the existing destination table and recreates it from the current cleaned DataFrame.**

This is a snapshot replacement, not an incremental update or upsert.

Consequences:

- Previous rows absent from the latest scrape are removed.
- Historical prices are not retained.
- Existing table indexes and constraints are not preserved.
- A smaller scrape replaces the table with that smaller dataset.
- Duplicate source listings are not automatically removed.

The load runs inside `engine.begin()`. A successful block commits; an exception rolls back the transaction.

An empty cleaned DataFrame is rejected before loading.

## Verify the Load

Connect to `glass_framesDB` in pgAdmin or `psql`.

### Count rows

```sql
SELECT COUNT(*) AS total_rows
FROM public.glass_frames;
```

### Preview products

```sql
SELECT *
FROM public.glass_frames
LIMIT 20;
```

### Count products by brand

```sql
SELECT
    brand_name,
    COUNT(*) AS product_count
FROM public.glass_frames
WHERE brand_name IS NOT NULL
GROUP BY brand_name
ORDER BY product_count DESC;
```

### Calculate average displayed price by brand

```sql
SELECT
    brand_name,
    ROUND(AVG(product_price), 2) AS average_price
FROM public.glass_frames
WHERE brand_name IS NOT NULL
GROUP BY brand_name
ORDER BY average_price DESC;
```

### Check missing prices

```sql
SELECT COUNT(*) AS missing_price_count
FROM public.glass_frames
WHERE product_price IS NULL;
```

### Investigate possible repeated products

```sql
SELECT
    brand_name,
    product_name,
    color_code,
    COUNT(*) AS occurrences
FROM public.glass_frames
GROUP BY brand_name, product_name, color_code
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;
```

Repeated combinations are candidates for investigation, not proof of duplicates. A stable product identifier would provide a stronger basis for deduplication.

## Troubleshooting

### `ModuleNotFoundError: No module named 'psycopg'`

The script may be running in a different Python environment from the one where the driver was installed.

Install and run using the same interpreter:

```bash
./venv/bin/python -m pip install sqlalchemy "psycopg[binary]"
./venv/bin/python glass_frames.py
```

Check the interpreter:

```bash
./venv/bin/python -c "import sys; print(sys.executable)"
```

### `ModuleNotFoundError: No module named 'sqlalchemy'`

Install SQLAlchemy in the environment running the script:

```bash
./venv/bin/python -m pip install sqlalchemy
```

### The notebook cannot import installed packages

Select the notebook kernel associated with the project's `venv`.

Alternatively, install through the active notebook kernel:

```python
%pip install requests beautifulsoup4 pandas sqlalchemy "psycopg[binary]"
```

### The program appears paused at the password prompt

Enter the PostgreSQL password and press Enter.

In a terminal, no characters may appear while typing. In a VS Code notebook, the password prompt may appear in an input box at the top of the window.

### Connection refused

Check that:

- PostgreSQL is running.
- The host and port match your server.
- PostgreSQL is accepting connections at that address.

### Password authentication failed

Check the database username and its PostgreSQL password. This password may differ from your computer login password.

### Database does not exist

Check that the database was created and its name matches the connection configuration exactly:

```text
glass_framesDB
```

### No products found on a page

Possible causes include:

- The requested page has no listings.
- The website changed its HTML.
- Products are loaded differently.
- The returned response is an error or challenge page despite an HTTP 200 status.

Inspect the response HTML before changing selectors. The script raises an error so it does not proceed to replace the database with a partial scrape.

### Repeated products across pages

Ensure pagination replaces the URL placeholder:

```python
url = base_url.format(current_page=current_page)
```

Do not append the page number to the end of the URL template.

Correct pagination syntax alone does not guarantee distinct responses; inspect the results if repetition persists.

## Current Limitations

- Requests a fixed number of pages rather than discovering the final page.
- Depends on the website's current HTML selectors.
- Uses Requests and does not execute JavaScript.
- Has a 30-second HTTP request timeout but no automatic retry policy.
- Stops on request failures rather than resuming from a checkpoint.
- Does not validate that every requested page contains distinct products.
- Does not extract a stable product ID or URL.
- Does not perform automatic deduplication.
- Uses snapshot replacement rather than upserts.
- Does not retain price history or scrape timestamps.
- Does not include automated end-to-end tests.

## Responsible Use

Review the website's terms and robots.txt before running automated requests, and use the data only as permitted.

The script includes a one-second delay between pages. Adjust request frequency to respect the service, and do not attempt to bypass access restrictions.

## Potential Improvements

- Extract product IDs and product URLs.
- Follow pagination links automatically.
- Add retries with backoff for temporary failures.
- Validate scraped records before loading.
- Add structured logging.
- Move connection settings into environment variables.
- Introduce unique constraints and upserts.
- Retain scrape timestamps and historical prices.
- Add automated tests for parsing and transformations.
- Schedule execution after making unattended authentication available.

## License

No license is specified in this README. Add a `LICENSE` file to define the permissions for reuse of the project's code.
