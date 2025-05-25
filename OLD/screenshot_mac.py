from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from PIL import Image
import warnings
import time
import os
import base64

# Allow very large images
Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter('ignore', Image.DecompressionBombWarning)

def scroll_to_bottom(driver, pause_time=30, max_scrolls=50):
    last_height = driver.execute_script("return document.body.scrollHeight")
    scrolls = 0
    while scrolls < max_scrolls:
        driver.execute_script("window.scrollBy(0, window.innerHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scrolls += 1

def get_fullpage_screenshot(driver, path):
    metrics = driver.execute_cdp_cmd('Page.getLayoutMetrics', {})
    width = metrics['contentSize']['width']
    height = metrics['contentSize']['height']

    driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
        "mobile": False,
        "width": width,
        "height": height,
        "deviceScaleFactor": 1,
        "screenOrientation": {"angle": 0, "type": "portraitPrimary"}
    })

    screenshot = driver.execute_cdp_cmd('Page.captureScreenshot', {
        'fromSurface': True,
        'captureBeyondViewport': True
    })
    img_data = base64.b64decode(screenshot['data'])

    with open(path, 'wb') as f:
        f.write(img_data)

    driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})

def main():
    with open("urls.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    output_folder = "screenshots"
    os.makedirs(output_folder, exist_ok=True)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(100)

    total = len(urls)
    for idx, url in enumerate(urls, 1):
        try:
            print(f"\n🔄 Processing {url} ({idx}/{total})...")
            driver.get(url)
            time.sleep(200)  # Initial page load wait

            scroll_to_bottom(driver, pause_time=30, max_scrolls=100)
            print("⏳ Finished scrolling. Waiting for images/content to load...")
            time.sleep(100)  # Extra buffer wait before screenshot

            # Removed: code that hides headers/sticky elements

            # Save full-page screenshot using CDP
            png_path = os.path.join(output_folder, f"screenshot_{idx}.png")
            get_fullpage_screenshot(driver, png_path)
            print(f"🖼️ PNG saved: {png_path}")

            # Convert to PDF (resize if necessary)
            img = Image.open(png_path)
            rgb = img.convert('RGB')

            max_width = 1240  # A4 width at 150 DPI
            if rgb.width > max_width:
                new_height = int((max_width / rgb.width) * rgb.height)
                rgb = rgb.resize((max_width, new_height), Image.LANCZOS)

            pdf_path = os.path.join(output_folder, f"screenshot_{idx}.pdf")
            rgb.save(pdf_path)
            print(f"📄 PDF saved: {pdf_path}")

        except Exception as e:
            print(f"❌ Failed to capture {url}: {e}")

    driver.quit()
    print("\n✅ All screenshots completed!")

if __name__ == "__main__":
    main()
