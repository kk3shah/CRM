from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 375, "height": 812}) # Mobile viewport
        
        print("Loading page...")
        page.goto("http://localhost:8080/index.html")
        page.wait_for_timeout(2000)
        
        print("Clicking hamburger...")
        page.click(".nav-toggle")
        page.wait_for_timeout(1000)
        
        # Check classes
        nav_links_classes = page.locator(".nav-links").get_attribute("class")
        nav_toggle_classes = page.locator(".nav-toggle").get_attribute("class")
        print(f"Nav links classes: {nav_links_classes}")
        print(f"Nav toggle classes: {nav_toggle_classes}")
        
        # Take screenshot
        page.screenshot(path="public_html/hamburger_test.png")
        print("Screenshot saved to public_html/hamburger_test.png")
        
        # Print computed style of nav-links
        display = page.evaluate("window.getComputedStyle(document.querySelector('.nav-links')).display")
        opacity = page.evaluate("window.getComputedStyle(document.querySelector('.nav-links')).opacity")
        visibility = page.evaluate("window.getComputedStyle(document.querySelector('.nav-links')).visibility")
        print(f"Computed nav-links - display: {display}, opacity: {opacity}, visibility: {visibility}")
        
        browser.close()

if __name__ == '__main__':
    main()
