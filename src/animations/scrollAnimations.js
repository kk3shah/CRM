import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export function initScrollAnimations() {
  // Nav scroll behavior
  const nav = document.getElementById('nav');
  ScrollTrigger.create({
    start: 'top -80',
    onUpdate: (self) => {
      nav?.classList.toggle('scrolled', self.progress > 0);
    },
  });

  // Scroll progress bar
  const progressBar = document.getElementById('scrollProgress');
  if (progressBar) {
    ScrollTrigger.create({
      start: 'top top',
      end: 'bottom bottom',
      onUpdate: (self) => {
        progressBar.style.width = `${self.progress * 100}%`;
      },
    });
  }

  // Section headers - reveal animation
  document.querySelectorAll('[data-animate="reveal"]').forEach((el) => {
    const label = el.querySelector('.section-label');
    const title = el.querySelector('.section-title');
    const subtitle = el.querySelector('.section-subtitle');

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: el,
        start: 'top 80%',
        toggleActions: 'play none none none',
      },
    });

    if (label) {
      tl.from(label, {
        y: 20,
        opacity: 0,
        duration: 0.6,
        ease: 'power3.out',
      });
    }

    if (title) {
      tl.from(title, {
        y: 30,
        opacity: 0,
        duration: 0.8,
        ease: 'power3.out',
      }, '-=0.3');
    }

    if (subtitle) {
      tl.from(subtitle, {
        y: 20,
        opacity: 0,
        duration: 0.6,
        ease: 'power3.out',
      }, '-=0.4');
    }
  });

  // Card animations - staggered entrance
  document.querySelectorAll('[data-animate="card"]').forEach((el) => {
    const delay = parseFloat(el.dataset.delay) || 0;

    gsap.from(el, {
      y: 60,
      opacity: 0,
      duration: 0.8,
      delay: delay,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        toggleActions: 'play none none none',
      },
    });
  });

  // Fade up animations
  document.querySelectorAll('[data-animate="fade-up"]').forEach((el) => {
    const delay = parseFloat(el.dataset.delay) || 0;

    gsap.from(el, {
      y: 30,
      opacity: 0,
      duration: 0.8,
      delay: delay,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        toggleActions: 'play none none none',
      },
    });
  });

  // Process step animations
  const processSteps = document.querySelectorAll('[data-animate="process-step"]');
  const processLineFill = document.getElementById('processLineFill');

  processSteps.forEach((el, index) => {
    const delay = parseFloat(el.dataset.delay) || 0;

    gsap.from(el, {
      y: 40,
      opacity: 0,
      duration: 0.7,
      delay: delay,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        toggleActions: 'play none none none',
        onEnter: () => {
          el.classList.add('active');
          // Animate the process line fill
          if (processLineFill) {
            const progress = ((index + 1) / processSteps.length) * 100;
            processLineFill.style.width = `${progress}%`;
          }
        },
      },
    });
  });

  // Nav active indicator
  initNavIndicator();
}

function initNavIndicator() {
  const sections = document.querySelectorAll('[data-section]');
  const navLinks = document.querySelectorAll('.nav-links a[data-nav]');
  const indicator = document.querySelector('.nav-indicator');

  if (!indicator || navLinks.length === 0) return;

  sections.forEach((section) => {
    ScrollTrigger.create({
      trigger: section,
      start: 'top center',
      end: 'bottom center',
      onEnter: () => updateIndicator(section.id),
      onEnterBack: () => updateIndicator(section.id),
    });
  });

  function updateIndicator(sectionId) {
    const activeLink = document.querySelector(`.nav-links a[data-nav="${sectionId}"]`);
    if (!activeLink) {
      indicator.classList.remove('visible');
      return;
    }

    navLinks.forEach((l) => l.classList.remove('active'));
    activeLink.classList.add('active');

    const rect = activeLink.getBoundingClientRect();
    const parentRect = activeLink.parentElement.parentElement.getBoundingClientRect();

    indicator.style.left = `${rect.left - parentRect.left}px`;
    indicator.style.width = `${rect.width}px`;
    indicator.classList.add('visible');
  }
}

export function refreshScrollTrigger() {
  ScrollTrigger.refresh();
}
