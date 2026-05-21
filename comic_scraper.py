#!/usr/bin/env python3
"""
Comic Scraper - Standalone CLI tool for downloading comics from e-hentai.org and readcomiconline.li
"""
import os
import sys
import ssl
import urllib3
import requests
import zipfile
import shutil
import re
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException, ConnectTimeout
from playwright.sync_api import sync_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Disable warnings about unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a custom SSL context that allows weaker DH keys
ssl_context = ssl.create_default_context()
ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")

# HTTP session for e-hentai
ehentai_session = requests.Session()
ehentai_adapter = requests.adapters.HTTPAdapter()
ehentai_session.mount("https://", ehentai_adapter)

# HTTP session for readcomiconline
rco_session = requests.Session()
rco_retries = Retry(total=5, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
rco_session.mount("https://", HTTPAdapter(max_retries=rco_retries))
RCO_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
rco_session.headers.update({"User-Agent": RCO_UA})

# ==================== E-HENTAI FUNCTIONS ====================

def ehentai_download_image(img_url, folder, img_name):
    """Download an image from E-Hentai"""
    try:
        response = ehentai_session.get(img_url, stream=True, verify=False)
        if response.status_code == 200:
            img_path = os.path.join(folder, img_name)
            with open(img_path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            logger.info(f"Downloaded: {img_name}")
            return True
        else:
            logger.warning(f"Failed to download: {img_url}")
            return False
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error: {e} - Skipping {img_url}")
        return False

def cleanup_empty_folder(folder_path):
    """Remove folder if it exists and is empty or only contains temp files"""
    try:
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            files = [f for f in os.listdir(folder_path) if not f.startswith('.')]
            if len(files) == 0:
                shutil.rmtree(folder_path, ignore_errors=True)
                logger.info(f"Cleaned up empty folder: {os.path.basename(folder_path)}")
    except Exception as e:
        logger.warning(f"Could not cleanup folder {folder_path}: {e}")

def create_cbz(folder):
    """Create CBZ file from folder with unique naming to prevent overwrites"""
    cbz_filename = f"{folder}.cbz"

    # Check if file already exists and add counter if needed
    if os.path.exists(cbz_filename):
        base_path = folder
        counter = 1
        while os.path.exists(cbz_filename):
            cbz_filename = f"{base_path}_({counter}).cbz"
            counter += 1
        logger.info(f"File already exists, using unique name: {os.path.basename(cbz_filename)}")

    with zipfile.ZipFile(cbz_filename, 'w', zipfile.ZIP_DEFLATED) as cbz:
        for root, _, files in os.walk(folder):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder)
                cbz.write(file_path, arcname)
    logger.info(f"Created CBZ archive: {cbz_filename}")

    # Remove the directory after creating the CBZ file
    shutil.rmtree(folder)
    logger.info(f"Removed directory: {folder}")

    return cbz_filename

def scrape_ehentai_gallery(url):
    """Scrape an E-Hentai gallery"""
    first_url = url + "?nw=always"
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_links = []
    save_folder = None

    try:
        logger.info(f"Scraping E-Hentai: {first_url}")
        response = requests.get(first_url, headers=headers)
        if response.status_code != 200:
            logger.error("Failed to access the URL.")
            raise Exception("Failed to access the URL")

        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string.strip()
        title = re.sub(r'\[.*?\]', '', title)  # Remove content in brackets
        title = title.replace(" - E-Hentai Galleries", "").strip()
        title = title.replace("#", "")  # Remove '#' from directory name
        title = title.replace(":", "")  # Remove ':' from directory name

        save_folder = os.path.join(os.getcwd(), title)

        # Ensure unique folder name to prevent conflicts
        if os.path.exists(save_folder):
            base_folder = save_folder
            counter = 1
            while os.path.exists(save_folder):
                save_folder = f"{base_folder}_({counter})"
                counter += 1
            logger.info(f"Folder exists, using unique name: {os.path.basename(save_folder)}")

        os.makedirs(save_folder, exist_ok=True)
        logger.info(f"Saving to: {save_folder}")

        gpc = soup.find('p', class_='gpc')
        if not gpc:
            logger.error("Could not determine the number of images.")
            raise Exception("Could not determine the number of images")

        match = re.search(r'Showing \d+ - \d+ of (\d+) images', gpc.text)
        if not match:
            logger.error("Could not parse the total number of images.")
            raise Exception("Could not parse the total number of images")

        total_images = int(match.group(1))
        total_pages = (total_images + 39) // 40  # Each page contains up to 40 images

        logger.info(f"Total images: {total_images}, Total pages: {total_pages}")

        # Collect all image page links
        for page in range(total_pages):
            page_url = first_url if page == 0 else url + f'?p={page}'
            logger.info(f"Scraping page {page + 1}/{total_pages}: {page_url}")
            response = requests.get(page_url, headers=headers)
            if response.status_code != 200:
                logger.warning(f"Failed to access page {page}.")
                continue

            time.sleep(1)  # Pause to avoid overwhelming the server

            soup = BeautifulSoup(response.text, 'html.parser')
            gallery_div = soup.find('div', id='gdt')
            if not gallery_div:
                logger.warning(f"No gallery found on page {page}.")
                continue

            links = [urljoin(url, a['href']) for a in gallery_div.find_all('a', href=True)]
            all_links.extend(links)

        logger.info(f"Found {len(all_links)} image page links")

        # Download images
        success_count = 0
        for index, link in enumerate(all_links, start=1):
            logger.info(f"Processing image {index}/{len(all_links)}")

            img_page = requests.get(link, headers=headers)
            if img_page.status_code != 200:
                logger.warning(f"Failed to access image page: {link}")
                continue

            img_soup = BeautifulSoup(img_page.text, 'html.parser')
            img_div = img_soup.find('div', id='i3')
            if not img_div:
                logger.warning(f"No image found on: {link}")
                continue

            img_tag = img_div.find('img')
            if img_tag and 'src' in img_tag.attrs:
                img_url = img_tag['src']
                img_ext = os.path.splitext(img_url)[-1]
                img_name = f"image_{index:04d}{img_ext}"

                if ehentai_download_image(img_url, save_folder, img_name):
                    success_count += 1
            else:
                logger.warning(f"No valid image found on: {link}")

            time.sleep(0.5)  # Small delay between downloads

        logger.info(f"Downloaded {success_count}/{len(all_links)} images")

        # Check if folder has any files before creating CBZ
        if not os.path.exists(save_folder) or not os.listdir(save_folder):
            logger.error("No files downloaded successfully")
            raise Exception("No files downloaded successfully")

        # Create CBZ
        cbz_path = create_cbz(save_folder)
        logger.info(f"✓ Successfully created: {cbz_path}")
        return cbz_path

    except Exception as e:
        # Clean up empty folder on error
        if save_folder:
            cleanup_empty_folder(save_folder)
        raise

# ==================== READCOMICONLINE FUNCTIONS ====================

def safe_title(text: str) -> str:
    """Sanitize title for filesystem"""
    t = ' '.join((text or 'comic').split())
    t = t.replace(" - Read Comic Online", "")
    t = re.sub(r' - Read .+ comic online.*$', '', t, flags=re.I)
    return re.sub(r'[<>:"/\\|?*\r\n]', '', t).strip() or "comic"

def get_issue_links(series_url: str) -> list:
    """Get all issue links from a series page"""
    r = rco_session.get(series_url, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    anchors = soup.find_all("a", href=True)
    links = []
    series_path = urlparse(series_url).path.rstrip("/")
    for a in anchors:
        href = a["href"]
        full = urljoin(series_url, href)
        # Match both /Issue-X and /Full formats
        if series_path in full and ("/Issue-" in full or "/Full" in full):
            if "readType=" not in full:
                full += ("&" if "?" in full else "?") + "readType=1"
            links.append(full)

    logger.info(f"Found {len(links)} issue links")
    return sorted(set(links))

def download_image_via_requests(url, output_path, referer):
    """Download image using requests with proper headers"""
    headers = {
        "Referer": referer,
        "User-Agent": RCO_UA,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with rco_session.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(32768):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Request failed: {str(e)[:60]}")
        return False

def scrape_rco_issue_with_browser(pw, issue_url: str):
    """Scrape a single issue using Playwright browser"""
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=RCO_UA, java_script_enabled=True)
    page = ctx.new_page()

    # Force readType=0 for single-page mode
    if "readType=" in issue_url:
        issue_url = re.sub(r'readType=\d+', 'readType=0', issue_url)
    else:
        issue_url += ("&" if "?" in issue_url else "?") + "readType=0"

    # Remove any existing fragment
    base_url = issue_url.split('#')[0]

    img_urls = []
    title_text = "comic"
    folder = None

    try:
        logger.info(f"Opening {base_url}")
        page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)

        # Get title
        title_text = page.title()

        # Find number of pages from select dropdown
        num_pages = page.evaluate("""
            () => {
                const sel = document.querySelector('select.selectEpisode') || document.querySelector('#selectPage');
                return sel ? sel.options.length : 0;
            }
        """)

        if not num_pages:
            logger.error("Could not find page selector")
            page.close()
            ctx.close()
            browser.close()
            return None

        logger.info(f"Found {num_pages} pages")

        # Navigate through each page and extract the main image from #divImage
        for page_num in range(1, num_pages + 1):
            logger.info(f"Page {page_num}/{num_pages}")

            # Wait for images to be present and loaded
            try:
                page.wait_for_selector("#divImage img", timeout=5000)
                page.wait_for_timeout(800)
            except Exception:
                pass

            # Extract only the main comic image from #divImage (the middle/2nd image)
            try:
                img_src = page.evaluate("""
                    () => {
                        const div = document.querySelector('#divImage');
                        if (!div) return null;
                        const imgs = Array.from(div.querySelectorAll('img')).filter(img => {
                            const src = img.src;
                            return src && src.includes('blogspot.com') && !src.includes('loading.gif');
                        });
                        // Return the middle image (usually index 1 in 0-indexed array)
                        if (imgs.length >= 2) {
                            return imgs[1].src;
                        } else if (imgs.length === 1) {
                            return imgs[0].src;
                        }
                        return null;
                    }
                """)

                if img_src:
                    img_urls.append(img_src)
                else:
                    logger.warning(f"No image found on page {page_num}")
            except Exception as e:
                logger.error(f"Failed to extract image on page {page_num}: {str(e)[:60]}")

            # Click next button for the next page (except on last page)
            if page_num < num_pages:
                try:
                    # Store current URL hash before click
                    current_hash = page.evaluate("() => window.location.hash")

                    # Click the next button
                    page.evaluate("() => document.querySelector('#btnNext').click()")

                    # Wait for hash to change
                    page.wait_for_function(
                        f"() => window.location.hash !== '{current_hash}'",
                        timeout=3000
                    )
                except Exception as e:
                    logger.warning(f"Navigation error: {str(e)[:60]}")

    except Exception as e:
        logger.error(f"Error: {e}")

    if not img_urls:
        logger.error("No images collected")
        try:
            page.close()
            ctx.close()
            browser.close()
        except Exception:
            pass
        if folder:
            cleanup_empty_folder(folder)
        return None

    # Create folder path after we have images to download
    folder = safe_title(title_text)

    # Ensure unique folder name to prevent conflicts
    if os.path.exists(folder):
        base_folder = folder
        counter = 1
        while os.path.exists(folder):
            folder = f"{base_folder}_({counter})"
            counter += 1
        logger.info(f"Folder exists, using unique name: {os.path.basename(folder)}")

    logger.info(f"Collected {len(img_urls)} images. Title: {os.path.basename(folder)}")
    os.makedirs(folder, exist_ok=True)

    # Download images directly using requests with proper referer
    for i, url in enumerate(img_urls, 1):
        ext = os.path.splitext(url.split("?")[0])[-1].lower()
        if not ext or len(ext) > 5:
            ext = ".jpg"
        out = os.path.join(folder, f"{i:03d}{ext}")

        # Try downloading with requests
        if download_image_via_requests(url, out, base_url):
            logger.info(f"✓ Downloaded {i}/{len(img_urls)}")
        else:
            logger.warning(f"! Failed {i}/{len(img_urls)}")

        time.sleep(0.2)

    try:
        page.close()
        ctx.close()
        browser.close()
    except Exception:
        pass

    # Check if folder has any files before creating CBZ
    if not os.path.exists(folder) or not os.listdir(folder):
        logger.error("No files downloaded successfully")
        cleanup_empty_folder(folder)
        return None

    cbz_path = create_cbz(folder)
    logger.info(f"✓ Successfully created: {cbz_path}")
    return cbz_path

def is_issue_url(url: str) -> bool:
    """Check if URL is a direct issue link (not a series page)"""
    path = urlparse(url).path
    parts = [p for p in path.split('/') if p]

    # If we have more than 2 parts after 'Comic', it's likely an issue
    if len(parts) >= 3 and parts[0] == 'Comic':
        return True

    # Also check for query parameters with 'id=' which indicates a specific issue
    if '?id=' in url:
        return True

    return False

def scrape_readcomiconline(url: str):
    """Scrape from ReadComicOnline - handles both single issues and series"""
    # Check if URL is a single issue or series
    if is_issue_url(url):
        # Single issue or full comic
        logger.info(f"Detected direct issue link: {url}")
        with sync_playwright() as pw:
            return [scrape_rco_issue_with_browser(pw, url)]
    else:
        # Series - get all issues
        logger.info(f"Detected series link, fetching all issues...")
        issues = get_issue_links(url)
        if not issues:
            logger.warning("No issues found")
            return []

        results = []
        with sync_playwright() as pw:
            for idx, u in enumerate(issues, 1):
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Scraping issue {idx}/{len(issues)}: {u}")
                    logger.info('='*60)
                    result = scrape_rco_issue_with_browser(pw, u)
                    if result:
                        results.append(result)
                    time.sleep(0.8)
                except Exception as e:
                    logger.error(f"Error on {u}: {e}")

        return results

# ==================== MAIN FUNCTIONS ====================

def detect_url_type(url: str) -> str:
    """Detect which comic site the URL belongs to"""
    url_lower = url.lower()
    if 'e-hentai.org' in url_lower or 'exhentai.org' in url_lower:
        return 'ehentai'
    elif 'rcostation.xyz' in url_lower:
        return 'readcomiconline'
    else:
        return 'unknown'

def process_url(url: str):
    """Process a single URL based on its type"""
    url = url.strip()
    if not url:
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"Processing URL: {url}")
    logger.info('='*60)

    url_type = detect_url_type(url)

    try:
        if url_type == 'ehentai':
            scrape_ehentai_gallery(url)
        elif url_type == 'readcomiconline':
            scrape_readcomiconline(url)
        else:
            logger.error(f"Unsupported URL: {url}")
            logger.error("Supported sites: e-hentai.org, rcostation.xyz")
    except Exception as e:
        logger.error(f"Failed to process {url}: {e}")

def process_text_file(filepath: str):
    """Process URLs from a text file"""
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return

    logger.info(f"Reading URLs from: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    logger.info(f"Found {len(urls)} URLs in file")

    for idx, url in enumerate(urls, 1):
        logger.info(f"\n\n>>> Processing URL {idx}/{len(urls)} <<<")
        process_url(url)

def main():
    """Main entry point"""
    print("="*60)
    print("Comic Scraper CLI")
    print("Supports: e-hentai.org, rcostation.xyz")
    print("="*60)
    print()

    choice = input("Enter (1) for single URL or (2) for text file: ").strip()

    if choice == '1':
        url = input("Enter URL: ").strip()
        if url:
            process_url(url)
        else:
            print("No URL provided")
    elif choice == '2':
        filename = input("Enter text file name (in current directory): ").strip()
        if filename:
            # If user provided full path, use it; otherwise assume current directory
            if os.path.isabs(filename):
                filepath = filename
            else:
                filepath = os.path.join(os.getcwd(), filename)
            process_text_file(filepath)
        else:
            print("No filename provided")
    else:
        print("Invalid choice")
        return

    print("\n" + "="*60)
    print("Scraping complete!")
    print("="*60)

if __name__ == "__main__":
    main()
