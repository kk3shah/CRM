export function initMicroInteractions() {
  initMagneticButtons();
  initTiltCards();
  initCardLightEffect();
  initCounterAnimation();
  initTrustCounters();
  initNavLogoShimmer();
  initDashboardParallax();
}

function initMagneticButtons() {
  const buttons = document.querySelectorAll('[data-magnetic]');

  buttons.forEach((btn) => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;

      const strength = 0.3;
      btn.style.transform = `translate(${x * strength}px, ${y * strength}px)`;
    });

    btn.addEventListener('mouseleave', () => {
      btn.style.transform = '';
      btn.style.transition = 'transform 0.5s cubic-bezier(0.23, 1, 0.32, 1)';
      setTimeout(() => {
        btn.style.transition = '';
      }, 500);
    });
  });
}

function initTiltCards() {
  const cards = document.querySelectorAll('[data-tilt]');

  cards.forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;

      const tiltX = (0.5 - y) * 12;
      const tiltY = (x - 0.5) * 12;

      card.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale3d(1.03, 1.03, 1.03)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
      card.style.transition = 'transform 0.6s cubic-bezier(0.23, 1, 0.32, 1)';
      setTimeout(() => {
        card.style.transition = 'border-color 0.4s ease, box-shadow 0.4s ease';
      }, 600);
    });

    card.addEventListener('mouseenter', () => {
      card.style.transition = 'none';
    });
  });
}

function initCardLightEffect() {
  const cards = document.querySelectorAll('.project-card, .service-card');

  cards.forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;

      card.style.setProperty('--mouse-x', `${x}%`);
      card.style.setProperty('--mouse-y', `${y}%`);
    });
  });
}

function initCounterAnimation() {
  const counters = document.querySelectorAll('.outcome-counter');

  counters.forEach(counter => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(counter);
          observer.unobserve(counter);
        }
      });
    }, { threshold: 0.5 });

    observer.observe(counter);
  });
}

function initTrustCounters() {
  const counters = document.querySelectorAll('.trust-number');

  counters.forEach(counter => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(counter);
          observer.unobserve(counter);
        }
      });
    }, { threshold: 0.5 });

    observer.observe(counter);
  });
}

function animateCounter(el) {
  const target = parseFloat(el.dataset.target);
  const decimals = parseInt(el.dataset.decimals) || 0;
  const prefix = el.dataset.prefix || '';
  const duration = 2000;
  const start = performance.now();

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = target * eased;

    el.textContent = prefix + (decimals > 0
      ? current.toFixed(decimals)
      : Math.round(current));

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

function initNavLogoShimmer() {
  const logo = document.querySelector('.nav-logo span');
  if (!logo) return;

  logo.addEventListener('mouseenter', () => {
    logo.style.background = 'linear-gradient(90deg, var(--text) 0%, var(--gold-light) 40%, var(--gold) 60%, var(--text) 100%)';
    logo.style.backgroundSize = '200% 100%';
    logo.style.webkitBackgroundClip = 'text';
    logo.style.backgroundClip = 'text';
    logo.style.webkitTextFillColor = 'transparent';
    logo.style.animation = 'heroShimmer 1.5s ease-in-out';
  });

  logo.addEventListener('mouseleave', () => {
    logo.style.background = '';
    logo.style.backgroundSize = '';
    logo.style.webkitBackgroundClip = '';
    logo.style.backgroundClip = '';
    logo.style.webkitTextFillColor = '';
    logo.style.animation = '';
  });
}

function initDashboardParallax() {
  const dashboards = document.querySelectorAll('.dashboard-float');
  if (!dashboards.length) return;

  const hero = document.querySelector('.hero');
  if (!hero) return;

  hero.addEventListener('mousemove', (e) => {
    const rect = hero.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5; // -0.5 to 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5;

    dashboards.forEach((dash, i) => {
      // Each dashboard moves at a different intensity for depth
      const depth = 1 + i * 0.4;
      const moveX = x * 20 * depth;
      const moveY = y * 12 * depth;

      // Combine with existing transforms
      const baseTransform = getComputedStyle(dash).getPropertyValue('--base-transform') || '';
      dash.style.transform = `${baseTransform} translate(${moveX}px, ${moveY}px)`;
    });
  });

  hero.addEventListener('mouseleave', () => {
    dashboards.forEach(dash => {
      dash.style.transform = '';
    });
  });
}

