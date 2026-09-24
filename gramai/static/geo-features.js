/* PasumAI geo features (front end).

   1. GPS shows a place name ("Vandalur, Chengalpattu") instead of latitude and longitude.
   2. When a crop is listed, a ranked "where to sell" panel compares nearby mandis and buyers who want that crop.
   3. Farmers can add more photos to a listing; each is checked against the farm's GPS and marked geo-tag verified.
   4. Buyer classification (restaurant, retail chain, wholesale trader...) at sign-up and on the profile.

   Loaded after app.js and hooks its functions, so app.js itself needs only small template changes. */
(function (w) {
  'use strict';

  var placeCache = {};

  function L() { return (w.I18N && w.I18N.lang && w.I18N.lang()) || 'en'; }
  function E(s) { return typeof w.esc === 'function' ? w.esc(s) : String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function money(n) { return '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
  function authHeaders() { return { Authorization: 'Bearer ' + (typeof token !== 'undefined' ? token : '') }; }
  function note(msg) { if (typeof w.toast === 'function') w.toast(msg); }

  /* ---------- 1. place names ---------- */

  function placeFor(lat, lon) {
    var key = Number(lat).toFixed(3) + ',' + Number(lon).toFixed(3) + ',' + L();
    if (placeCache[key]) return Promise.resolve(placeCache[key]);
    return w.api('/api/geo/reverse?lat=' + encodeURIComponent(lat) + '&lon=' + encodeURIComponent(lon) + '&lang=' + encodeURIComponent(L()))
      .then(function (p) { placeCache[key] = p; return p; });
  }

  function paintPlace(g) {
    var coords = Number(g.lat).toFixed(5) + ', ' + Number(g.lon).toFixed(5);
    var t = document.getElementById('gpsText');
    if (t && t.classList.contains('success-status')) {
      t.innerHTML = '✓ Location verified: <b class="geo-place" title="' + E(coords) + '">📍 ' + E(g.place) + '</b>';
    }
    document.querySelectorAll('.verified-location-summary').forEach(function (el) {
      el.innerHTML = '📍 Verified location: <b class="geo-place" title="' + E(coords) + '">' + E(g.place) + '</b>';
    });
  }

  function decoratePlace() {
    if (typeof cropVerify === 'undefined' || !cropVerify || !cropVerify.g) return;
    var g = cropVerify.g;
    if (g.place) { paintPlace(g); return; }
    var t = document.getElementById('gpsText');
    if (t && t.classList.contains('success-status')) t.innerHTML = '✓ Location verified: <b>📍 finding the place name…</b>';
    placeFor(g.lat, g.lon).then(function (p) { g.place = p.place; paintPlace(g); }).catch(function () {
      g.place = 'Your farm location'; paintPlace(g);
    });
  }

  /* ---------- 2. where to sell ---------- */

  var KIND = { market: 'Mandi', demand: 'Wants your crop', buyer: 'Regular buyer' };
  var TYPE_ICON = { RESTAURANT: '🍽️', RETAIL_CHAIN: '🛒', WHOLESALE_TRADER: '🏪', PROCESSOR: '🏭', EXPORTER: '🚢', INSTITUTION: '🏥', KIRANA: '🏬', FPO_COOP: '🤝', INDIVIDUAL: '🏠' };

  function optionCard(o) {
    var icon = o.kind === 'market' ? '🏛️' : (TYPE_ICON[o.buyer_type] || '🧑‍💼');
    var tags = (o.tags || []).map(function (t) { return '<span class="geo-tag ' + (t === 'Best overall' ? 'best' : '') + '">' + E(t) + '</span>'; }).join('');
    var action = o.kind === 'demand'
      ? '<button class="secondary" onclick="closeModal();route(\'preorders\')">Respond in Pre-Orders →</button>'
      : (o.kind === 'market' ? '<button class="secondary" onclick="closeModal();route(\'crops\')">See price forecast →</button>' : '');
    return '<div class="geo-opt ' + (o.rank === 1 ? 'top' : '') + '" data-kind="' + o.kind + '">' +
      '<div class="geo-rank">' + o.rank + '</div>' +
      '<div class="geo-opt-main">' +
        '<div class="geo-opt-head"><b>' + icon + ' ' + E(o.name) + '</b>' + tags + '</div>' +
        '<div class="geo-opt-sub">' + E(o.type_label) + ' · ' + E(KIND[o.kind]) + (o.verified ? ' · ✓ verified' : '') + '</div>' +
        '<div class="geo-opt-place">📍 ' + E(o.place) + ' · <b>' + o.distance_km + ' km</b> away</div>' +
        '<div class="geo-opt-note">' + E(o.note || '') + (o.price_estimated ? ' · price estimated from nearby mandis' : '') + '</div>' +
        '<div class="geo-opt-nums">' +
          '<span>Price<b>' + money(o.price_per_qtl) + '</b></span>' +
          '<span>Transport<b>−' + money(o.transport_per_qtl) + '</b>' + (o.trip_cost ? '≈ ' + money(o.trip_cost) + ' per trip, ' + E(String(o.vehicle || 'vehicle').toLowerCase()) : E(o.vehicle || '')) + '</span>' +
          '<span>Fees &amp; freshness<b>−' + money((o.loss_per_qtl || 0) + (o.fee_per_qtl || 0)) + '</b>market fee, spoilage on the way</span>' +
          '<span class="keep">You keep<b>' + money(o.net_per_qtl) + '</b>per quintal</span>' +
          '<span>For your ' + o.sellable_qtl + ' qtl<b>' + money(o.est_total) + '</b></span>' +
        '</div>' +
        (action ? '<div class="geo-opt-actions">' + action + '</div>' : '') +
      '</div></div>';
  }

  function openBestOptions(hid, justListed) {
    var body = document.getElementById('modalBody');
    body.innerHTML = '<div class="geo-modal"><h2>🧭 Finding the best places to sell…</h2><p class="soft-note">Comparing mandis and buyers around your farm.</p></div>';
    document.getElementById('modal').classList.remove('hidden');
    w.api('/api/geo/harvest/' + hid + '/best-options').then(function (d) {
      var kinds = { all: d.options.length };
      d.options.forEach(function (o) { kinds[o.kind === 'market' ? 'market' : 'buyers'] = (kinds[o.kind === 'market' ? 'market' : 'buyers'] || 0) + 1; });
      body.innerHTML = '<div class="geo-modal">' +
        '<h2>' + (justListed ? '✅ Listed! ' : '') + '🧭 Best places to sell your ' + E(d.crop) + '</h2>' +
        '<p class="geo-from">From 📍 <b>' + E(d.origin.place || 'your farm') + '</b> · ' + d.quantity_qtl + ' qtl' + (d.price_date ? ' · prices of ' + E(d.price_date) : '') + '</p>' +
        '<div class="geo-suggest"><span>💡 Our suggestion</span><p>' + E(d.suggestion) + '</p></div>' +
        '<div class="geo-filter" id="geoFilter">' +
          '<button class="on" data-f="all">All (' + kinds.all + ')</button>' +
          '<button data-f="market">Mandis (' + (kinds.market || 0) + ')</button>' +
          '<button data-f="buyers">Buyers (' + (kinds.buyers || 0) + ')</button>' +
        '</div>' +
        '<div class="geo-list" id="geoList">' + d.options.map(optionCard).join('') + '</div>' +
        '<p class="geo-how">' + E(d.how) + '</p></div>';
      body.querySelectorAll('#geoFilter button').forEach(function (b) {
        b.onclick = function () {
          body.querySelectorAll('#geoFilter button').forEach(function (x) { x.classList.toggle('on', x === b); });
          body.querySelectorAll('.geo-opt').forEach(function (el) {
            var k = el.dataset.kind, f = b.dataset.f;
            el.style.display = (f === 'all' || (f === 'market' && k === 'market') || (f === 'buyers' && k !== 'market')) ? '' : 'none';
          });
        };
      });
    }).catch(function (e) {
      body.innerHTML = '<div class="geo-modal"><h2>🧭 Best places to sell</h2><div class="card error">' + E(e.message) + '</div></div>';
    });
  }

  /* ---------- 3. more photos, geo-tag verified ---------- */

  var STATUS = {
    GEO_VERIFIED: ['📍 Geo-tag verified', 'ok'],
    NEAR_FARM: ['Near the farm', 'warn'],
    FAR_FROM_FARM: ['Far from the farm', 'bad'],
    NO_GPS: ['No location', 'bad']
  };

  function blobUrl(url) {
    return fetch(url, { headers: authHeaders() }).then(function (r) { if (!r.ok) throw new Error('photo'); return r.blob(); })
      .then(function (b) { return URL.createObjectURL(b); });
  }

  function photoCard(p) {
    var st = STATUS[p.geo_status] || STATUS.NO_GPS;
    var dist = p.distance_m != null && p.geo_status !== 'NO_GPS' ? (p.distance_m < 1000 ? Math.round(p.distance_m) + ' m from the farm' : (p.distance_m / 1000).toFixed(1) + ' km from the farm') : '';
    return '<figure class="geo-photo"><div class="geo-img" data-url="' + E(p.url) + '"><span>Loading…</span></div>' +
      '<figcaption><span class="geo-badge ' + st[1] + '">' + st[0] + '</span>' +
      (p.place ? '<small>' + E(p.place) + '</small>' : '') + (dist ? '<small>' + dist + '</small>' : '') +
      (p.note ? '<small>' + E(p.note) + '</small>' : '') + '</figcaption></figure>';
  }

  function openHarvestPhotos(hid) {
    var body = document.getElementById('modalBody');
    document.getElementById('modal').classList.remove('hidden');
    body.innerHTML = '<div class="geo-modal"><h2>📷 Photos</h2><p class="soft-note">Loading…</p></div>';
    w.api('/api/geo/harvest/' + hid + '/photos').then(function (d) {
      body.innerHTML = '<div class="geo-modal">' +
        '<h2>📷 Photos of your crop</h2>' +
        '<p class="geo-from">' + d.verified_count + ' of ' + d.photos.length + ' photo(s) geo-tag verified. ' + E(d.rule) + '</p>' +
        '<div class="geo-photos">' + d.photos.map(photoCard).join('') + '</div>' +
        '<div class="geo-add"><h3>Add another photo</h3>' +
          '<p class="soft-note">Stand at your farm and take the photo now. We record where it was taken, so buyers can trust it.</p>' +
          '<input id="geoPhotoFile" class="control" type="file" accept="image/*" capture="environment">' +
          '<input id="geoPhotoNote" class="control" placeholder="Optional note, e.g. Ripe fruit, second plot">' +
          '<button class="primary" id="geoPhotoBtn">📍 Take location &amp; upload</button>' +
          '<div id="geoPhotoMsg" class="soft-note"></div></div></div>';
      body.querySelectorAll('.geo-img').forEach(function (el) {
        blobUrl(el.dataset.url).then(function (u) { el.innerHTML = '<img alt="Crop photo" src="' + u + '">'; })
          .catch(function () { el.innerHTML = '<span>Photo unavailable</span>'; });
      });
      document.getElementById('geoPhotoBtn').onclick = function () { uploadPhoto(hid); };
    }).catch(function (e) {
      body.innerHTML = '<div class="geo-modal"><h2>📷 Photos</h2><div class="card error">' + E(e.message) + '</div></div>';
    });
  }

  function uploadPhoto(hid) {
    var file = (document.getElementById('geoPhotoFile') || {}).files;
    var msg = document.getElementById('geoPhotoMsg');
    var btn = document.getElementById('geoPhotoBtn');
    if (!file || !file[0]) { msg.textContent = 'Choose or take a photo first.'; return; }
    btn.disabled = true;
    msg.textContent = 'Getting your location…';
    function send(lat, lon) {
      var fd = new FormData();
      fd.append('photo', file[0]);
      if (lat != null) { fd.append('latitude', lat); fd.append('longitude', lon); }
      fd.append('note', (document.getElementById('geoPhotoNote') || {}).value || '');
      msg.textContent = 'Uploading…';
      fetch('/api/geo/harvest/' + hid + '/photos', { method: 'POST', headers: authHeaders(), body: fd })
        .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail || 'Upload failed'); return j; }); })
        .then(function (p) {
          note(p.geo_status === 'GEO_VERIFIED' ? 'Photo added and geo-tag verified' : 'Photo added: ' + (STATUS[p.geo_status] || STATUS.NO_GPS)[0]);
          openHarvestPhotos(hid);
          if (typeof w.farmerCrops === 'function' && w.currentPage === 'crops') w.farmerCrops();
        })
        .catch(function (e) { btn.disabled = false; msg.textContent = e.message; });
    }
    if (!navigator.geolocation) { send(null, null); return; }
    navigator.geolocation.getCurrentPosition(
      function (pos) { send(pos.coords.latitude, pos.coords.longitude); },
      function () { msg.textContent = 'Location is off, so this photo will not be geo-tag verified.'; send(null, null); },
      { enableHighAccuracy: true, timeout: 12000 });
  }

  /* ---------- 4. buyer classification ---------- */

  var buyerTypes = null;
  function loadBuyerTypes() {
    if (buyerTypes) return Promise.resolve(buyerTypes);
    return fetch('/api/geo/buyer-types').then(function (r) { return r.json(); }).then(function (t) { buyerTypes = t; return t; });
  }

  function typeOptions(selected) {
    return '<option value="">Choose your business type</option>' + (buyerTypes || []).map(function (t) {
      return '<option value="' + t.code + '"' + (t.code === selected ? ' selected' : '') + '>' + t.icon + ' ' + E(t.label) + '</option>';
    }).join('');
  }

  function fillRegisterTypes() {
    loadBuyerTypes().then(function () {
      var sel = document.getElementById('rBuyerType');
      if (sel && sel.options.length < 2) sel.innerHTML = typeOptions('');
    });
  }

  function syncRegisterFields() {
    var box = document.getElementById('rBuyerFields');
    if (box) box.classList.toggle('hidden', typeof activeRole === 'undefined' || activeRole !== 'buyer');
  }


  /* ---------- 5. buyer discovery page ---------- */

  var disc = { lat: null, lon: null, crop: '', sort: 'auto' };
  var SORTS = [['auto', 'Best match for my business'], ['distance', 'Nearest first'], ['price', 'Lowest delivered price'], ['verified', 'Most geo-verified']];

  function discoverQuery() {
    var q = [];
    if (disc.lat != null) { q.push('lat=' + encodeURIComponent(disc.lat), 'lon=' + encodeURIComponent(disc.lon)); }
    if (disc.crop) q.push('crop=' + encodeURIComponent(disc.crop));
    q.push('sort=' + encodeURIComponent(disc.sort));
    return q.join('&');
  }

  function harvestCard(i) {
    var c = i.certificate;
    var vs = i.vs_market_pct == null ? '' :
      '<small class="' + (i.vs_market_pct <= 0 ? 'geo-good' : 'geo-warn') + '">' + (i.vs_market_pct <= 0 ? Math.abs(i.vs_market_pct) + '% below' : i.vs_market_pct + '% above') + ' today\'s mandi average</small>';
    var tags = (i.tags || []).map(function (t) { return '<span class="geo-tag ' + (i.rank === 1 && t.indexOf('Best') === 0 ? 'best' : '') + '">' + E(t) + '</span>'; }).join('');
    var photo = c && c.has_photo ? '<div class="geo-img" data-url="' + E(c.photo_url) + '"><span>🌾</span></div>' : '<div class="geo-img"><span>🌾</span></div>';
    var strip = typeof w.certStrip === 'function' && c ? w.certStrip(c) : '';
    return '<div class="geo-disc-card ' + (i.rank === 1 ? 'top' : '') + '">' +
      '<div class="geo-rank">' + i.rank + '</div>' + photo +
      '<div class="geo-disc-body">' +
        '<div class="geo-opt-head"><b>' + E(i.crop) + ' · Grade ' + E(i.grade || '—') + '</b>' + tags + '</div>' +
        '<div class="geo-opt-sub">' + E(i.seller_name) + ' · ' + E(i.seller_class) + (i.kyc_verified ? ' · ✓ KYC verified' : '') + '</div>' +
        '<div class="geo-opt-place">📍 ' + E(i.place) + ' · <b>' + i.distance_km + ' km</b> from you' + (i.location_exact ? '' : ' <small>(district level)</small>') + '</div>' +
        '<div class="geo-badges">' +
          (i.geo_verified_photos ? '<span class="geo-badge ok">📍 ' + i.geo_verified_photos + ' geo-tag verified photo' + (i.geo_verified_photos > 1 ? 's' : '') + '</span>' : '<span class="geo-badge bad">No geo-tagged photo</span>') +
          (c ? '<a class="geo-badge ok" href="' + E(c.verify_url) + '" target="_blank" rel="noopener">🔎 Scan-verified certificate</a>' : '<span class="geo-badge warn">No quality certificate</span>') +
        '</div>' + strip +
        '<div class="geo-opt-nums">' +
          '<span>Farmer\'s price<b>' + money(i.ask_price) + '</b>per quintal' + vs + '</span>' +
          '<span>+ Transport<b>' + money(i.transport_per_qtl) + '</b>' + (i.seller_transport ? 'seller delivers' : 'buyer pickup') + '</span>' +
          '<span class="keep">Delivered<b>' + money(i.landed_per_qtl) + '</b>per quintal</span>' +
          '<span>Available<b>' + Number(i.quantity_qtl).toLocaleString('en-IN') + ' qtl</b></span>' +
        '</div>' +
        '<div class="action-row">' +
          '<button class="primary" onclick="viewListing(' + i.id + ')">👁 View details</button>' +
          '<button class="secondary" onclick="openBuyerListingNegotiation(' + i.id + ',' + i.seller_id + ',' + Number(i.ask_price || 0) + ')">🤝 Negotiate</button>' +
          '<button class="secondary" onclick="openSellerChatFromListing(' + i.seller_id + ',' + i.id + ')">💬 Chat</button>' +
        '</div></div></div>';
  }

  function renderBuyerDiscover(d) {
    var type = (buyerTypes || []).filter(function (t) { return t.code === d.buyer_type; })[0];
    var typeChip = type ? '<span class="geo-type">' + type.icon + ' ' + E(type.label) + '</span>' :
      '<span class="geo-type none">Set your business type in Profile for better matches</span>';
    var el = document.getElementById('content');
    el.innerHTML = '<div class="geo-disc">' +
      '<div class="geo-disc-head"><span class="verified-badge">✓ PasumAI verified marketplace</span>' +
        '<h2>Harvests near you</h2>' +
        '<p>Distances are from 📍 <b>' + E(d.origin.place) + '</b> ' +
        '<button class="secondary" id="geoUseMe">📍 Use my current location</button></p>' +
        '<p>' + typeChip + ' <span class="geo-focus">Ranking favours <b>' + E(d.focus) + '</b></span></p></div>' +
      '<div class="geo-controls">' +
        '<label>Crop<select id="geoCrop" class="control"><option value="">All crops</option>' +
          d.crops.map(function (c) { return '<option' + (c === disc.crop ? ' selected' : '') + '>' + E(c) + '</option>'; }).join('') + '</select></label>' +
        '<label>Sort by<select id="geoSort" class="control">' +
          SORTS.map(function (s) { return '<option value="' + s[0] + '"' + (s[0] === disc.sort ? ' selected' : '') + '>' + s[1] + '</option>'; }).join('') + '</select></label>' +
      '</div>' +
      '<div class="geo-list">' + (d.items.length ? d.items.map(harvestCard).join('') : '<div class="empty">No harvests match. Try another crop.</div>') + '</div>' +
      '<p class="geo-how">' + E(d.how) + '</p></div>';
    el.querySelectorAll('.geo-img[data-url]').forEach(function (n) {
      blobUrl(n.dataset.url).then(function (u) { n.innerHTML = '<img alt="Produce" src="' + u + '">'; }).catch(function () { });
    });
    document.getElementById('geoCrop').onchange = function () { disc.crop = this.value; loadBuyerDiscover(); };
    document.getElementById('geoSort').onchange = function () { disc.sort = this.value; loadBuyerDiscover(); };
    document.getElementById('geoUseMe').onclick = function () {
      if (!navigator.geolocation) { note('Location is not available in this browser'); return; }
      navigator.geolocation.getCurrentPosition(function (pos) {
        disc.lat = pos.coords.latitude; disc.lon = pos.coords.longitude; loadBuyerDiscover();
      }, function () { note('Allow location access to measure distance from where you are'); }, { enableHighAccuracy: true, timeout: 12000 });
    };
  }

  function loadBuyerDiscover() {
    var el = document.getElementById('content');
    return loadBuyerTypes().then(function () { return w.api('/api/geo/buyer/discover?' + discoverQuery()); })
      .then(renderBuyerDiscover)
      .catch(function (e) { el.innerHTML = '<div class="card error">' + E(e.message) + '</div>'; });
  }

  w.buyerDiscover = function () {
    document.getElementById('content').innerHTML = '<div class="empty">Finding harvests near you…</div>';
    return loadBuyerDiscover();
  };

  w.buyerTypeChip = function (code) {
    var t = (buyerTypes || []).filter(function (x) { return x.code === code; })[0];
    return t ? '<span class="geo-type" title="' + E(t.note) + '">' + t.icon + ' ' + E(t.label.split(' (')[0]) + '</span>' : '';
  };

  w.GeoFeatures = { typeOptions: typeOptions, loadBuyerTypes: loadBuyerTypes, placeFor: placeFor, buyerTypes: function () { return buyerTypes; } };
  w.openBestOptions = openBestOptions;
  w.openHarvestPhotos = openHarvestPhotos;

  /* ---------- hooks ---------- */

  function hook(name, after) {
    var orig = w[name];
    if (typeof orig !== 'function') return;
    w[name] = function () { var out = orig.apply(this, arguments); try { after.apply(this, arguments); } catch (e) { /* cosmetic only */ } return out; };
  }

  function init() {
    hook('renderVerifiedCropStep', decoratePlace);
    hook('selectRole', syncRegisterFields);
    hook('showAuthMode', function () { syncRegisterFields(); fillRegisterTypes(); });

    var pub = w.publishVerifiedCrop;
    if (typeof pub === 'function') {
      w.publishVerifiedCrop = async function () {
        var vid = (typeof cropVerify !== 'undefined' && cropVerify && cropVerify.ver) ? cropVerify.ver.verification_id : null;
        var out = await pub.apply(this, arguments);
        // The original closes the wizard only when the listing was saved.
        var modal = document.getElementById('modal');
        if (vid && modal && modal.classList.contains('hidden')) {
          try {
            var list = await w.api('/api/v2/v3/harvests');
            var mine = list.filter(function (h) { return Number(h.verification_id) === Number(vid); })
              .sort(function (a, b) { return b.id - a.id; })[0];
            if (mine) openBestOptions(mine.id, true);
          } catch (e) { /* the listing itself is already saved */ }
        }
        return out;
      };
    }
    fillRegisterTypes();
    syncRegisterFields();
    loadBuyerTypes();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
