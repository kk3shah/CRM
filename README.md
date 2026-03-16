# Dedolytics Portfolio Website

## https://www.dedolytics.com

Premium static portfolio website showcasing analytics dashboards and the Kindworth product.

## Quick Start

### 1. Add Your Content

Place your files in the `Data/` folder:

```
Data/
├── Dedolytics logo.jpeg          # Your logo
├── Dashboard1.png                 # Dashboard images
├── Report.pdf                     # PDF reports
├── Recovery Chain.pbix           # Power BI files
└── Kindworth/                     # Kindworth product assets
    ├── Dashboard.pdf
    └── Investor Deck.pdf
```

### 2. Generate the Portfolio

Run the build script to scan your assets and generate the manifest:

```bash
python tools/build_portfolio.py
```

This will:
- Copy assets to `/assets/work/` and `/assets/kindworth/`
- Extract color palette from your logo
- Generate preview images (if ImageMagick/pdftoppm available)
- Create `manifest.json` with all asset metadata
- Create `theme.json` with extracted color variables

### 3. Preview Locally

Simply open `index.html` in your browser:

```bash
open index.html
```

Or use a local server for better testing:

```bash
python -m http.server 8000
# Then visit http://localhost:8000
```

### 4. Deploy to Hosting

Upload these files to your web hosting:

```
index.html
kindworth.html
styles.css
app.js
robots.txt
sitemap.xml
assets/          (entire folder)
```

## Folder Structure

```
/
├── index.html              # Main Dedolytics page
├── kindworth.html          # Kindworth product page
├── styles.css              # All CSS styles
├── app.js                  # Interactive functionality
├── robots.txt              # SEO
├── sitemap.xml             # SEO
├── README.md               # This file
├── Data/                   # SOURCE: Your content files
│   ├── logo.jpeg
│   ├── *.png, *.pdf, *.pbix
│   └── Kindworth/
├── tools/
│   └── build_portfolio.py  # Build script
└── assets/                 # GENERATED: Web-ready assets
    ├── images/
    │   ├── logo.jpeg
    │   └── kindworth-logo.png
    ├── work/               # Copied dashboard files
    ├── kindworth/          # Copied Kindworth files
    ├── previews/           # Generated preview images
    ├── manifest.json       # Asset metadata
    └── theme.json          # Color theme
```

## Features

- **Static Site**: No build tools required, works on any hosting
- **Game-Menu Gallery**: 3D carousel with keyboard/touch navigation
- **PDF Viewer**: In-browser PDF viewing with PDF.js
- **Image Viewer**: Zoomable image viewing
- **Logo Color Extraction**: Automatic theme from your branding
- **Responsive**: Works on desktop, tablet, and mobile
- **Accessible**: Keyboard navigation, ARIA labels, focus states

## Optional Enhancements

### Better PDF Previews

Install poppler for PDF thumbnail generation:

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils
```

### Image Enhancement

Install ImageMagick for image optimization:

```bash
# macOS
brew install imagemagick

# Ubuntu/Debian
sudo apt-get install imagemagick
```

### Gemini API Enrichment

Set your API key for AI-generated metadata:

```bash
export GEMINI_API_KEY="your-api-key"
python tools/build_portfolio.py
```

## Hosting Options

### Option 1: Static File Hosting

Upload to any static hosting:
- Netlify (drag & drop)
- Vercel
- GitHub Pages
- AWS S3 + CloudFront
- Any shared hosting File Manager

### Option 2: Custom Domain

1. Upload files to your hosting
2. Point `dedolytics.com` DNS to your hosting provider
3. Configure SSL/HTTPS

Example for Cloudflare:
```
A Record: @ → [hosting IP]
CNAME: www → dedolytics.com
```

## Customization

### Colors

Edit `assets/theme.json` or run the build script with a new logo.

### Content

Modify the HTML files directly:
- `index.html`: Services, Process, Outcomes sections
- `kindworth.html`: Features, Problem/Solution sections

### Styles

All CSS is in `styles.css` with CSS custom properties for easy theming.

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

© 2024 Dedolytics. All rights reserved.

---

Built with ❤️ for business intelligence
