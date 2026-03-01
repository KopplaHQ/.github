"""Fetch latest blog posts from sitemap and update README.md."""
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

SITEMAP_URL = "https://kopplamarketing.com/sitemap.xml"
MAX_POSTS = 10


def fetch_url(url):
    """Fetch URL content as string, with curl fallback for restrictive servers."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KopplaBlogBot/1.0; +https://github.com/KopplaHQ)"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return subprocess.check_output(
            ["curl", "-sL", "-A", "Mozilla/5.0 (compatible; KopplaBlogBot/1.0)", url],
            text=True,
            timeout=30,
        )


def get_page_title(url):
    """Extract <title> from a page, fallback to slug-based title."""
    try:
        html = fetch_url(url)
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            # Remove common suffixes like " | Koppla Marketing" or " - Koppla"
            title = re.split(r"\s*[|–—-]\s*Koppla", title)[0].strip()
            if title:
                return title
    except Exception:
        pass
    # Fallback: convert URL slug to title
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").title()


def fetch_blog_posts():
    """Fetch blog posts from sitemap, filtered to /blog/ and sorted by date."""
    xml_text = fetch_url(SITEMAP_URL)
    root = ET.fromstring(xml_text)

    # Detect sitemap namespace
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    posts = []
    for url_elem in root.findall("sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        lastmod = url_elem.find("sm:lastmod", ns)
        if loc is None or lastmod is None:
            continue

        url = loc.text.strip()

        # Only include /blog/ posts (not the /blog/ index itself)
        if "/blog/" not in url or url.rstrip("/").endswith("/blog"):
            continue

        date_str = lastmod.text.strip()
        try:
            date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            continue

        posts.append((date, url))

    # Sort by publish date, newest first
    posts.sort(key=lambda x: x[0], reverse=True)
    return posts[:MAX_POSTS]


def main():
    posts = fetch_blog_posts()

    rows = []
    for date, url in posts:
        title = get_page_title(url)
        date_str = date.strftime("%b %Y")
        rows.append(f"| {date_str} | [**{title}**]({url}) |")

    block = "| Date | Post |\n| --- | --- |\n" + "\n".join(rows)

    readme_path = "profile/README.md"
    with open(readme_path) as f:
        readme = f.read()

    readme = re.sub(
        r"(<!-- BLOG-POST-LIST:START -->\n).*?(<!-- BLOG-POST-LIST:END -->)",
        rf"\1{block}\n\2",
        readme,
        flags=re.DOTALL,
    )

    with open(readme_path, "w") as f:
        f.write(readme)

    print(f"Updated README with {len(rows)} posts")


if __name__ == "__main__":
    main()
