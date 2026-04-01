import requests
from bs4 import BeautifulSoup
from typing import Optional
import time

BASE_URL = "http://books.toscrape.com"

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def get_soup(url: str) -> Optional[BeautifulSoup]:
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (BookScraper/1.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None


def get_book_details(product_url: str) -> dict:
    
    soup = get_soup(product_url)
    if not soup:
        return {"description": "", "category": "Unknown"}

    # Description
    desc_tag = soup.select_one("#product_description ~ p")
    description = desc_tag.text.strip() if desc_tag else ""

    # Category from breadcrumb (index 2 = 3rd item)
    breadcrumb = soup.select("ul.breadcrumb li")
    category = breadcrumb[2].text.strip() if len(breadcrumb) >= 3 else "Unknown"

    return {"description": description, "category": category}


def parse_books_from_page(soup: BeautifulSoup, category: str = "All") -> list[dict]:
    
    books = []
    articles = soup.select("article.product_pod")

    for article in articles:
        try:
            # Title
            title_tag = article.select_one("h3 > a")
            title = title_tag["title"] if title_tag else "Unknown"

            # Price — strip £ symbol
            price_tag = article.select_one("p.price_color")
            price_text = price_tag.text.strip() if price_tag else "0"
            price = float(price_text.replace("£", "").replace("Â", "").strip())

            # Star rating — from CSS class e.g. "star-rating Three"
            rating_tag = article.select_one("p.star-rating")
            rating_classes = rating_tag["class"] if rating_tag else []
            rating_word = next(
                (cls for cls in rating_classes if cls != "star-rating"), "Zero"
            )
            rating = RATING_MAP.get(rating_word, 0)

            # Availability — full text e.g. "In stock (12 available)"
            avail_tag = article.select_one("p.availability")
            availability = avail_tag.text.strip() if avail_tag else "Unknown"

            # Image URL — absolute URL
            img_tag = article.select_one("img")
            img_src = img_tag["src"] if img_tag else ""
            image_url = BASE_URL + "/" + img_src.replace("../../", "").replace("../", "")

            # Product URL — absolute URL
            product_url = ""
            if title_tag and title_tag.get("href"):
                href = title_tag["href"]
                product_url = BASE_URL + "/catalogue/" + href.replace("../", "")

            # Fetch description + real category from detail page
            details = get_book_details(product_url) if product_url else {"description": "", "category": "Unknown"}

            books.append({
                "title": title,
                "price": price,
                "rating": rating,
                "availability": availability,
                "category": details["category"],
                "description": details["description"],
                "image_url": image_url,
                "product_url": product_url,
            })

        except Exception as e:
            print(f"Error parsing book entry: {e}")
            continue

    return books


def get_next_page_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    
    next_btn = soup.select_one("li.next > a")
    if not next_btn:
        return None
    href = next_btn["href"]
    base = current_url.rsplit("/", 1)[0]
    return f"{base}/{href}"


def scrape_all_books(delay: float = 0.3) -> list[dict]:
    
    all_books = []
    url = f"{BASE_URL}/catalogue/page-1.html"
    page_num = 1

    print("Starting full scrape — 50 pages expected...")

    while url:
        print(f"Scraping page {page_num}: {url}")
        soup = get_soup(url)
        if not soup:
            print(f"Skipping page {page_num} — failed to fetch")
            break

        books = parse_books_from_page(soup, category="All")
        all_books.extend(books)
        print(f"Page {page_num}: {len(books)} books (total: {len(all_books)})")

        url = get_next_page_url(soup, url)
        page_num += 1
        time.sleep(delay)

    print(f"Done — {len(all_books)} books scraped")
    return all_books


def scrape_page(page_number: int) -> list[dict]:
    
    if page_number == 1:
        url = f"{BASE_URL}/index.html"
    else:
        url = f"{BASE_URL}/catalogue/page-{page_number}.html"

    soup = get_soup(url)
    if not soup:
        return []

    return parse_books_from_page(soup, category="All")


def get_all_categories() -> list[dict]:
    
    soup = get_soup(f"{BASE_URL}/index.html")
    if not soup:
        return []

    categories = []
    for link in soup.select("ul.nav-list > li > ul > li > a"):
        name = link.text.strip()
        href = link["href"]
        categories.append({"name": name, "url": f"{BASE_URL}/{href}"})

    return categories


def scrape_category(category_name: str, delay: float = 0.3) -> list[dict]:

    categories = get_all_categories()

    matched = next(
        (c for c in categories if category_name.lower() in c["name"].lower()),
        None
    )
    if not matched:
        print(f"Category '{category_name}' not found")
        return []

    category_display = matched["name"]
    url = matched["url"]
    all_books = []
    page_num = 1

    print(f"Scraping category: '{category_display}'")

    while url:
        soup = get_soup(url)
        if not soup:
            break

        books = parse_books_from_page(soup, category=category_display)
        all_books.extend(books)
        print(f"Page {page_num}: {len(books)} books (total: {len(all_books)})")

        next_btn = soup.select_one("li.next > a")
        if next_btn:
            href = next_btn["href"]
            base = url.rsplit("/", 1)[0]
            url = f"{base}/{href}"
            page_num += 1
            time.sleep(delay)
        else:
            break

    return all_books