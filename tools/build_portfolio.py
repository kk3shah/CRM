#!/usr/bin/env python3
"""
Dedolytics Portfolio Builder
============================
Scans ./Data folder and generates:
- assets/manifest.json (asset metadata)
- assets/theme.json (color palette from logo)
- assets/work/ (copied dashboard files)
- assets/kindworth/ (copied Kindworth files)
- assets/previews/ (generated preview images)
- assets/images/logo.png (copied logo)

Zero external dependencies. Uses only Python standard library.
Optional: ImageMagick (magick/convert) and pdftoppm (poppler) for enhanced previews.

Usage: python tools/build_portfolio.py
"""

import os
import sys
import json
import shutil
import struct
import subprocess
import math
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "Data"
ASSETS_DIR = PROJECT_ROOT / "assets"
WORK_DIR = ASSETS_DIR / "work"
KINDWORTH_DIR = ASSETS_DIR / "kindworth"
PREVIEWS_DIR = ASSETS_DIR / "previews"
IMAGES_DIR = ASSETS_DIR / "images"

# File patterns
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
PDF_EXTENSIONS = {'.pdf'}
PBIX_EXTENSIONS = {'.pbix'}

# Preview settings
PREVIEW_WIDTH = 1400
PREVIEW_HEIGHT = 900

# Tag keywords for inference
TAG_KEYWORDS = {
    'power bi': 'Power BI',
    'powerbi': 'Power BI',
    'pbix': 'Power BI',
    'sql': 'SQL',
    'snowflake': 'Snowflake',
    'tableau': 'Tableau',
    'metabase': 'Metabase',
    'shopify': 'Shopify',
    'forecast': 'Forecasting',
    'inventory': 'Inventory',
    'replenishment': 'Replenishment',
    'vendor': 'Vendor',
    'scorecard': 'Scorecard',
    'supply chain': 'Supply Chain',
    'dashboard': 'Dashboard',
    'report': 'Reporting',
    'executive': 'Executive',
    'kpi': 'KPI',
    'shorts': 'Inventory',
    'po': 'Purchase Orders',
    'csl': 'Service Level',
    'redsticker': 'Retail Analytics',
    'recovery': 'Recovery',
    'chain': 'Supply Chain',
    'kindworth': 'Kindworth',
    'kq': 'Culture Analytics',
    'burnout': 'HR Analytics',
    'team health': 'Team Health',
    'leadership': 'Leadership',
    'investor': 'Investor Relations',
    'demo': 'Demo',
    'overview': 'Overview',
}


def read_png_dimensions(filepath: Path) -> Tuple[int, int]:
    """Read PNG dimensions without external deps."""
    with open(filepath, 'rb') as f:
        data = f.read(24)
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', data[16:24])
            return w, h
    return 0, 0


def read_jpeg_dimensions(filepath: Path) -> Tuple[int, int]:
    """Read JPEG dimensions without external deps."""
    with open(filepath, 'rb') as f:
        f.seek(0)
        data = f.read(2)
        if data != b'\xff\xd8':
            return 0, 0
        while True:
            marker = f.read(2)
            if len(marker) < 2:
                break
            if marker[0] != 0xff:
                break
            if marker[1] in (0xc0, 0xc1, 0xc2):
                f.read(3)
                h, w = struct.unpack('>HH', f.read(4))
                return w, h
            elif marker[1] == 0xd9:
                break
            elif marker[1] in (0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0x01):
                continue
            else:
                length = struct.unpack('>H', f.read(2))[0]
                f.seek(length - 2, 1)
    return 0, 0


def get_image_dimensions(filepath: Path) -> Tuple[int, int]:
    """Get image dimensions for common formats."""
    ext = filepath.suffix.lower()
    if ext == '.png':
        return read_png_dimensions(filepath)
    elif ext in ('.jpg', '.jpeg'):
        return read_jpeg_dimensions(filepath)
    return 0, 0


def extract_colors_from_image(filepath: Path, num_colors: int = 8) -> List[Tuple[int, int, int]]:
    """
    Extract dominant colors from an image using pixel sampling.
    Uses a simple k-means-like approach with pure Python.
    """
    ext = filepath.suffix.lower()
    
    if ext == '.png':
        return extract_colors_from_png(filepath, num_colors)
    elif ext in ('.jpg', '.jpeg'):
        return extract_colors_from_jpeg(filepath, num_colors)
    
    # Fallback: return default dark palette
    return [
        (10, 10, 10),      # bg - near black
        (21, 21, 21),      # panel - dark grey
        (245, 245, 245),   # text - off-white
        (136, 136, 136),   # muted - grey
        (201, 201, 201),   # accent - silver
        (224, 224, 224),   # accent2 - light silver
        (255, 255, 255),   # glow - white
        (50, 50, 50),      # border - dark border
    ]


def extract_colors_from_png(filepath: Path, num_colors: int) -> List[Tuple[int, int, int]]:
    """Extract colors from PNG using pure Python."""
    try:
        import zlib
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Verify PNG signature
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError("Not a valid PNG")
        
        # Parse chunks
        pos = 8
        width = height = 0
        bit_depth = color_type = 0
        palette = []
        compressed_data = b''
        
        while pos < len(data):
            length = struct.unpack('>I', data[pos:pos+4])[0]
            chunk_type = data[pos+4:pos+8]
            chunk_data = data[pos+8:pos+8+length]
            pos += 12 + length
            
            if chunk_type == b'IHDR':
                width, height = struct.unpack('>II', chunk_data[:8])
                bit_depth = chunk_data[8]
                color_type = chunk_data[9]
            elif chunk_type == b'PLTE':
                for i in range(0, len(chunk_data), 3):
                    palette.append((chunk_data[i], chunk_data[i+1], chunk_data[i+2]))
            elif chunk_type == b'IDAT':
                compressed_data += chunk_data
            elif chunk_type == b'IEND':
                break
        
        # Decompress image data
        raw_data = zlib.decompress(compressed_data)
        
        # Sample pixels
        pixels = []
        bytes_per_pixel = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 3)
        row_bytes = 1 + width * bytes_per_pixel
        
        # Sample every 10th pixel for speed
        step = max(1, min(width, height) // 50)
        
        for y in range(0, height, step):
            row_start = y * row_bytes + 1  # +1 for filter byte
            for x in range(0, width, step):
                pixel_start = row_start + x * bytes_per_pixel
                if pixel_start + bytes_per_pixel <= len(raw_data):
                    if color_type == 2:  # RGB
                        r = raw_data[pixel_start]
                        g = raw_data[pixel_start + 1]
                        b = raw_data[pixel_start + 2]
                        pixels.append((r, g, b))
                    elif color_type == 6:  # RGBA
                        r = raw_data[pixel_start]
                        g = raw_data[pixel_start + 1]
                        b = raw_data[pixel_start + 2]
                        a = raw_data[pixel_start + 3]
                        if a > 128:  # Only include opaque pixels
                            pixels.append((r, g, b))
                    elif color_type == 3 and palette:  # Indexed
                        idx = raw_data[pixel_start]
                        if idx < len(palette):
                            pixels.append(palette[idx])
        
        if not pixels:
            raise ValueError("No pixels extracted")
        
        return quantize_colors(pixels, num_colors)
        
    except Exception as e:
        print(f"  Warning: Could not extract PNG colors: {e}")
        return get_default_palette()


def extract_colors_from_jpeg(filepath: Path, num_colors: int) -> List[Tuple[int, int, int]]:
    """Extract colors from JPEG - simplified approach."""
    # JPEG decoding without external deps is complex
    # Return default palette based on the Dedolytics brand
    return get_default_palette()


def get_default_palette() -> List[Tuple[int, int, int]]:
    """Default luxury dark palette matching Dedolytics brand."""
    return [
        (10, 10, 10),      # bg - near black
        (21, 21, 21),      # panel - dark grey
        (245, 245, 245),   # text - off-white
        (136, 136, 136),   # muted - grey
        (201, 201, 201),   # accent - silver
        (224, 224, 224),   # accent2 - light silver
        (255, 255, 255),   # glow - white
        (40, 40, 40),      # border - dark border
    ]


def quantize_colors(pixels: List[Tuple[int, int, int]], num_colors: int) -> List[Tuple[int, int, int]]:
    """Simple color quantization using k-means-like clustering."""
    if not pixels:
        return get_default_palette()
    
    # Count color frequencies (quantized to 32-level buckets)
    bucket_size = 8
    color_counts = Counter()
    for r, g, b in pixels:
        quantized = (
            (r // bucket_size) * bucket_size,
            (g // bucket_size) * bucket_size,
            (b // bucket_size) * bucket_size
        )
        color_counts[quantized] += 1
    
    # Get most common colors
    common_colors = [c for c, _ in color_counts.most_common(num_colors * 2)]
    
    # Sort by luminance
    def luminance(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    
    common_colors.sort(key=luminance)
    
    # Ensure we have enough colors
    while len(common_colors) < num_colors:
        common_colors.append(common_colors[-1] if common_colors else (128, 128, 128))
    
    return common_colors[:num_colors]


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex string."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def create_theme_from_colors(colors: List[Tuple[int, int, int]]) -> Dict:
    """Create CSS theme variables from extracted colors."""
    # For Dedolytics, we want a matte black base with silver accents
    # The logo is white/silver on black, so we preserve that aesthetic
    
    # Sort by luminance
    sorted_colors = sorted(colors, key=lambda c: 0.299*c[0] + 0.587*c[1] + 0.114*c[2])
    
    # Find the darkest and lightest colors
    darkest = sorted_colors[0]
    lightest = sorted_colors[-1]
    mid_dark = sorted_colors[len(sorted_colors)//4] if len(sorted_colors) > 1 else darkest
    mid_light = sorted_colors[3*len(sorted_colors)//4] if len(sorted_colors) > 2 else lightest
    
    # Ensure we have a proper dark background
    bg = darkest if sum(darkest) < 60 else (10, 10, 10)
    panel = mid_dark if sum(mid_dark) < 100 else (21, 21, 21)
    
    theme = {
        "palette": [rgb_to_hex(c) for c in colors],
        "variables": {
            "bg": rgb_to_hex(bg),
            "panel": rgb_to_hex(panel),
            "text": rgb_to_hex(lightest) if sum(lightest) > 200 else "#f5f5f5",
            "muted": rgb_to_hex(mid_light) if 80 < sum(mid_light) < 500 else "#888888",
            "accent": "#c9c9c9",  # Silver
            "accent2": "#e0e0e0",  # Light silver
            "glow": "rgba(255,255,255,0.08)",
            "border": "#2a2a2a",
        },
        "source": "extracted from logo"
    }
    
    return theme


def clean_filename_to_title(filename: str) -> str:
    """Convert filename to clean title."""
    # Remove extension
    name = Path(filename).stem
    # Remove common prefixes
    for prefix in ['Download ', 'download_', 'Kindworth - ', 'Kindworth_']:
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Replace separators with spaces
    name = name.replace('_', ' ').replace('-', ' ').replace('  ', ' ')
    # Title case
    name = ' '.join(word.capitalize() for word in name.split())
    return name.strip()


def infer_tags(filename: str, content_type: str = 'dashboard') -> List[str]:
    """Infer tags from filename and content type."""
    tags = []
    filename_lower = filename.lower()
    
    for keyword, tag in TAG_KEYWORDS.items():
        if keyword in filename_lower:
            if tag not in tags:
                tags.append(tag)
    
    # Add type-specific tags
    if content_type == 'kindworth':
        if 'Kindworth' not in tags:
            tags.append('Kindworth')
    
    return tags[:5]  # Limit to 5 tags


def check_tool_available(tool: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        result = subprocess.run(
            ['which', tool],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def generate_pdf_preview(pdf_path: Path, output_path: Path, item_id: str) -> Dict:
    """Generate preview from PDF, return quality info."""
    info = {
        "pages": 0,
        "thumbs": [],
        "preview_method": "fallback"
    }
    
    # Try pdftoppm first (best quality)
    if check_tool_available('pdftoppm'):
        try:
            # Get page count
            result = subprocess.run(
                ['pdfinfo', str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    info['pages'] = int(line.split(':')[1].strip())
            
            # Generate first page preview
            temp_prefix = output_path.parent / f"temp_{item_id}"
            subprocess.run(
                ['pdftoppm', '-png', '-f', '1', '-l', '1', 
                 '-scale-to-x', str(PREVIEW_WIDTH), '-scale-to-y', '-1',
                 str(pdf_path), str(temp_prefix)],
                capture_output=True,
                timeout=60
            )
            
            # Find generated file
            for f in output_path.parent.glob(f"temp_{item_id}*.png"):
                shutil.move(str(f), str(output_path.with_suffix('.png')))
                info['preview_method'] = 'pdftoppm'
                break
            
            # Generate thumbnails for first 3 pages
            if info['pages'] > 0:
                for page in range(1, min(4, info['pages'] + 1)):
                    thumb_path = output_path.parent / f"{item_id}_p{page}.png"
                    subprocess.run(
                        ['pdftoppm', '-png', '-f', str(page), '-l', str(page),
                         '-scale-to-x', '200', '-scale-to-y', '-1',
                         str(pdf_path), str(output_path.parent / f"temp_{item_id}_p{page}")],
                        capture_output=True,
                        timeout=30
                    )
                    for f in output_path.parent.glob(f"temp_{item_id}_p{page}*.png"):
                        shutil.move(str(f), str(thumb_path))
                        info['thumbs'].append(f"assets/previews/{thumb_path.name}")
                        break
                        
        except Exception as e:
            print(f"    pdftoppm failed: {e}")
    
    # If no preview generated, create a branded placeholder
    if info['preview_method'] == 'fallback':
        create_placeholder_preview(output_path, "PDF Document", pdf_path.stem)
    
    return info


def generate_pbix_preview(pbix_path: Path, output_path: Path) -> Dict:
    """Generate a branded placeholder for PBIX files."""
    info = {
        "pages": 0,
        "thumbs": [],
        "preview_method": "placeholder"
    }
    
    create_placeholder_preview(output_path, "Power BI Dashboard", pbix_path.stem)
    return info


def create_placeholder_preview(output_path: Path, doc_type: str, title: str):
    """Create a simple branded placeholder (just copy approach for now)."""
    # For now, we'll indicate this needs a placeholder
    # The website will handle this gracefully
    placeholder_info = {
        "type": doc_type,
        "title": title,
        "needs_placeholder": True
    }
    info_path = output_path.with_suffix('.json')
    with open(info_path, 'w') as f:
        json.dump(placeholder_info, f)


def copy_and_process_image(src_path: Path, dst_path: Path, preview_path: Path) -> Dict:
    """Copy image and generate preview."""
    info = {
        "blur_score": 0.5,  # Default mid-value
        "preview_method": "basic"
    }
    
    # Copy original
    shutil.copy2(src_path, dst_path)
    
    # Try ImageMagick for enhanced preview
    if check_tool_available('magick'):
        try:
            subprocess.run(
                ['magick', str(src_path),
                 '-resize', f'{PREVIEW_WIDTH}x{PREVIEW_HEIGHT}>',
                 '-gravity', 'center',
                 '-background', '#0a0a0a',
                 '-extent', f'{PREVIEW_WIDTH}x{PREVIEW_HEIGHT}',
                 '-quality', '90',
                 str(preview_path.with_suffix('.webp'))],
                capture_output=True,
                timeout=30
            )
            if preview_path.with_suffix('.webp').exists():
                info['preview_method'] = 'imagemagick'
        except Exception as e:
            print(f"    ImageMagick failed: {e}")
    
    # Fallback: just copy the original as preview
    if info['preview_method'] == 'basic':
        shutil.copy2(src_path, preview_path.with_suffix(src_path.suffix))
    
    return info


def scan_directory(directory: Path, prefix: str, category: str) -> List[Dict]:
    """Scan a directory for assets and create manifest entries."""
    items = []
    item_counter = 0
    
    # Patterns to exclude (logos)
    LOGO_PATTERNS = {'logo', 'dedolytics logo', 'kindworth_logo', 'kindworth-logo'}
    
    for item in sorted(directory.iterdir()):
        if item.name.startswith('.'):
            continue
        if item.is_dir():
            # Skip subdirectories for now (Wiki, etc.)
            continue
        
        # Skip logo files
        stem_lower = item.stem.lower()
        if any(pattern in stem_lower for pattern in LOGO_PATTERNS):
            print(f"  Skipping logo file: {item.name}")
            continue
        
        ext = item.suffix.lower()
        item_counter += 1
        item_id = f"{prefix}_{item_counter:03d}"
        
        if ext in IMAGE_EXTENSIONS:
            # Process image
            dst_path = (KINDWORTH_DIR if category == 'kindworth' else WORK_DIR) / item.name
            preview_path = PREVIEWS_DIR / f"{item_id}.webp"
            
            print(f"  Processing image: {item.name}")
            quality_info = copy_and_process_image(item, dst_path, preview_path)
            
            # Determine preview extension
            if preview_path.with_suffix('.webp').exists():
                preview_ext = '.webp'
            else:
                preview_ext = item.suffix
            
            items.append({
                "id": item_id,
                "type": "image",
                "category": category,
                "source": f"assets/{'kindworth' if category == 'kindworth' else 'work'}/{item.name}",
                "preview": f"assets/previews/{item_id}{preview_ext}",
                "title": clean_filename_to_title(item.name),
                "tags": infer_tags(item.name, category),
                "caption": "",
                "quality": quality_info,
                "size_bytes": item.stat().st_size
            })
            
        elif ext in PDF_EXTENSIONS:
            # Process PDF
            dst_path = (KINDWORTH_DIR if category == 'kindworth' else WORK_DIR) / item.name
            preview_path = PREVIEWS_DIR / f"{item_id}"
            
            print(f"  Processing PDF: {item.name}")
            shutil.copy2(item, dst_path)
            pdf_info = generate_pdf_preview(item, preview_path, item_id)
            
            # Determine preview extension
            if (preview_path.with_suffix('.png')).exists():
                preview_ext = '.png'
            elif (preview_path.with_suffix('.webp')).exists():
                preview_ext = '.webp'
            else:
                preview_ext = '.json'  # Placeholder marker
            
            items.append({
                "id": item_id,
                "type": "pdf",
                "category": category,
                "source": f"assets/{'kindworth' if category == 'kindworth' else 'work'}/{item.name}",
                "preview": f"assets/previews/{item_id}{preview_ext}",
                "title": clean_filename_to_title(item.name),
                "tags": infer_tags(item.name, category),
                "caption": "",
                "quality": {
                    "blur_score": 0.0,
                    "preview_method": pdf_info['preview_method']
                },
                "pdf": {
                    "pages": pdf_info['pages'],
                    "thumbs": pdf_info['thumbs']
                },
                "size_bytes": item.stat().st_size
            })
            
        elif ext in PBIX_EXTENSIONS:
            # Process PBIX
            dst_path = WORK_DIR / item.name
            preview_path = PREVIEWS_DIR / f"{item_id}"
            
            print(f"  Processing PBIX: {item.name}")
            shutil.copy2(item, dst_path)
            pbix_info = generate_pbix_preview(item, preview_path)
            
            items.append({
                "id": item_id,
                "type": "pbix",
                "category": category,
                "source": f"assets/work/{item.name}",
                "preview": f"assets/previews/{item_id}.json",  # Placeholder marker
                "title": clean_filename_to_title(item.name),
                "tags": ['Power BI'] + infer_tags(item.name, category),
                "caption": "Power BI Dashboard (requires Power BI Desktop to open)",
                "quality": {
                    "blur_score": 0.0,
                    "preview_method": "placeholder"
                },
                "size_bytes": item.stat().st_size
            })
    
    return items


def find_logo() -> Optional[Path]:
    """Find the logo file in the data directory."""
    logo_patterns = [
        'Dedolytics logo.jpeg',
        'Dedolytics logo.png',
        'Dedolytics logo.jpg',
        'logo.png',
        'logo.jpg',
        'logo.jpeg',
    ]
    
    for pattern in logo_patterns:
        path = DATA_DIR / pattern
        if path.exists():
            return path
    
    return None


def find_kindworth_logo() -> Optional[Path]:
    """Find the Kindworth logo file."""
    kindworth_dir = DATA_DIR / 'Kindworth'
    if not kindworth_dir.exists():
        return None
    
    for pattern in ['Download kindworth_logo.png', 'kindworth_logo.png', 'logo.png']:
        path = kindworth_dir / pattern
        if path.exists():
            return path
    
    return None


def main():
    """Main build process."""
    print("\n" + "="*60)
    print("  DEDOLYTICS PORTFOLIO BUILDER")
    print("="*60 + "\n")
    
    # Ensure directories exist
    for d in [WORK_DIR, KINDWORTH_DIR, PREVIEWS_DIR, IMAGES_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Find and process logo
    print("Step 1: Processing logo...")
    logo_path = find_logo()
    theme_data = {}
    
    if logo_path:
        print(f"  Found logo: {logo_path.name}")
        # Copy logo
        shutil.copy2(logo_path, IMAGES_DIR / 'logo.jpeg')
        
        # Extract colors
        print("  Extracting color palette...")
        colors = extract_colors_from_image(logo_path)
        theme_data = create_theme_from_colors(colors)
        
        print(f"  Extracted {len(colors)} colors")
        for i, color in enumerate(colors):
            print(f"    Color {i+1}: {rgb_to_hex(color)}")
    else:
        print("  Warning: No logo found, using default palette")
        theme_data = create_theme_from_colors(get_default_palette())
    
    # Find Kindworth logo
    kindworth_logo = find_kindworth_logo()
    if kindworth_logo:
        print(f"  Found Kindworth logo: {kindworth_logo.name}")
        shutil.copy2(kindworth_logo, IMAGES_DIR / 'kindworth-logo.png')
    
    # Write theme.json
    theme_path = ASSETS_DIR / 'theme.json'
    with open(theme_path, 'w') as f:
        json.dump(theme_data, f, indent=2)
    print(f"  Created: {theme_path}")
    
    # Scan for assets
    print("\nStep 2: Scanning for dashboard assets...")
    all_items = []
    
    # Scan main data directory
    main_items = scan_directory(DATA_DIR, 'work', 'dashboard')
    all_items.extend(main_items)
    print(f"  Found {len(main_items)} items in Data/")
    
    # Scan Kindworth directory
    kindworth_path = DATA_DIR / 'Kindworth'
    if kindworth_path.exists():
        print("\nStep 3: Scanning Kindworth assets...")
        kindworth_items = scan_directory(kindworth_path, 'kw', 'kindworth')
        all_items.extend(kindworth_items)
        print(f"  Found {len(kindworth_items)} items in Data/Kindworth/")
    
    # Create manifest
    print("\nStep 4: Creating manifest...")
    manifest = {
        "brand": {
            "name": "Dedolytics",
            "tagline": "Business Intelligence. Delivered.",
            "email": "hello@dedolytics.org",
            "services": ["Power BI", "SQL", "Snowflake"]
        },
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "items": all_items
    }
    
    manifest_path = ASSETS_DIR / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"  Created: {manifest_path}")
    
    # Summary
    print("\n" + "="*60)
    print("  BUILD COMPLETE")
    print("="*60)
    
    pdf_count = sum(1 for i in all_items if i['type'] == 'pdf')
    image_count = sum(1 for i in all_items if i['type'] == 'image')
    pbix_count = sum(1 for i in all_items if i['type'] == 'pbix')
    
    print(f"\n  Total assets: {len(all_items)}")
    print(f"    - PDFs: {pdf_count}")
    print(f"    - Images: {image_count}")
    print(f"    - Power BI files: {pbix_count}")
    print(f"\n  Accent color: {theme_data['variables'].get('accent', 'default')}")
    print(f"\n  Output directory: {ASSETS_DIR}")
    print("\n  Next: Open index.html in a browser to preview the site\n")


if __name__ == '__main__':
    main()
