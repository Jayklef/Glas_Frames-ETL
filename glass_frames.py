import time
import requests
import pandas as pd 
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, URL, Numeric



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