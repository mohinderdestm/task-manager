import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

BASE_URL = "http://books.toscrape.com/"

RATING_MAP = {
    "One": 1, "Two": 2, "Three": 3,
    "Four": 4, "Five": 5
}


async def fetch(client, url):
    try:
        res = await client.get(url, timeout=10)
        res.raise_for_status()
        return res.text
    except httpx.HTTPStatusError as e:
        print(f"HTTP error {e.response.status_code} -> {url}")
    except httpx.RequestError as e:
        print(f"Request error -> {url}: {e}")
    return None


async def get_categories(client):
    html = await fetch(client, BASE_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    categories = []
    for a in soup.select(".side_categories ul li ul li a"):
        name = a.text.strip()
        link = urljoin(BASE_URL, a["href"])
        categories.append((name, link))

    return categories


async def parse_book_detail(client, url, category):
    html = await fetch(client, url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    try:
        title = soup.find("h1").text.strip()
        price = float(soup.select_one(".price_color").text.replace("£", ""))
        rating_class = soup.select_one(".star-rating")["class"]
        rating = RATING_MAP.get(rating_class[1], 0)
        availability = soup.select_one(".availability").text.strip()

        image_rel = soup.select_one(".item.active img")["src"]
        image_url = urljoin(url, image_rel)

        description_tag = soup.select_one("#product_description ~ p")
        description = description_tag.text.strip() if description_tag else ""

        return {
            "title": title,
            "price": price,
            "rating": rating,
            "availability": availability,
            "category": category,
            "product_url": url,
            "image_url": image_url,
            "description": description,
            "created_at": datetime.utcnow()
        }

    except Exception as e:
        print(f"Parsing error -> {url}: {e}")
        return None


async def scrape_category(client, category_name, category_url, pages=None):
    results = []
    page_url = category_url
    page_count = 0

    while page_url:
        if pages and page_count >= pages:
            break

        html = await fetch(client, page_url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")

        for book in soup.select(".product_pod h3 a"):
            book_url = urljoin(page_url, book["href"])
            detail = await parse_book_detail(client, book_url, category_name)
            if detail:
                results.append(detail)

        next_btn = soup.select_one(".next a")
        page_url = urljoin(page_url, next_btn["href"]) if next_btn else None

        page_count += 1

    return results


async def scrape_all(category_filter=None, pages=None):
    async with httpx.AsyncClient() as client:
        categories = await get_categories(client)

        all_data = []

        for name, url in categories:
            # ✅ case-insensitive category filter
            if category_filter and name.lower() != category_filter.lower():
                continue

            print(f"Scraping category: {name}")
            data = await scrape_category(client, name, url, pages)
            all_data.extend(data)

        return all_data