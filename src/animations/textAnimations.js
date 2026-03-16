import gsap from 'gsap';

export function initHeroAnimations() {
  const title = document.querySelector('.hero-title');
  if (!title) return;

  // Split hero title into characters for staggered reveal
  const text = title.textContent.trim();
  title.innerHTML = '';
  // Remove background-clip text since we're splitting into spans
  title.style.webkitTextFillColor = 'unset';
  title.style.backgroundClip = 'unset';
  title.style.webkitBackgroundClip = 'unset';
  title.style.background = 'none';

  const chars = text.split('').map((char) => {
    const span = document.createElement('span');
    span.textContent = char === ' ' ? '\u00A0' : char;
    span.style.display = 'inline-block';
    span.style.opacity = '0';
    span.style.transform = 'translateY(80px) rotateX(-40deg)';
    span.style.willChange = 'transform, opacity';
    span.style.color = '#f0f0f0';
    title.appendChild(span);
    return span;
  });

  // Animate characters in with gold shimmer
  gsap.to(chars, {
    opacity: 1,
    y: 0,
    rotateX: 0,
    duration: 1,
    stagger: 0.04,
    ease: 'power3.out',
    delay: 0.3,
    onComplete: () => {
      // After reveal, add gold shimmer to each char sequentially
      gsap.to(chars, {
        color: '#c8a45e',
        duration: 0.3,
        stagger: 0.03,
        ease: 'power2.inOut',
        yoyo: true,
        repeat: 1,
      });
    },
  });

  // Hero subtitle
  const subtitle = document.querySelector('.hero-subtitle');
  if (subtitle) {
    subtitle.style.opacity = '0';
    gsap.to(subtitle, {
      opacity: 1,
      y: 0,
      duration: 0.8,
      ease: 'power3.out',
      delay: 0.8,
    });
    gsap.set(subtitle, { y: 20 });
  }

  // Hero services tags
  const tags = document.querySelectorAll('.hero-tag, .hero-tag-divider');
  if (tags.length) {
    tags.forEach((t) => (t.style.opacity = '0'));
    gsap.to(tags, {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 0.5,
      stagger: 0.08,
      ease: 'back.out(1.7)',
      delay: 1.1,
    });
    gsap.set(tags, { y: 15, scale: 0.9 });
  }

  // Hero CTA buttons
  const cta = document.querySelector('.hero-cta');
  if (cta) {
    Array.from(cta.children).forEach((c) => (c.style.opacity = '0'));
    gsap.to(cta.children, {
      opacity: 1,
      y: 0,
      duration: 0.6,
      stagger: 0.15,
      ease: 'power3.out',
      delay: 1.4,
    });
    gsap.set(cta.children, { y: 20 });
  }

  // Scroll indicator
  const scrollIndicator = document.querySelector('.hero-scroll-indicator');
  if (scrollIndicator) {
    scrollIndicator.style.opacity = '0';
    gsap.to(scrollIndicator, {
      opacity: 1,
      duration: 1,
      delay: 2.0,
      ease: 'power2.out',
    });
  }
}
