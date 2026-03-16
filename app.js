/**
 * DEDOLYTICS - Portfolio Application
 * Interactive gallery, modal viewer, and carousel logic
 */

(function () {
    'use strict';

    // ========================================
    // Configuration
    // ========================================
    const CONFIG = {
        carouselCardWidth: 400,
        carouselGap: 60,
        friction: 0.88,          // Lower for faster response
        snapThreshold: 0.3,      // Lower for easier card transitions
        touchSensitivity: 1.5,   // Higher for mobile
        wheelSensitivity: 1.2,   // 4x higher for better scroll response
    };

    // ========================================
    // State
    // ========================================
    const state = {
        manifest: null,
        theme: null,
        currentIndex: 0,
        velocity: 0,
        isDragging: false,
        dragStart: 0,
        dragOffset: 0,
        carouselOffset: 0,
        animationFrame: null,
        pdfDoc: null,
        currentPage: 1,
        currentZoom: 1,
        isZoomed: false,
    };

    // ========================================
    // DOM Elements
    // ========================================
    let elements = {};

    // ========================================
    // Theme Loading
    // ========================================
    async function loadTheme() {
        try {
            const response = await fetch('assets/theme.json');
            if (!response.ok) throw new Error('Theme not found');

            state.theme = await response.json();
            applyTheme(state.theme);
            console.log('Theme loaded:', state.theme);
        } catch (error) {
            console.warn('Using default theme:', error.message);
        }
    }

    function applyTheme(theme) {
        if (!theme || !theme.variables) return;

        const root = document.documentElement;
        Object.entries(theme.variables).forEach(([key, value]) => {
            root.style.setProperty(`--${key}`, value);
        });
    }

    // ========================================
    // Manifest Loading
    // ========================================
    async function loadManifest() {
        try {
            const response = await fetch('assets/manifest.json');
            if (!response.ok) throw new Error('Manifest not found');

            state.manifest = await response.json();
            console.log('Manifest loaded:', state.manifest.items?.length || 0, 'items');

            return state.manifest;
        } catch (error) {
            console.warn('No manifest found:', error.message);
            return null;
        }
    }

    // ========================================
    // Gallery Rendering
    // ========================================
    function renderGallery(category = 'dashboard') {
        const track = elements.galleryTrack;
        if (!track || !state.manifest) return;

        // Filter items by category
        const items = state.manifest.items.filter(item =>
            category === 'all' || item.category === category
        );

        if (items.length === 0) {
            renderEmptyState(track);
            return;
        }

        track.innerHTML = '';
        items.forEach((item, index) => {
            const card = createGalleryCard(item, index);
            track.appendChild(card);
        });

        // Reset state
        state.currentIndex = 0;
        state.carouselOffset = 0;
        updateCarousel();
    }

    function createGalleryCard(item, index) {
        const card = document.createElement('div');
        card.className = 'gallery-card';
        card.dataset.index = index;
        card.dataset.id = item.id;
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `View ${item.title}`);
        card.setAttribute('tabindex', '0');

        // Preview image or placeholder
        let previewHtml;
        if (item.preview && !item.preview.endsWith('.json')) {
            previewHtml = `<img class="gallery-card-image" src="${item.preview}" alt="${item.title}" loading="lazy" onerror="this.parentElement.innerHTML = createPlaceholderHTML('${item.type}', '${item.title}')">`;
        } else {
            previewHtml = createPlaceholderHTML(item.type, item.title);
        }

        // Tags HTML
        const tagsHtml = (item.tags || []).slice(0, 2).map(tag =>
            `<span class="gallery-card-tag">${tag}</span>`
        ).join('');

        card.innerHTML = `
      ${previewHtml}
      <div class="gallery-card-content">
        <h4 class="gallery-card-title">${item.title}</h4>
        <div class="gallery-card-meta">
          <span class="gallery-card-type">${getTypeLabel(item.type)}</span>
          <div class="gallery-card-tags">${tagsHtml}</div>
        </div>
      </div>
    `;

        // Event listeners
        card.addEventListener('click', () => openViewer(item));
        card.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                openViewer(item);
            }
        });

        return card;
    }

    function createPlaceholderHTML(type, title) {
        const icon = type === 'pdf' ? '📄' : type === 'pbix' ? '📊' : '🖼️';
        const label = type === 'pdf' ? 'PDF Document' : type === 'pbix' ? 'Power BI' : 'Image';

        return `
      <div class="placeholder-preview">
        <span class="placeholder-preview-icon">${icon}</span>
        <span class="placeholder-preview-text">${label}</span>
      </div>
    `;
    }

    // Make it globally available for onerror
    window.createPlaceholderHTML = createPlaceholderHTML;

    function getTypeLabel(type) {
        const labels = {
            'pdf': 'PDF',
            'image': 'Image',
            'pbix': 'Power BI'
        };
        return labels[type] || type.toUpperCase();
    }

    function renderEmptyState(container) {
        container.innerHTML = `
      <div class="gallery-empty">
        <div class="gallery-empty-icon">📊</div>
        <h3>No Work Items Yet</h3>
        <p>Run the build script to populate the portfolio.</p>
        <code style="display: block; margin-top: 1rem; padding: 1rem; background: var(--panel); border-radius: 8px; font-size: 0.875rem;">
          python tools/build_portfolio.py
        </code>
      </div>
    `;
    }

    // ========================================
    // Carousel Physics
    // ========================================

    // Helper to get items visible in main gallery
    function getVisibleItems() {
        if (!state.manifest?.items) return [];
        return state.manifest.items.filter(i => i.category === 'dashboard');
    }

    function updateCarousel() {
        const track = elements.galleryTrack;
        if (!track) return;

        const cards = track.querySelectorAll('.gallery-card');
        const totalCards = cards.length;
        if (totalCards === 0) return;

        // Get actual card width from CSS (responsive)
        const firstCard = cards[0];
        const computedWidth = firstCard ? parseFloat(getComputedStyle(firstCard).width) : CONFIG.carouselCardWidth;
        const gap = CONFIG.carouselGap;
        const cardStep = computedWidth + gap;

        cards.forEach((card, index) => {
            // Calculate position relative to current index
            const relativeIndex = index - state.currentIndex;
            const dragOffset = state.carouselOffset / cardStep;
            const position = relativeIndex + dragOffset;

            // 3D transforms - cards centered via CSS left: 50%, offset from there
            const x = position * cardStep;
            const z = -Math.abs(position) * 80;
            const rotateY = position * -8;
            const scale = 1 - Math.abs(position) * 0.1;
            const opacity = 1 - Math.abs(position) * 0.25;

            card.style.transform = `translateX(calc(-50% + ${x}px)) translateZ(${z}px) rotateY(${rotateY}deg) scale(${Math.max(0.75, scale)})`;
            card.style.opacity = Math.max(0.3, opacity);
            card.style.zIndex = 10 - Math.abs(Math.round(position));

            // Update active state
            const isActive = Math.abs(position) < 0.5;
            card.classList.toggle('active', isActive);
            if (isActive) {
                const items = getVisibleItems();
                if (items[index]) {
                    updateInfoPanel(items[index]);
                }
            }
        });
    }

    function updateInfoPanel(item) {
        const infoPanel = elements.galleryInfo;
        if (!infoPanel || !item) return;

        infoPanel.querySelector('.gallery-info-title').textContent = item.title;
        infoPanel.querySelector('.gallery-info-caption').textContent =
            item.caption || item.tags?.join(' • ') || '';

        infoPanel.classList.add('visible');
    }

    function animateCarousel() {
        if (Math.abs(state.velocity) > 0.1) {
            state.carouselOffset += state.velocity;
            state.velocity *= CONFIG.friction;

            // Snap to card
            const snapOffset = CONFIG.carouselCardWidth + CONFIG.carouselGap;
            if (Math.abs(state.carouselOffset) >= snapOffset * CONFIG.snapThreshold) {
                const direction = state.carouselOffset > 0 ? -1 : 1;
                navigate(direction);
                state.carouselOffset = 0;
                state.velocity = 0;
            }

            updateCarousel();
            state.animationFrame = requestAnimationFrame(animateCarousel);
        } else {
            state.velocity = 0;
            state.carouselOffset *= 0.9;

            if (Math.abs(state.carouselOffset) > 0.5) {
                updateCarousel();
                state.animationFrame = requestAnimationFrame(animateCarousel);
            } else {
                state.carouselOffset = 0;
                updateCarousel();
            }
        }
    }

    function navigate(direction) {
        const items = getVisibleItems();
        const maxIndex = items.length - 1;

        state.currentIndex = Math.max(0, Math.min(maxIndex, state.currentIndex + direction));
        updateCarousel();
    }

    // ========================================
    // Input Handlers
    // ========================================
    function setupCarouselInput() {
        const carousel = elements.galleryCarousel;
        if (!carousel) return;

        // Mouse drag
        carousel.addEventListener('mousedown', (e) => {
            state.isDragging = true;
            state.dragStart = e.clientX;
            cancelAnimationFrame(state.animationFrame);
            carousel.style.cursor = 'grabbing';
        });

        document.addEventListener('mousemove', (e) => {
            if (!state.isDragging) return;

            const delta = e.clientX - state.dragStart;
            state.dragStart = e.clientX;
            state.carouselOffset += delta;
            state.velocity = delta;
            updateCarousel();
        });

        document.addEventListener('mouseup', () => {
            if (state.isDragging) {
                state.isDragging = false;
                carousel.style.cursor = '';
                animateCarousel();
            }
        });

        // Touch
        carousel.addEventListener('touchstart', (e) => {
            state.isDragging = true;
            state.dragStart = e.touches[0].clientX;
            cancelAnimationFrame(state.animationFrame);
        }, { passive: true });

        carousel.addEventListener('touchmove', (e) => {
            if (!state.isDragging) return;

            const touch = e.touches[0];
            const delta = (touch.clientX - state.dragStart) * CONFIG.touchSensitivity;
            state.dragStart = touch.clientX;
            state.carouselOffset += delta;
            state.velocity = delta;
            updateCarousel();
        }, { passive: true });

        carousel.addEventListener('touchend', () => {
            state.isDragging = false;
            animateCarousel();
        });

        // Mouse wheel - listen on the gallery section for better capture
        const gallerySection = document.getElementById('work');
        const wheelHandler = (e) => {
            // Only handle if gallery is visible in viewport
            if (!gallerySection) return;
            const rect = gallerySection.getBoundingClientRect();
            const inView = rect.top < window.innerHeight * 0.8 && rect.bottom > window.innerHeight * 0.2;

            if (!inView) return;

            e.preventDefault();

            // Use deltaY for vertical scroll, deltaX for horizontal
            const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
            state.velocity -= delta * CONFIG.wheelSensitivity;
            cancelAnimationFrame(state.animationFrame);
            animateCarousel();
        };

        // Attach to both carousel and section for comprehensive coverage
        carousel.addEventListener('wheel', wheelHandler, { passive: false });
        gallerySection?.addEventListener('wheel', wheelHandler, { passive: false });

        // Keyboard
        document.addEventListener('keydown', (e) => {
            // Only handle if gallery is in view
            const gallerySection = document.getElementById('work');
            if (!gallerySection) return;

            const rect = gallerySection.getBoundingClientRect();
            const inView = rect.top < window.innerHeight && rect.bottom > 0;

            if (!inView) return;

            switch (e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    navigate(-1);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    navigate(1);
                    break;
                case 'Enter':
                    const activeCard = document.querySelector('.gallery-card.active');
                    if (activeCard) activeCard.click();
                    break;
            }
        });

        // Navigation buttons
        elements.navPrev?.addEventListener('click', () => navigate(-1));
        elements.navNext?.addEventListener('click', () => navigate(1));
    }

    // ========================================
    // Modal Viewer
    // ========================================
    function openViewer(item) {
        const modal = elements.modal;
        if (!modal) return;

        // Update modal title
        modal.querySelector('.modal-title').textContent = item.title;

        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = '';

        if (item.type === 'pdf' || item.type === 'pbix') {
            renderPDFViewer(modalBody, item);
        } else {
            renderImageViewer(modalBody, item);
        }

        modal.classList.add('open');
        document.body.style.overflow = 'hidden';

        // Update download link
        const downloadBtn = modal.querySelector('[data-action="download"]');
        if (downloadBtn) {
            downloadBtn.href = item.source;
            const ext = item.type === 'pdf' ? '.pdf' : item.type === 'pbix' ? '.pbix' : '';
            downloadBtn.download = `${item.title}${ext}`;
        }
    }

    function closeViewer() {
        const modal = elements.modal;
        if (!modal) return;

        modal.classList.remove('open');
        document.body.style.overflow = '';

        // Cleanup PDF
        if (state.pdfDoc) {
            state.pdfDoc.destroy();
            state.pdfDoc = null;
        }
        state.currentPage = 1;
        state.currentZoom = 1;
        state.isZoomed = false;
    }

    // ========================================
    // PDF Viewer
    // ========================================
    async function renderPDFViewer(container, item) {
        container.innerHTML = `
      <div class="pdf-viewer">
        <div class="pdf-sidebar" id="pdfSidebar">
          <div class="pdf-thumbs">Loading...</div>
        </div>
        <div class="pdf-main">
          <canvas id="pdfCanvas" class="pdf-canvas"></canvas>
          <div class="pdf-page-nav">
            <button class="modal-btn" data-action="prevPage" aria-label="Previous page">‹</button>
            <span class="pdf-page-info"><span id="currentPage">1</span> / <span id="totalPages">1</span></span>
            <button class="modal-btn" data-action="nextPage" aria-label="Next page">›</button>
          </div>
        </div>
      </div>
    `;

        // Setup page navigation
        container.querySelector('[data-action="prevPage"]').addEventListener('click', () => renderPage(state.currentPage - 1));
        container.querySelector('[data-action="nextPage"]').addEventListener('click', () => renderPage(state.currentPage + 1));

        // Check if PDF.js is available
        if (typeof pdfjsLib === 'undefined') {
            await loadPDFJS();
        }

        try {
            // For PBIX files, show a message
            if (item.type === 'pbix') {
                container.innerHTML = `
          <div class="image-viewer" style="flex-direction: column; gap: 2rem;">
            <div class="placeholder-preview" style="width: 400px; height: 300px;">
              <span class="placeholder-preview-icon">📊</span>
              <span class="placeholder-preview-text">Power BI Dashboard</span>
            </div>
            <div style="text-align: center; max-width: 400px;">
              <h4 style="margin-bottom: 0.5rem;">Power BI File</h4>
              <p style="color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem;">
                This Power BI dashboard requires Power BI Desktop to view.
              </p>
              <a href="${item.source}" class="btn btn-secondary" download>
                Download .pbix File
              </a>
            </div>
          </div>
        `;
                return;
            }

            // Load PDF
            const loadingTask = pdfjsLib.getDocument(item.source);
            state.pdfDoc = await loadingTask.promise;

            // Update page count
            document.getElementById('totalPages').textContent = state.pdfDoc.numPages;

            // Render first page
            state.currentPage = 1;
            await renderPage(1);

            // Render thumbnails
            await renderPDFThumbnails(item);
        } catch (error) {
            console.error('Error loading PDF:', error);
            container.innerHTML = `
        <div class="image-viewer" style="flex-direction: column;">
          <div class="placeholder-preview" style="width: 300px; height: 200px;">
            <span class="placeholder-preview-icon">⚠️</span>
            <span class="placeholder-preview-text">Unable to load PDF</span>
          </div>
          <a href="${item.source}" class="btn btn-secondary" style="margin-top: 1rem;" download>
            Download PDF
          </a>
        </div>
      `;
        }
    }

    async function loadPDFJS() {
        return new Promise((resolve, reject) => {
            // Check if already loading
            if (document.querySelector('script[src*="pdf.min.js"]')) {
                const checkLoaded = setInterval(() => {
                    if (typeof pdfjsLib !== 'undefined') {
                        clearInterval(checkLoaded);
                        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                        resolve();
                    }
                }, 100);
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
            script.onload = () => {
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async function renderPage(pageNum) {
        if (!state.pdfDoc) return;
        if (pageNum < 1 || pageNum > state.pdfDoc.numPages) return;

        state.currentPage = pageNum;
        document.getElementById('currentPage').textContent = pageNum;

        const page = await state.pdfDoc.getPage(pageNum);
        const canvas = document.getElementById('pdfCanvas');
        const ctx = canvas.getContext('2d');

        // Calculate scale to fit container
        const container = canvas.parentElement;
        const containerWidth = container.clientWidth - 64;
        const containerHeight = container.clientHeight - 100;

        const viewport = page.getViewport({ scale: 1 });
        const scaleX = containerWidth / viewport.width;
        const scaleY = containerHeight / viewport.height;
        const scale = Math.min(scaleX, scaleY, 2) * state.currentZoom;

        const scaledViewport = page.getViewport({ scale });

        canvas.width = scaledViewport.width;
        canvas.height = scaledViewport.height;

        await page.render({
            canvasContext: ctx,
            viewport: scaledViewport
        }).promise;

        // Update thumbnail active state
        document.querySelectorAll('.pdf-thumb').forEach(thumb => {
            thumb.classList.toggle('active', parseInt(thumb.dataset.page) === pageNum);
        });
    }

    async function renderPDFThumbnails(item) {
        const sidebar = document.getElementById('pdfSidebar');
        if (!sidebar || !state.pdfDoc) return;

        const thumbContainer = sidebar.querySelector('.pdf-thumbs');
        thumbContainer.innerHTML = '';

        // Use pre-generated thumbs if available
        if (item.pdf?.thumbs?.length) {
            item.pdf.thumbs.forEach((thumbUrl, index) => {
                const thumb = document.createElement('img');
                thumb.className = 'pdf-thumb';
                thumb.src = thumbUrl;
                thumb.dataset.page = index + 1;
                thumb.alt = `Page ${index + 1}`;
                thumb.loading = 'lazy';
                if (index === 0) thumb.classList.add('active');
                thumb.addEventListener('click', () => renderPage(index + 1));
                thumbContainer.appendChild(thumb);
            });
            return;
        }

        // Generate thumbnails from PDF
        for (let i = 1; i <= Math.min(state.pdfDoc.numPages, 10); i++) {
            const page = await state.pdfDoc.getPage(i);
            const viewport = page.getViewport({ scale: 0.2 });

            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            canvas.className = 'pdf-thumb';
            canvas.dataset.page = i;
            if (i === 1) canvas.classList.add('active');

            const ctx = canvas.getContext('2d');
            await page.render({
                canvasContext: ctx,
                viewport
            }).promise;

            canvas.addEventListener('click', () => renderPage(i));
            thumbContainer.appendChild(canvas);
        }
    }

    // ========================================
    // Image Viewer
    // ========================================
    function renderImageViewer(container, item) {
        const viewer = document.createElement('div');
        viewer.className = 'image-viewer';

        const img = document.createElement('img');
        img.src = item.source;
        img.alt = item.title;
        img.loading = 'lazy';

        // Toggle zoom on click
        img.addEventListener('click', () => {
            state.isZoomed = !state.isZoomed;
            viewer.classList.toggle('zoomed', state.isZoomed);
        });

        viewer.appendChild(img);
        container.appendChild(viewer);
    }

    // ========================================
    // Modal Controls
    // ========================================
    function setupModalControls() {
        const modal = elements.modal;
        if (!modal) return;

        // Close button
        modal.querySelector('.modal-close')?.addEventListener('click', closeViewer);

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeViewer();
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('open')) {
                closeViewer();
            }
        });

        // Zoom controls
        modal.querySelector('[data-action="zoomIn"]')?.addEventListener('click', () => {
            state.currentZoom = Math.min(3, state.currentZoom + 0.25);
            renderPage(state.currentPage);
        });

        modal.querySelector('[data-action="zoomOut"]')?.addEventListener('click', () => {
            state.currentZoom = Math.max(0.5, state.currentZoom - 0.25);
            renderPage(state.currentPage);
        });
    }

    // ========================================
    // Navigation
    // ========================================
    function setupNavigation() {
        // Smooth scroll for nav links
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                if (href === '#') return;

                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });

        // Mobile nav toggle
        const navToggle = document.querySelector('.nav-toggle');
        const navLinks = document.querySelector('.nav-links');

        navToggle?.addEventListener('click', () => {
            const isOpen = navLinks?.classList.toggle('open');
            navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });

        // Close mobile menu when clicking a link
        navLinks?.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('open');
                navToggle?.setAttribute('aria-expanded', 'false');
            });
        });
    }

    // ========================================
    // Contact Form
    // ========================================
    function setupContactForm() {
        const form = document.getElementById('contactForm');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const name = form.querySelector('[name="name"]')?.value || '';
            const email = form.querySelector('[name="email"]')?.value || '';
            const message = form.querySelector('[name="message"]')?.value || '';

            const subject = encodeURIComponent(`Inquiry from ${name}`);
            const body = encodeURIComponent(`From: ${name}\nEmail: ${email}\n\n${message}`);

            window.location.href = `mailto:hello@dedolytics.org?subject=${subject}&body=${body}`;
        });
    }

    // ========================================
    // Intersection Observer for Animations
    // ========================================
    function setupScrollAnimations() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        document.querySelectorAll('.service-card, .process-step, .outcome-item, .feature-card').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(el);
        });

        // Add visible styles
        const style = document.createElement('style');
        style.textContent = `
      .service-card.visible, .process-step.visible, .outcome-item.visible, .feature-card.visible {
        opacity: 1 !important;
        transform: translateY(0) !important;
      }
    `;
        document.head.appendChild(style);
    }

    // ========================================
    // Kindworth Page
    // ========================================
    function setupKindworthGallery() {
        // Check if we're on the Kindworth page
        const kindworthGallery = document.getElementById('kindworthGallery');
        if (!kindworthGallery || !state.manifest) return;

        const track = kindworthGallery.querySelector('.gallery-track');
        if (!track) return;

        // Filter Kindworth items
        const kindworthItems = state.manifest.items.filter(item => item.category === 'kindworth');

        if (kindworthItems.length === 0) {
            track.innerHTML = '<div class="gallery-empty"><p>No Kindworth assets found.</p></div>';
            return;
        }

        track.innerHTML = '';
        kindworthItems.forEach((item, index) => {
            const card = createGalleryCard(item, index);
            track.appendChild(card);
        });

        // Setup scroll navigation buttons
        const prevBtn = document.getElementById('kwNavPrev');
        const nextBtn = document.getElementById('kwNavNext');
        const scrollAmount = 340; // card width + gap

        prevBtn?.addEventListener('click', () => {
            track.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
        });
        nextBtn?.addEventListener('click', () => {
            track.scrollBy({ left: scrollAmount, behavior: 'smooth' });
        });
    }

    // ========================================
    // Initialization
    // ========================================
    async function init() {
        console.log('Initializing Dedolytics Portfolio...');

        // Cache DOM elements
        elements = {
            galleryCarousel: document.getElementById('galleryCarousel'),
            galleryTrack: document.querySelector('.gallery-track'),
            galleryInfo: document.querySelector('.gallery-info'),
            navPrev: document.getElementById('navPrev'),
            navNext: document.getElementById('navNext'),
            modal: document.getElementById('viewerModal'),
        };

        // Load theme and manifest
        await Promise.all([loadTheme(), loadManifest()]);

        // Setup components
        if (state.manifest) {
            renderGallery('dashboard');
            setupKindworthGallery();
        }

        setupCarouselInput();
        setupModalControls();
        setupNavigation();
        setupContactForm();
        setupScrollAnimations();

        console.log('Portfolio initialized successfully');
    }

    // Wait for DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
