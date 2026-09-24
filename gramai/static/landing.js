/* GRAM AI landing page + accessibility helpers.
 *
 * Built for farmers who may not read comfortably:
 *  - first visit opens a big, script-first language picker
 *  - every block has a Listen button that reads the (already translated) text aloud
 *  - the mobile-number box goes straight to OTP login, no email or password
 *  - inside the app, a Listen button in the header reads the current page
 *
 * Relies on globals from app.js (setLanguage, selectRole, showAuthMode,
 * showLoginMethod, sendOtp, logout, boot, LANGS, activeRole, currentLang).
 */
(function (w) {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };

  var LANG_EN = {
    en: 'English', hi: 'Hindi', mr: 'Marathi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali', gu: 'Gujarati',
    kn: 'Kannada', ml: 'Malayalam', pa: 'Punjabi', or: 'Odia', as: 'Assamese', ur: 'Urdu', ne: 'Nepali',
    sa: 'Sanskrit', ks: 'Kashmiri', sd: 'Sindhi', kok: 'Konkani', mai: 'Maithili', doi: 'Dogri', brx: 'Bodo',
    mni: 'Manipuri', sat: 'Santali', raj: 'Rajasthani'
  };

  var CROP_ART = {
    Banana: ['🍌', '#fff3c4'], Chilli: ['🌶️', '#ffe0d6'], Cotton: ['☁️', '#e8f1fb'], Groundnut: ['🥜', '#f6e6cf'],
    Maize: ['🌽', '#fff0b8'], Onion: ['🧅', '#f7e1ea'], Potato: ['🥔', '#f1e5d2'], Rice: ['🍚', '#eef6e6'],
    Soybean: ['🫘', '#efe8d6'], Tomato: ['🍅', '#ffe1dc'], Turmeric: ['🫚', '#fff0c9'], Wheat: ['🌾', '#fbefcf']
  };

  // Used only if the server cannot be reached, so the page never looks empty.
  var FALLBACK = [
    { crop: 'Onion', price: 2140, best: 2480, best_market: 'Oddanchatram, Tamil Nadu', change_pct: 4.2 },
    { crop: 'Tomato', price: 1860, best: 2210, best_market: 'Coimbatore, Tamil Nadu', change_pct: 2.1 },
    { crop: 'Wheat', price: 2310, best: 2460, best_market: 'Indore, Madhya Pradesh', change_pct: -0.8 },
    { crop: 'Turmeric', price: 13620, best: 14180, best_market: 'Erode, Tamil Nadu', change_pct: 1.4 }
  ];

  var prices = [];
  var speakingBtn = null;

  function rupees(n) { return '₹' + Math.round(n).toLocaleString('en-IN'); }
  function lang() { return w.currentLang || localStorage.getItem('gram_lang') || 'en'; }
  function tr(s) { return w.I18N ? w.I18N.t(s) : s; }
  function toastMsg(s) { if (typeof w.toast === 'function') w.toast(tr(s)); }

  /* ---------------- voice ---------------- */

  function voiceTag() {
    var L = w.LANGS && w.LANGS[lang()];
    return L ? L[1] : 'en-IN';
  }

  function pickVoice() {
    if (!w.speechSynthesis) return null;
    var all = speechSynthesis.getVoices(), want = voiceTag(), base = want.split('-')[0];
    return all.filter(function (v) { return v.lang === want; })[0] ||
      all.filter(function (v) { return v.lang.replace('_', '-').indexOf(base) === 0; })[0] || null;
  }

  function stop() {
    if (w.speechSynthesis) { try { speechSynthesis.cancel(); } catch (e) {} }
    if (speakingBtn) speakingBtn.classList.remove('speaking');
    speakingBtn = null;
  }

  function speak(text, btn) {
    if (!w.speechSynthesis) { toastMsg('Voice is not supported on this browser.'); return; }
    var wasThis = btn && btn === speakingBtn;
    stop();
    if (wasThis) return; // second tap on the same button stops reading
    text = String(text || '').replace(/[•|*#_>→‹›]/g, ' ').replace(/\s{2,}/g, ' ').trim().slice(0, 1500);
    if (!text) return;
    var u = new SpeechSynthesisUtterance(text), v = pickVoice();
    if (v) { u.voice = v; u.lang = v.lang; } else {
      u.lang = voiceTag();
      if (lang() !== 'en' && speechSynthesis.getVoices().length) {
        toastMsg('This phone has no voice for your language. Install it in phone settings under Text-to-speech.');
      }
    }
    u.rate = 0.9;
    u.onend = u.onerror = function () { if (speakingBtn === btn) stop(); };
    if (btn) { btn.classList.add('speaking'); speakingBtn = btn; }
    speechSynthesis.speak(u);
  }

  var READ_SEL = 'h1,h2,h3,p,li,blockquote,figcaption,.lp-card-row,.lp-card-best,.lp-calc-out > div,.lp-calc-field > span,.stat,.stat-card,label';

  function readableText(root) {
    var parts = [];
    root.querySelectorAll(READ_SEL).forEach(function (el) {
      if (el.closest('button,svg,[aria-hidden="true"],.lp-dialog,.hidden')) return;
      var parent = el.parentElement && el.parentElement.closest(READ_SEL);
      if (parent && root.contains(parent)) return; // already read as part of its parent
      var t = el.textContent.replace(/\s+/g, ' ').trim();
      if (t) parts.push(t);
    });
    if (!parts.length) parts.push(root.textContent.replace(/\s+/g, ' ').trim());
    return parts.join('. ').replace(/\.\s*\./g, '.');
  }

  /* ---------------- language picker ---------------- */

  function buildLangGrid() {
    var g = $('lpLangGrid');
    if (!g || !w.LANGS) return;
    g.innerHTML = Object.keys(w.LANGS).map(function (k) {
      return '<button type="button" data-lang="' + k + '" class="' + (k === lang() ? 'on' : '') + '">' +
        '<b>' + w.LANGS[k][0] + '</b><small>' + (LANG_EN[k] || k) + '</small></button>';
    }).join('');
    g.onclick = function (e) {
      var b = e.target.closest('button[data-lang]');
      if (!b) return;
      w.setLanguage(b.dataset.lang);
      closeLangPicker();
    };
  }

  function syncLangLabel() {
    var n = $('lpLangName');
    if (n && w.LANGS && w.LANGS[lang()]) n.textContent = w.LANGS[lang()][0];
    var g = $('lpLangGrid');
    if (g) g.querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.lang === lang()); });
  }

  function openLangPicker() { var pk = $('lpLangPicker'); if (!pk) return; buildLangGrid(); pk.classList.remove('hidden'); }
  function closeLangPicker() {
    var pk = $('lpLangPicker'); if (!pk) return;
    pk.classList.add('hidden');
    // Remember that the choice was offered, even if English was kept.
    // (app.js always stores gram_lang on load, so a separate flag is needed.)
    localStorage.setItem('gram_lang_chosen', '1');
  }

  /* ---------------- login dialog ---------------- */

  function method(m) {
    w.showLoginMethod(m);
    $('otpMethod').classList.toggle('active', m === 'otp');
    $('emailMethod').classList.toggle('active', m === 'email');
  }

  function openAuth(mode, role) {
    if (role) w.selectRole(role);
    w.showAuthMode(mode || 'login');
    $('lpAuth').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeAuth() {
    $('lpAuth').classList.add('hidden');
    document.body.style.overflow = '';
  }

  function startWithPhone(inputId) {
    var phone = ($(inputId).value || '').replace(/\D/g, '').slice(-10);
    openAuth('login', 'farmer');
    method('otp');
    $('loginPhone').value = phone;
    if (phone.length === 10) {
      w.sendOtp();
    } else {
      $('otpMessage').textContent = tr('Please enter your 10-digit mobile number.');
      $('loginPhone').focus();
    }
  }

  /* ---------------- prices + calculator ---------------- */

  function renderCards() {
    var box = $('lpCards');
    if (!box) return;
    box.innerHTML = prices.map(function (p) {
      var art = CROP_ART[p.crop] || ['🌱', '#eef6e6'];
      var down = p.change_pct < 0;
      var pct = p.best ? Math.max(8, Math.min(100, Math.round(p.price / p.best * 100))) : 60;
      return '<article class="lp-card">' +
        '<div class="lp-card-art" style="background:linear-gradient(' + art[1] + ',#fff)"><span aria-hidden="true">' + art[0] + '</span></div>' +
        '<div class="lp-card-body">' +
          '<h3>' + p.crop + '</h3>' +
          '<div class="lp-card-row"><span class="lp-card-price" data-no-i18n>' + rupees(p.price) + '</span>' +
            '<span class="lp-chip' + (down ? ' down' : '') + '" data-no-i18n>' + (down ? '▼ ' : '▲ ') + Math.abs(p.change_pct) + '%</span></div>' +
          '<div class="lp-card-row"><small>per quintal, change since last week</small></div>' +
          '<div class="lp-bar" aria-hidden="true"><span style="width:' + pct + '%"></span></div>' +
          '<div class="lp-card-best"><span aria-hidden="true">📍</span><span>Best price at ' + (p.best_market || '') + ': <b data-no-i18n>' + rupees(p.best) + '</b></span></div>' +
        '</div></article>';
    }).join('');
    if (w.I18N) w.I18N.apply(box);
  }

  function fillCalcCrops() {
    var sel = $('lpCalcCrop');
    if (!sel) return;
    var keep = sel.value || 'Onion';
    sel.innerHTML = prices.map(function (p) {
      var art = CROP_ART[p.crop] || ['🌱'];
      return '<option value="' + p.crop + '">' + art[0] + ' ' + p.crop + '</option>';
    }).join('');
    sel.value = prices.some(function (p) { return p.crop === keep; }) ? keep : prices[0].crop;
    calc();
  }

  function calc() {
    var sel = $('lpCalcCrop'), qtyEl = $('lpCalcQty');
    if (!sel || !qtyEl || !prices.length) return;
    var p = prices.filter(function (x) { return x.crop === sel.value; })[0] || prices[0];
    var qty = +qtyEl.value;
    var local = p.price * 0.82 * qty;
    var gram = p.price * 0.97 * qty;
    $('lpQtyOut').textContent = qty;
    $('lpLocal').textContent = rupees(local);
    $('lpGram').textContent = rupees(gram);
    $('lpGain').textContent = '+' + rupees(gram - local);
  }

  function loadPrices() {
    fetch('/api/public/prices')
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (d) {
        prices = (d.crops && d.crops.length) ? d.crops : FALLBACK;
        if (d.date && $('lpPriceDate')) $('lpPriceDate').textContent = '(' + new Date(d.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) + ')';
      })
      .catch(function () { prices = FALLBACK; })
      .then(function () { renderCards(); fillCalcCrops(); });
  }

  function scrollCards(dir) {
    var box = $('lpCards');
    if (box) box.scrollBy({ left: dir * Math.max(270, box.clientWidth * 0.8), behavior: 'smooth' });
  }

  /* ---------------- in-app Listen button ---------------- */

  function addAppListenButton() {
    var controls = document.querySelector('.header-controls');
    if (!controls || $('appListen')) return;
    var b = document.createElement('button');
    b.id = 'appListen';
    b.className = 'app-listen';
    b.type = 'button';
    b.title = 'Listen to this page';
    b.setAttribute('aria-label', 'Listen to this page');
    b.innerHTML = '<span aria-hidden="true">🔊</span><span class="app-listen-label">Listen</span>';
    b.onclick = function () {
      var title = ($('pageTitle') || {}).textContent || '';
      speak(title + '. ' + readableText($('content')), b);
    };
    controls.insertBefore(b, controls.firstChild);
  }


  /* Farm view (default: warm, larger, roomier) or Modern (black and lime). Remembered per browser. */
  function addThemeToggle() {
    var controls = document.querySelector('.header-controls');
    if (!controls || $('themeToggle')) return;
    var b = document.createElement('button');
    b.id = 'themeToggle';
    b.className = 'theme-toggle';
    b.type = 'button';
    function paint() {
      var farm = document.documentElement.dataset.appTheme !== 'modern';
      b.innerHTML = farm ? '<span aria-hidden="true">🖤</span><span>Modern look</span>'
                         : '<span aria-hidden="true">🌿</span><span>Farm view</span>';
      b.title = farm ? 'Switch to the black and lime look' : 'Switch to the simple farm view';
      b.setAttribute('aria-label', b.title);
    }
    b.onclick = function () {
      var next = document.documentElement.dataset.appTheme === 'modern' ? 'farm' : 'modern';
      document.documentElement.dataset.appTheme = next;
      try { localStorage.setItem('gram_app_theme', next); } catch (e) { /* private mode */ }
      paint();
    };
    paint();
    var listen = $('appListen');
    controls.insertBefore(b, listen ? listen.nextSibling : controls.firstChild);
  }

  /* ---------------- wiring ---------------- */

  function wrap(name, after) {
    var orig = w[name];
    if (typeof orig !== 'function') return;
    w[name] = function () {
      var out = orig.apply(this, arguments);
      after();
      return out;
    };
  }

  function init() {
    // Keep the header label and picker in step with every language change.
    wrap('setLanguage', syncLangLabel);
    wrap('setLanguage', function () { if (w.ScrollReveal) w.ScrollReveal.refresh(); });
    // Leaving or entering the app must never leave a dialog or voice hanging.
    wrap('logout', function () { closeAuth(); stop(); });
    wrap('boot', function () { closeAuth(); closeLangPicker(); stop(); });
    wrap('route', stop);

    syncLangLabel();
    loadPrices();
    addAppListenButton();
    addThemeToggle();

    var nav = $('lpNav');
    addEventListener('scroll', function () { if (nav) nav.classList.toggle('scrolled', scrollY > 10); }, { passive: true });

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      closeAuth();
      var lpk = $('lpLangPicker'); if (lpk && !lpk.classList.contains('hidden')) closeLangPicker();
      stop();
    });

    ['lpHeroPhone', 'lpCtaPhone', 'loginPhone', 'rPhone', 'loginOtp'].forEach(function (id) {
      var el = $(id);
      if (el) el.addEventListener('input', function () { el.value = el.value.replace(/\D/g, ''); });
    });

    if (w.speechSynthesis) speechSynthesis.getVoices(); // warm the voice list

    // First visit: ask for a language before anything else.
    if (!localStorage.getItem('gram_lang_chosen') && !localStorage.getItem('gram_token')) openLangPicker();


    // Splash cursor + scroll-reveal text (React Bits effects, vanilla ports).
    if (w.SplashCursor && !(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches)) {
      try { w.SplashCursor({ RAINBOW_MODE: true, parent: $('auth'), DENSITY_DISSIPATION: 6, VELOCITY_DISSIPATION: 3, SPLAT_RADIUS: 0.12 }); } catch (e) { /* no WebGL: skip */ }
    }
    if (w.ScrollReveal) {
      w.ScrollReveal.refresh();
      addEventListener('load', w.ScrollReveal.refresh);
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(w.ScrollReveal.refresh);
    }
    // Hero video: two stacked copies leapfrog each other so the loop never dips to blank.
    // The next copy starts ~1s before the current one ends and fades in over it.
    var vids = [$('lpHeroVideo'), $('lpHeroVideo2')];
    if (vids[0] && vids[1]) {
      var FADE_IN = 0.5, OVERLAP = 1, cur = 0, firstPlay = true;
      var RATE = 1.25; // hero video playback speed
      vids.forEach(function (v) { v.defaultPlaybackRate = RATE; v.playbackRate = RATE; v.addEventListener('loadedmetadata', function () { v.playbackRate = RATE; }); });
      var play = function (v) { v.playbackRate = RATE; var pl = v.play(); if (pl && pl.catch) pl.catch(function () {}); };
      vids[1].style.opacity = 0;
      (function tick() {
        var a = vids[cur], b = vids[1 - cur], d = a.duration, t = a.currentTime;
        if (d && isFinite(d) && !a.paused) {
          if (firstPlay) a.style.opacity = Math.min(t / FADE_IN, 1);
          var rem = d - t;
          if (rem < OVERLAP) {
            if (b.paused) { b.currentTime = 0; b.style.zIndex = 1; a.style.zIndex = 0; play(b); }
            b.style.opacity = Math.min(1, Math.max(0, 1 - rem / OVERLAP));
          }
          if (a.ended || rem < 0.04) {
            firstPlay = false;
            b.style.opacity = 1;
            a.pause(); a.style.opacity = 0;
            cur = 1 - cur;
          }
        } else if (a.ended) {
          b.currentTime = 0; b.style.opacity = 1; play(b); a.style.opacity = 0; cur = 1 - cur; firstPlay = false;
        }
        requestAnimationFrame(tick);
      })();
      var kick = function () { if (vids[cur].paused) play(vids[cur]); };
      kick();
      vids[0].addEventListener('canplay', kick);
      ['pointerdown', 'scroll', 'keydown', 'touchstart'].forEach(function (ev) { addEventListener(ev, kick, { once: true, passive: true }); });
    }

    // Scroll reveal for the sections below the hero.
    var rv = document.querySelectorAll('.lp-who, .lp-split, .lp-prices, .lp-soil-inner, .lp-night-inner, .lp-final');
    if ('IntersectionObserver' in w) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
      }, { threshold: 0.12 });
      rv.forEach(function (el) { el.classList.add('lp-rv'); io.observe(el); });
      document.querySelectorAll('.lp-why').forEach(function (el) { el.classList.add('lp-rv-stagger'); io.observe(el); });
    }

    // Phone mock drifts a little as you scroll.
    var phoneMock = document.querySelector('.lp-device.phone');
    if (phoneMock) addEventListener('scroll', function () {
      var r = phoneMock.getBoundingClientRect();
      if (r.top < innerHeight && r.bottom > 0) phoneMock.style.transform = 'rotate(-4deg) translateY(' + ((r.top - innerHeight / 2) * -0.06).toFixed(1) + 'px)';
    }, { passive: true });

    // First visit: ask for a language before anything else.
  }

  w.LP = {
    openAuth: openAuth, closeAuth: closeAuth, method: method, startWithPhone: startWithPhone,
    openLangPicker: openLangPicker, closeLangPicker: closeLangPicker,
    speakSection: function (id) {
      var el = $(id), btn = w.event && w.event.target && w.event.target.closest('button');
      if (el) speak(readableText(el), btn);
    },
    speakEl: function (el) {
      var btn = w.event && w.event.target && w.event.target.closest('button');
      speak(readableText(el), btn);
    },
    scrollCards: scrollCards, calc: calc, stop: stop
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
