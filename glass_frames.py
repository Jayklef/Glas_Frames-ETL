import time
import requests
import pandas as pd 
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, URL, Numeric
from getpass import getpass



def extract_glasses(total_pages=20):
    base_url = (
        "https://www.framesdirect.com/eyeglasses/"
        "?p={current_page}&rows=24&sortby=7&noreset=true"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    brand_name = []
    product_name = []
    product_price = []
    color = []
    rating = []

    for current_page in range(1, total_pages + 1):
        print(f"Extracting page {current_page}...")

        url = base_url.format(current_page=current_page)

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        glass_listings = soup.find_all("div", class_="prod-holder")

        # Stop with an error rather than loading an incomplete scrape.
        if not glass_listings:
            raise ValueError(
                f"No products found on page {current_page}. "
                "Check the response HTML."
            )

        for glass in glass_listings:
            brand_el = glass.find(class_="catalog-name")
            brand = (
                brand_el.get_text(strip=True)
                if brand_el else "Unknown Brand"
            )

            product_el = (
                glass.find(class_="product-name")
                or glass.find(class_="product_name")
            )
            product = (
                product_el.get_text(strip=True)
                if product_el else "Unknown Product"
            )

            price_el = glass.find(class_="prod-aslowas")
            price = (
                price_el.get_text(strip=True)
                if price_el else "Unknown Price"
            )

            color_span = glass.select_one(
                'span[id^="dvSelectedColorName"]'
            )
            glass_color = (
                color_span.get_text(strip=True)
                if color_span else "Unknown Color"
            )

            popular_block = glass.find(class_="prod-popular")

            if popular_block:
                star_count = len(
                    popular_block.find_all(
                        "i", class_="icon-star-solid"
                    )
                )
                rating_value = (
                    f"{star_count} Stars"
                    if star_count > 0 else "No Reviews"
                )
            else:
                rating_value = "No Reviews"

            brand_name.append(brand)
            product_name.append(product)
            product_price.append(price)
            color.append(glass_color)
            rating.append(rating_value)

        if current_page < total_pages:
            time.sleep(1)

    return pd.DataFrame({
        "brand_name": brand_name,
        "product_name": product_name,
        "product_price": product_price,
        "color": color,
        "rating": rating
    })
    

   
#glass_df = extract_glasses(total_pages=20)
#glass_df.head()
#print(f"Total rows extracted: {len(glass_df)}")




def transform_glasses(glass_df):
    clean_glass_df = glass_df.copy()

    # Clean spaces and represent missing values consistently.
    for column in clean_glass_df.columns:
        clean_glass_df[column] = (
            clean_glass_df[column]
            .astype("string")
            .str.strip()
        )

    clean_glass_df = clean_glass_df.replace({
        "Unknown Brand": pd.NA,
        "Unknown Product": pd.NA,
        "Unknown Price": pd.NA,
        "Unknown Color": pd.NA,
        "": pd.NA
    })

    # Convert price to float.
    clean_glass_df["product_price"] = pd.to_numeric(
        clean_glass_df["product_price"]
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False),
        errors="coerce"
    ).astype("float64")

    # Separate color and color code.
    color_parts = clean_glass_df["color"].str.rsplit(
        " (", n=1, expand=True
    )

    # Ensure both columns exist even if no codes were found.
    color_parts = color_parts.reindex(columns=[0, 1])

    clean_glass_df["color"] = (
        color_parts[0].astype("string").str.strip()
    )

    clean_glass_df["color_code"] = (
        color_parts[1]
        .astype("string")
        .str.removesuffix(")")
        .str.strip()
    )

    # Remove rows with no usable product details.
    clean_glass_df = clean_glass_df.dropna(
        subset=[
            "brand_name",
            "product_name",
            "product_price",
            "color"
        ],
        how="all"
    ).reset_index(drop=True)

    return clean_glass_df


# clean_glass_df = transform_glasses(glass_df)
# clean_glass_df.head()
# print(f"The data description is : {clean_glass_df.head()}")



def connect_to_database():
    connection_url = URL.create(
        drivername="postgresql+psycopg",
        username="postgres",
        password=getpass("Enter your PostgreSQL password: "),
        host="localhost",
        port=5432,
        database="glass_framesDB"
    )

    engine = create_engine(
        connection_url,
        connect_args={"connect_timeout": 10}
    )

    return engine

#engine = connect_to_database()


def load_glasses(clean_glass_df, engine):
    if clean_glass_df.empty:
        raise ValueError("No cleaned data to load.")

    with engine.begin() as connection:
        clean_glass_df.to_sql(
            name="glass_frames",
            con=connection,
            schema="public",
            if_exists="replace",
            index=False,
            dtype={
                "product_price": Numeric(10, 2)
            }
        )

    print(f"Loaded {len(clean_glass_df)} rows.")
    
    
# try:
#     load_glasses(clean_glass_df, engine)
# finally:
#     engine.dispose()
    
    
def run_etl(total_pages=20):
    glass_df = extract_glasses(total_pages=total_pages)
    clean_glass_df = transform_glasses(glass_df)

    engine = connect_to_database()

    try:
        load_glasses(clean_glass_df, engine)
    finally:
        engine.dispose()

    return clean_glass_df



if __name__ == "__main__":
    clean_glass_df = run_etl(total_pages=20)

    print("\nPreview of cleaned data:")
    print(clean_glass_df.head())

    print(f"\nTotal cleaned rows: {len(clean_glass_df)}")