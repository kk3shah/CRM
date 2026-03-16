from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        def log_msg(msg):
            print(f"[{msg.type}] {msg.text}")
            
        def log_err(err):
            print(f"[ERROR] {err.error}")

        page.on("console", log_msg)
        page.on("pageerror", log_err)
        
        print("Loading page...")
        page.goto("file:///Users/kushalshah/Documents/Dedolytics/public_html/index.html")
        page.wait_for_timeout(2000)
        browser.close()

if __name__ == '__main__':
    main()
