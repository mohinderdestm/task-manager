import httpx
import asyncio
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
SITE_URL = "https://books.toscrape.com/"

semaphore = asyncio.Semaphore(10)


async def scrape_book_detail(client, url):
    async with semaphore:
        try:
            res = await client.get(url, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            desc_tag = soup.find("meta", attrs={"name": "description"})
            description = desc_tag["content"].strip() if desc_tag else ""

            category = soup.find("ul", class_="breadcrumb").find_all("li")[2].text.strip()

            availability = soup.find("p", class_="instock availability").text.strip()

            image_rel = soup.find("div", class_="item active").img["src"]
            image_url = SITE_URL + image_rel.replace("../", "")

            return {
                "description": description,
                "category": category,
                "availability": availability,
                "image_url": image_url
            }

        except Exception:
            return {}


async def fetch_full_book(client, title, price, rating, product_url, slug):
    details = await scrape_book_detail(client, product_url)

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "product_url": product_url,
        "slug": slug, 
        **details
    }


async def scrape_page(client, page):
    url = BASE_URL.format(page)
    print(f"Scraping page {page}...")

    async with semaphore:
        res = await client.get(url, timeout=10)

    soup = BeautifulSoup(res.text, "html.parser")
    books = soup.find_all("article", class_="product_pod")

    tasks = []

    for book in books:
        title = book.h3.a["title"]
        price = book.find("p", class_="price_color").text
        rating = book.find("p", class_="star-rating")["class"][1]

        relative_url = book.h3.a["href"]

        clean_url = relative_url.replace("../", "")

        product_url = SITE_URL + "catalogue/" + clean_url

        slug = clean_url.split("/")[0]

        tasks.append(fetch_full_book(client, title, price, rating, product_url, slug))

    results = await asyncio.gather(*tasks)
    return results


async def scrape_books():
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20)
    ) as client:

        page_tasks = [scrape_page(client, page) for page in range(1, 51)]
        pages_data = await asyncio.gather(*page_tasks)

        all_books = [book for page in pages_data for book in page]
        return all_books