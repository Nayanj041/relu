import csv
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-PH,en;q=0.9",
    "Accept": "application/json, text/html;q=0.9",
}


ROLLUP_BASE_URL = "https://api.nike.com/product_feed/rollup_threads/v2"
API_BASE_URL = "https://api.nike.com/cic/browse/v2"
CONSUMER_CHANNEL_ID = "d9a5bc42-4b9c-4976-858a-f159cf99c647"
PAGE_SIZE = 60
LISTING_DELAY = 0.6
DETAIL_DELAY = 0.5
DETAIL_WORKERS = 4


CSV_HEADERS = [
    "Product_URL",
    "Product_Image_URL",
    "Product_Tagging",
    "Product_Name",
    "Product_Description",
    "Original_Price",
    "Discount_Price",
    "Sizes_Available",
    "Vouchers",
    "Available_Colors",
    "Color_Shown",
    "Style_Code",
    "Rating_Score",
    "Review_Count",
]


@dataclass
class Product:
    Product_URL: str = ""
    Product_Image_URL: str = ""
    Product_Tagging: str = ""
    Product_Name: str = ""
    Product_Description: str = ""
    Original_Price: str = ""
    Discount_Price: str = ""
    Sizes_Available: str = ""
    Vouchers: str = ""
    Available_Colors: str = ""
    Color_Shown: str = ""
    Style_Code: str = ""
    Rating_Score: str = ""
    Review_Count: str = ""


class NikeScraperPH:
    def __init__(self, base_url: str = "https://www.nike.com/ph/w"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.products: List[Product] = []
        self.empty_tagging_count = 0

    def fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def price_to_float(self, price_text: str) -> Optional[float]:
        if not price_text:
            return None
        cleaned = price_text.replace("₱", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    def format_price(self, value: Optional[object]) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return f"₱{value:,.2f}"
        text = str(value).strip()
        if not text:
            return ""
        if text.startswith("₱"):
            return text
        if re.search(r"\d", text):
            return f"₱{text}"
        return text

    def parse_price_value(self, value: Optional[object]) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return self.price_to_float(str(value))

    def build_api_params(self, anchor: int, include_filter: bool) -> List[Tuple[str, str]]:
        params = [
            ("queryid", "products"),
            ("country", "PH"),
            ("language", "en-PH"),
            ("marketplace", "PH"),
            ("channel", "web"),
            ("count", str(PAGE_SIZE)),
            ("anchor", str(anchor)),
            ("consumerChannelId", CONSUMER_CHANNEL_ID),
            ("path", "/ph/w"),
        ]
        if include_filter:
            params.append(("filter", "gender:Women"))
        return params

    def build_rollup_params(self, anchor: int, include_gender: bool) -> List[Tuple[str, str]]:
        params = [
            ("filter", "marketplace(PH)"),
            ("filter", "language(en-PH)"),
            ("filter", f"channelId({CONSUMER_CHANNEL_ID})"),
            ("filter", "employeePrice(false)"),
            ("filter", "exclusiveAccess(false)"),
            ("anchor", str(anchor)),
            ("count", str(PAGE_SIZE)),
        ]
        if include_gender:
            params.append(("filter", "gender(Women)"))
        return params

    def extract_tags(self, info: dict) -> str:
        tags: List[str] = []
        for key in ["productTags", "productTag", "badges", "badging", "label"]:
            value = info.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item not in tags:
                        tags.append(item)
                    elif isinstance(item, dict):
                        label = item.get("label") or item.get("title") or item.get("name")
                        if label and label not in tags:
                            tags.append(label)
            elif isinstance(value, str) and value not in tags:
                tags.append(value)

        merch = info.get("merchProduct") or {}
        merch_tags = merch.get("productTags")
        if isinstance(merch_tags, list):
            for item in merch_tags:
                if isinstance(item, str) and item not in tags:
                    tags.append(item)

        return " | ".join(tags)

    def parse_product_from_info(self, info: dict) -> Product:
        merch = info.get("merchProduct") or info.get("product") or {}
        content = info.get("productContent") or {}
        price = info.get("merchPrice") or info.get("price") or {}

        product = Product()

        url = merch.get("url") or info.get("pdpUrl") or content.get("pdpUrl") or ""
        if url and url.startswith("/"):
            url = "https://www.nike.com" + url
        product.Product_URL = url

        image_urls = info.get("imageUrls") or content.get("imageUrls") or {}
        product.Product_Image_URL = image_urls.get("productImageUrl", "")

        product.Product_Tagging = self.extract_tags(info)

        product.Product_Name = (
            merch.get("label")
            or merch.get("name")
            or content.get("title")
            or ""
        )
        product.Product_Description = (
            content.get("subtitle")
            or merch.get("subtitle")
            or content.get("description")
            or ""
        )

        full_value = self.parse_price_value(price.get("fullPrice"))
        current_value = self.parse_price_value(price.get("currentPrice"))
        discounted_flag = price.get("discounted") is True

        if full_value is not None:
            product.Original_Price = self.format_price(full_value)
        elif current_value is not None:
            product.Original_Price = self.format_price(current_value)

        if current_value is not None and full_value is not None and current_value < full_value:
            product.Discount_Price = self.format_price(current_value)
        elif discounted_flag and current_value is not None:
            product.Discount_Price = self.format_price(current_value)

        color_options = info.get("colorOptions") or info.get("availableColors") or info.get("colors")
        if isinstance(color_options, list):
            product.Available_Colors = f"{len(color_options)} Colors"
        elif isinstance(color_options, int):
            product.Available_Colors = f"{color_options} Colors"

        product.Color_Shown = merch.get("colorDescription", "")
        product.Style_Code = merch.get("styleColor") or merch.get("styleCode") or ""

        return product

    def parse_products_from_payload(self, payload: dict) -> List[Product]:
        products: List[Product] = []
        items = payload.get("data", {}).get("products", {}).get("products")
        if not items:
            items = payload.get("products", [])
        if not items:
            items = payload.get("objects", [])

        def walk(value: object) -> None:
            if isinstance(value, dict):
                if "productInfo" in value and isinstance(value["productInfo"], list):
                    for info in value["productInfo"]:
                        if isinstance(info, dict):
                            products.append(self.parse_product_from_info(info))
                elif "merchProduct" in value or "productContent" in value:
                    products.append(self.parse_product_from_info(value))
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        if items:
            walk(items)
        else:
            walk(payload)

        return products

    def load_products_from_rollup_api(self) -> None:
        seen_urls: Set[str] = set()
        anchor = 0
        page = 1

        for include_gender in [True, False]:
            while True:
                params = self.build_rollup_params(anchor, include_gender)
                try:
                    response = self.session.get(ROLLUP_BASE_URL, params=params, timeout=30)
                except Exception as exc:
                    logger.warning("Rollup request failed: %s", exc)
                    break

                if response.status_code != 200:
                    logger.warning("Rollup status %s", response.status_code)
                    break

                try:
                    payload = response.json()
                except Exception:
                    logger.warning("Rollup returned non-JSON response")
                    break

                page_products = self.parse_products_from_payload(payload)
                if not page_products:
                    logger.info("Rollup returned 0 products; keys: %s", list(payload.keys()))
                    break

                for product in page_products:
                    if product.Product_URL and product.Product_URL not in seen_urls:
                        seen_urls.add(product.Product_URL)
                        self.products.append(product)

                logger.info("Rollup page %s: collected %s products", page, len(seen_urls))
                anchor += PAGE_SIZE
                page += 1
                time.sleep(LISTING_DELAY)

            if self.products:
                break
            anchor = 0
            page = 1

    def load_products_from_browse_api(self) -> None:
        seen_urls: Set[str] = set()
        anchor = 0
        page = 1

        for include_filter in [True, False]:
            while True:
                params = self.build_api_params(anchor, include_filter)
                try:
                    response = self.session.get(API_BASE_URL, params=params, timeout=30)
                except Exception as exc:
                    logger.warning("Browse request failed: %s", exc)
                    break

                if response.status_code != 200:
                    logger.warning("Browse status %s", response.status_code)
                    break

                try:
                    payload = response.json()
                except Exception:
                    logger.warning("Browse returned non-JSON response")
                    break

                page_products = self.parse_products_from_payload(payload)
                if not page_products:
                    logger.info("Browse returned 0 products; keys: %s", list(payload.keys()))
                    break

                for product in page_products:
                    if product.Product_URL and product.Product_URL not in seen_urls:
                        seen_urls.add(product.Product_URL)
                        self.products.append(product)

                logger.info("API page %s: collected %s products", page, len(seen_urls))
                anchor += PAGE_SIZE
                page += 1
                time.sleep(LISTING_DELAY)

            if self.products:
                break
            anchor = 0
            page = 1

    def load_products_from_html(self) -> None:
        html = self.fetch_html(self.base_url)
        payloads: List[dict] = []

        next_data_match = re.search(r"<script[^>]*id=\"__NEXT_DATA__\"[^>]*>(.*?)</script>", html, re.DOTALL)
        if next_data_match:
            try:
                payloads.append(json.loads(next_data_match.group(1)))
            except Exception:
                pass

        preloaded_match = re.search(r"__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;", html, re.DOTALL)
        if preloaded_match:
            raw = preloaded_match.group(1)
            try:
                payloads.append(json.loads(raw))
            except Exception:
                sanitized = raw.replace("undefined", "null")
                try:
                    payloads.append(json.loads(sanitized))
                except Exception:
                    pass

        seen_urls: Set[str] = set()
        for payload in payloads:
            for product in self.parse_products_from_payload(payload):
                if product.Product_URL and product.Product_URL not in seen_urls:
                    seen_urls.add(product.Product_URL)
                    self.products.append(product)

    def load_all_products(self) -> None:
        self.load_products_from_rollup_api()
        if not self.products:
            self.load_products_from_browse_api()
        if not self.products:
            self.load_products_from_html()

        logger.info("Finished collecting listing data: %s products", len(self.products))

    def fetch_product_details(self, product: Product) -> None:
        if not product.Product_URL:
            return

        try:
            response = self.session.get(product.Product_URL, timeout=20)
            if response.status_code != 200:
                return

            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text("\n", strip=True)

            sizes = []
            for size_elem in soup.select("li[data-qa='size-available'], button[data-qa='size-available']"):
                text = size_elem.get_text(strip=True)
                if text and text not in sizes:
                    sizes.append(text)
            if sizes:
                product.Sizes_Available = " | ".join(sizes)

            color_match = re.search(r"(?:Colour|Color) Shown:\s*([^\n]+)", page_text, re.IGNORECASE)
            if color_match:
                product.Color_Shown = color_match.group(1).strip()

            style_match = re.search(r"Style(?:\s*Code)?:\s*([A-Za-z0-9-]+)", page_text, re.IGNORECASE)
            if style_match:
                product.Style_Code = style_match.group(1).strip()

            review_match = re.search(r"([0-5](?:\.\d)?)\s*\((\d+)\s*Reviews?\)", page_text)
            if review_match:
                product.Rating_Score = review_match.group(1)
                product.Review_Count = review_match.group(2)
            else:
                alt_review_match = re.search(r"(\d+)\s*Reviews?", page_text)
                alt_rating_match = re.search(r"([0-5](?:\.\d)?)\s*Rating", page_text)
                if alt_review_match:
                    product.Review_Count = alt_review_match.group(1)
                if alt_rating_match:
                    product.Rating_Score = alt_rating_match.group(1)

            voucher_candidates = []
            for line in page_text.split("\n"):
                lower = line.lower()
                if any(term in lower for term in ["voucher", "promo", "member", "% off"]):
                    if len(line) < 120:
                        voucher_candidates.append(line.strip())
            if voucher_candidates:
                product.Vouchers = voucher_candidates[0]

            time.sleep(DETAIL_DELAY)

        except Exception:
            return

    def enrich_products(self) -> None:
        logger.info("Fetching product details for %s products", len(self.products))
        with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
            list(executor.map(self.fetch_product_details, self.products))

    def count_empty_tagging(self) -> None:
        self.empty_tagging_count = sum(1 for p in self.products if not p.Product_Tagging.strip())
        print(f"Total products with empty tagging: {self.empty_tagging_count}")

    def get_valid_products(self) -> List[Product]:
        valid = []
        for product in self.products:
            if not product.Product_Tagging.strip():
                continue
            if not product.Discount_Price.strip():
                continue
            valid.append(product)
        return valid

    def save_products_csv(self, products: List[Product], filename: str) -> None:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for product in products:
                writer.writerow({key: getattr(product, key) for key in CSV_HEADERS})

        logger.info("Saved %s products to %s", len(products), filename)

    def print_top_expensive(self, products: List[Product], limit: int = 10) -> None:
        priced = []
        for product in products:
            price_val = self.price_to_float(product.Discount_Price)
            if price_val is not None:
                priced.append((price_val, product))

        priced.sort(key=lambda x: x[0], reverse=True)

        print("\nTop 10 Most Expensive Products:")
        print("-" * 80)
        for idx, (_, product) in enumerate(priced[:limit], 1):
            print(f"{idx}. {product.Product_Name}")
            print(f"   Final Price: {product.Discount_Price}")
            print(f"   URL: {product.Product_URL}")
            print()

    def save_top_20_rating_review(self, filename: str = "top_20_rating_review.csv") -> None:
        eligible = []
        for product in self.products:
            try:
                if int(product.Review_Count) > 150:
                    eligible.append(product)
            except Exception:
                continue

        def rating_key(p: Product):
            try:
                rating = float(p.Rating_Score) if p.Rating_Score else 0.0
            except ValueError:
                rating = 0.0
            return (-rating, -int(p.Review_Count))

        eligible.sort(key=rating_key)

        ranked = []
        current_rank = 0
        last_rating = None
        last_reviews = None

        for idx, product in enumerate(eligible[:20], 1):
            try:
                rating = float(product.Rating_Score) if product.Rating_Score else 0.0
                reviews = int(product.Review_Count)
            except Exception:
                continue

            if rating != last_rating or reviews != last_reviews:
                current_rank = idx
            last_rating = rating
            last_reviews = reviews

            ranked.append({
                "Rank": current_rank,
                "Product_Name": product.Product_Name,
                "Rating_Score": product.Rating_Score,
                "Review_Count": product.Review_Count,
                "Original_Price": product.Original_Price,
                "Discount_Price": product.Discount_Price,
                "Product_URL": product.Product_URL,
            })

        headers = [
            "Rank",
            "Product_Name",
            "Rating_Score",
            "Review_Count",
            "Original_Price",
            "Discount_Price",
            "Product_URL",
        ]

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(ranked)

        logger.info("Saved top 20 rating/review ranking to %s", filename)

    def run(self) -> None:
        self.load_all_products()
        if not self.products:
            logger.warning("No products found")
            return

        self.enrich_products()
        self.count_empty_tagging()

        valid_products = self.get_valid_products()
        self.save_products_csv(valid_products, "products_data.csv")

        self.print_top_expensive([p for p in self.products if p.Discount_Price.strip()])
        self.save_top_20_rating_review()


if __name__ == "__main__":
    scraper = NikeScraperPH()
    scraper.run()
