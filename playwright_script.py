import os
import time
import re
from urllib.parse import urlparse
from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def hide_sticky_elements(page):
    page.evaluate("""
        const elements = Array.from(document.querySelectorAll('*'));
        for (const el of elements) {
            const style = window.getComputedStyle(el);
            if ((style.position === 'fixed' || style.position === 'sticky') && parseInt(style.height) < 200) {
                el.setAttribute('data-original-display', el.style.display);
                el.style.display = 'none';
            }
        }
    """)

def restore_sticky_elements(page):
    page.evaluate("""
        const elements = Array.from(document.querySelectorAll('*'));
        for (const el of elements) {
            if (el.hasAttribute('data-original-display')) {
                el.style.display = el.getAttribute('data-original-display');
                el.removeAttribute('data-original-display');
            }
        }
    """)

def sanitize_filename(s):
    return re.sub(r'[\\/*?"<>|]', "", s)

def extract_page_metadata(page):
    title = page.title().strip()
    publication = urlparse(page.url).hostname.replace("www.", "").split(".")[0].capitalize()
    date_element = page.query_selector("time")
    if date_element:
        date_text = date_element.inner_text().strip()
    else:
        date_text = time.strftime("%d %b %Y")
    return publication, title, date_text

def capture_and_stitch(page, url, idx):
    print(f"\n🔗 Loading: {url}")
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
    except PlaywrightTimeoutError:
        print("⚠️ networkidle timed out, retrying with wait_until='load'")
        try:
            page.goto(url, wait_until="load", timeout=30000)
        except Exception as e:
            print(f"❌ Error loading page: {e}")
            return

    if "confirm you are human" in page.content().lower():
        print("🛑 CAPTCHA or bot block detected, skipping this URL.")
        return

    publication, title, date_text = extract_page_metadata(page)
    filename_base = sanitize_filename(f"{publication}_{title}_{date_text}")

    print("✅ Page loaded. Waiting for header to fully render...")
    try:
        page.wait_for_selector("header", timeout=3000)
    except:
        print("⚠️ Header not explicitly found — proceeding anyway.")
    page.wait_for_timeout(500)
    top_path = f"screenshots/tmp_{idx}_header.png"
    page.screenshot(path=top_path)

    print("👻 Hiding sticky headers...")
    hide_sticky_elements(page)

    total_height = page.evaluate("document.body.scrollHeight")
    viewport_height = page.viewport_size["height"]
    scroll_position = viewport_height
    part = 1
    image_parts = []

    while scroll_position < total_height:
        print(f"📸 Capturing part {part} at scrollY: {scroll_position}px")
        page.evaluate(f"window.scrollTo(0, {scroll_position})")
        page.wait_for_timeout(1000)
        part_path = f"screenshots/tmp_{idx}_part{part}.png"
        page.screenshot(path=part_path)
        image_parts.append(part_path)
        scroll_position += viewport_height
        part += 1

        if scroll_position > 3 * total_height:
            print("🛑 Stopping due to excessive scroll (possible infinite page).")
            break

    print(f"🔧 Stitching {len(image_parts) + 1} parts together...")
    stitched_image = stitch_images_vertically([top_path] + image_parts)
    full_path = f"screenshots/{filename_base}.png"
    stitched_image.save(full_path)
    print(f"🖼️ Saved full screenshot: {full_path}")

    os.remove(top_path)
    for img_file in image_parts:
        os.remove(img_file)

    restore_sticky_elements(page)

def stitch_images_vertically(image_paths):
    images = [Image.open(p) for p in image_paths]
    total_height = sum(img.height for img in images)
    max_width = max(img.width for img in images)
    stitched = Image.new("RGB", (max_width, total_height))

    current_y = 0
    for img in images:
        stitched.paste(img, (0, current_y))
        current_y += img.height

    return stitched

def run_capture(urls):
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        chromium_args = {
            "headless": True,
        }

        browser = p.chromium.launch(**chromium_args)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            locale="en-US",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.207 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()

        for idx, url in enumerate(urls, 1):
            try:
                capture_and_stitch(page, url, idx)
            except Exception as e:
                print(f"❌ Error with {url}, retrying in headed mode...")
                try:
                    context.close()
                    browser.close()
                    browser = p.chromium.launch(headless=False, slow_mo=50)
                    context = browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        device_scale_factor=1,
                        locale="en-US",
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.207 Safari/537.36",
                        extra_http_headers={
                            "Accept-Language": "en-US,en;q=0.9",
                            "Upgrade-Insecure-Requests": "1"
                        }
                    )
                    page = context.new_page()
                    capture_and_stitch(page, url, idx)
                except Exception as e:
                    print(f"❌ Still failed with headed mode: {e}")

        browser.close()


