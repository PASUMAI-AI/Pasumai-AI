/* GRAM Saathi - multilingual, voice-enabled assistant UI.
 *
 * Talks to /api/ai/stream (server-sent events) so answers appear as they are
 * written, shows which platform data the assistant read, and supports speech in
 * and speech out in all 24 interface languages.
 */
(function (w) {
  'use strict';

  var SESSION = 'main';
  // 'auto' answers in the language the question was written in.
  var replyLang = localStorage.getItem('gram_reply_lang') || 'auto';
  var busy = false, listening = false, stick = true;
  var speakOn = localStorage.getItem('gram_tts') === '1';
  var handsFree = false;
  var lastAnswer = '';
  var lastAnswerLang = '';

  // Voice recording (mic -> backend STT) and playback (backend TTS) state.
  var mediaRecorder = null, mediaChunks = [], mediaStream = null;
  var ttsAudio = null;

  var VOICE_TAG = {
    en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN', ta: 'ta-IN', te: 'te-IN', bn: 'bn-IN',
    gu: 'gu-IN', kn: 'kn-IN', ml: 'ml-IN', pa: 'pa-IN', or: 'or-IN', as: 'as-IN',
    ur: 'ur-IN', ne: 'ne-NP', sa: 'sa-IN', ks: 'ur-IN', sd: 'sd-IN', kok: 'mr-IN',
    mai: 'hi-IN', doi: 'hi-IN', brx: 'hi-IN', mni: 'bn-IN', sat: 'hi-IN', raj: 'hi-IN'
  };

  function lang() {
    return (w.currentLang) || localStorage.getItem('gram_lang') || 'en';
  }
  function tag(l) { return VOICE_TAG[l || lang()] || 'en-IN'; }
  function authToken() {
    return (w.token) || localStorage.getItem('gram_token') || '';
  }
  function $(id) { return document.getElementById(id); }
  function T(s) { return w.I18N ? w.I18N.t(s) : s; }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ------------------------- markdown-lite renderer ------------------------ */
  function md(src) {
    var text = esc(src || '');
    var lines = text.split('\n'), out = [], list = null, table = null;

    function closeList() { if (list) { out.push('</' + list + '>'); list = null; } }
    function closeTable() {
      if (table) { out.push('</tbody></table></div>'); table = null; }
    }

    for (var i = 0; i < lines.length; i++) {
      var ln = lines[i];
      var raw = ln.trim();

      // Markdown table row
      if (/^\|.*\|$/.test(raw)) {
        var cells = raw.slice(1, -1).split('|').map(function (c) { return c.trim(); });
        if (/^[\s|:-]+$/.test(raw)) continue;           // separator row
        if (!table) {
          out.push('<div class="gs-tablewrap"><table class="gs-table"><thead><tr>' +
            cells.map(function (c) { return '<th>' + c + '</th>'; }).join('') +
            '</tr></thead><tbody>');
          table = 1;
        } else {
          out.push('<tr>' + cells.map(function (c) { return '<td>' + c + '</td>'; })
            .join('') + '</tr>');
        }
        continue;
      }
      closeTable();

      if (!raw) { closeList(); continue; }

      var h = raw.match(/^(#{1,4})\s+(.*)$/);
      if (h) { closeList(); out.push('<b class="gs-h">' + h[2] + '</b>'); continue; }

      var ul = raw.match(/^[-*•]\s+(.*)$/);
      if (ul) {
        if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul'; }
        out.push('<li>' + ul[1] + '</li>');
        continue;
      }
      var ol = raw.match(/^(\d+)[.)]\s+(.*)$/);
      if (ol) {
        if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol'; }
        out.push('<li>' + ol[2] + '</li>');
        continue;
      }
      closeList();
      out.push('<p>' + raw + '</p>');
    }
    closeList(); closeTable();

    return out.join('')
      .replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>')
      .replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<i>$2</i>')
      .replace(/`([^`\n]+)`/g, '<code>$1</code>')
      .replace(/\b(SELL NOW|SHIFT MARKET|WAIT|STORE|ACCEPT|NEGOTIATE)\b/g,
        '<span class="gs-decide">$1</span>');
  }

  /* ------------------------------ message DOM ------------------------------ */
  function atBottom() {
    var box = $('gsBody');
    if (!box) return true;
    return box.scrollHeight - box.scrollTop - box.clientHeight < 90;
  }

  function scroll(force) {
    var box = $('gsBody');
    if (!box) return;
    if (force || stick) box.scrollTop = box.scrollHeight;
  }

  function addMsg(who, html, cls) {
    var box = $('gsBody');
    if (!box) return null;
    var wrap = document.createElement('div');
    wrap.className = 'gs-msg gs-' + who + (cls ? ' ' + cls : '');
    wrap.innerHTML =
      '<div class="gs-avatar">' + (who === 'me' ? '🧑' : '🌿') + '</div>' +
      '<div class="gs-bubble"></div>';
    wrap.querySelector('.gs-bubble').innerHTML = html;
    box.appendChild(wrap);
    scroll();
    return wrap;
  }

  function typing(on) {
    var old = $('gsTyping');
    if (old) old.remove();
    if (!on) return;
    var box = $('gsBody');
    var el = document.createElement('div');
    el.id = 'gsTyping';
    el.className = 'gs-msg gs-bot';
    el.innerHTML = '<div class="gs-avatar">🌿</div>' +
      '<div class="gs-bubble gs-dots"><span></span><span></span><span></span></div>';
    box.appendChild(el);
    scroll();
  }

  var TOOL_LABEL = {
    get_price_forecast: 'Running the price forecast',
    compare_best_markets: 'Comparing markets by net price',
    get_market_prices: 'Reading mandi prices',
    list_crops_and_markets: 'Looking up crops and markets',
    get_my_listings: 'Reading your listings',
    get_my_orders: 'Reading your orders',
    get_my_harvests: 'Reading your harvests',
    get_my_rewards: 'Checking your reward points',
    get_my_payments: 'Checking your payments',
    get_my_profile: 'Reading your profile',
    search_buyers: 'Searching verified buyers',
    search_transport: 'Searching transporters',
    get_my_notifications: 'Reading your notifications',
    get_my_grievances: 'Reading your complaints',
    get_quality_certificates: 'Reading quality certificates',
    get_platform_stats: 'Reading platform statistics',
    explain_platform: 'Looking up how this works'
  };

  function toolNote(name) {
    var el = $('gsTool');
    if (!el) return;
    el.textContent = '⚙ ' + T(TOOL_LABEL[name] || name) + '…';
    el.classList.remove('hidden');
  }
  function clearToolNote() {
    var el = $('gsTool');
    if (el) el.classList.add('hidden');
  }

  /* ------------------------- structured data cards ------------------------- */
  /* Tool output is rendered as labelled tables and key/value rows. A raw JSON
     dump is unreadable on a phone and overflows the panel horizontally. */

  var HIDE_KEYS = { id: 1, user_id: 1, seller_id: 1, buyer_id: 1, listing_id: 1,
    farmer_id: 1, market_id: 1, verification_id: 1, group_id: 1, note: 1,
    photo_path: 1, certificate_path: 1, image_url: 1, quality_image: 1,
    provider_ref: 1, gateway_order_id: 1, gateway_payment_id: 1 };

  var MONEY_KEY = /(price|amount|total|rupees|cashback|fee|cost|income|value)/i;
  // "total_points" and "points_cost" are counts, not currency.
  var NOT_MONEY = /(point|count|score|index|rating|qty|quantity|qtl|days|pct|percent)/i;
  var PAISE_KEY = /paise$/i;
  var PCT_KEY = /(pct|percent|confidence|accuracy|agreement|stability|availability|reliability)/i;

  function humanize(key) {
    return String(key)
      .replace(/_paise$/i, '')
      .replace(/_qtl$/i, ' (qtl)')
      .replace(/_pct$/i, ' %')
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); })
      .replace(/\bId\b/g, 'ID').replace(/\bKyc\b/g, 'KYC')
      .replace(/\bUpi\b/g, 'UPI').replace(/\bQtl\b/g, 'qtl');
  }

  function money(n) {
    return 'Rs ' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }

  function fmtValue(key, v) {
    if (v === null || v === undefined || v === '') return '—';
    if (typeof v === 'boolean') return v ? 'Yes' : 'No';
    if (typeof v === 'number') {
      if (PAISE_KEY.test(key)) return money(v / 100);
      if (MONEY_KEY.test(key) && !NOT_MONEY.test(key)) return money(v);
      if (PCT_KEY.test(key)) return Number(v).toFixed(1) + '%';
      return Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }
    var s = String(v);
    // ISO timestamps become a plain date.
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m && s.length >= 10) return m[3] + '/' + m[2] + '/' + m[1];
    if (/^(OPEN|ACTIVE|PLACED|SUCCESS|VERIFIED|RESOLVED|CLOSED)$/i.test(s)) {
      return '<span class="gs-badge gs-good">' + esc(s) + '</span>';
    }
    if (/^(PENDING|PROCESSING|NOT_STARTED)$/i.test(s)) {
      return '<span class="gs-badge gs-warn">' + esc(s) + '</span>';
    }
    if (/^(FAILED|REJECTED|CANCELLED)$/i.test(s)) {
      return '<span class="gs-badge gs-bad">' + esc(s) + '</span>';
    }
    return esc(s.length > 90 ? s.slice(0, 90) + '…' : s);
  }

  function keepKeys(obj) {
    return Object.keys(obj).filter(function (k) {
      if (HIDE_KEYS[k]) return false;
      var v = obj[k];
      return v !== null && v !== undefined && v !== '' &&
        (typeof v !== 'object' || Array.isArray(v));
    });
  }

  /* Array of uniform objects -> a table, capped so the card stays readable. */
  function renderTable(arr) {
    var rows = arr.filter(function (r) { return r && typeof r === 'object'; });
    if (!rows.length) {
      return '<div class="gs-kv"><span>' + esc(T('No records')) + '</span></div>';
    }
    var cols = keepKeys(rows[0]).filter(function (c) {
      return typeof rows[0][c] !== 'object';
    }).slice(0, 6);
    if (!cols.length) return '';

    var shown = rows.slice(0, 8);
    var head = cols.map(function (c) { return '<th>' + esc(humanize(c)) + '</th>'; });
    var body = shown.map(function (r) {
      return '<tr>' + cols.map(function (c) {
        return '<td>' + fmtValue(c, r[c]) + '</td>';
      }).join('') + '</tr>';
    });
    var more = rows.length > shown.length
      ? '<div class="gs-more">+ ' + (rows.length - shown.length) + ' ' +
        esc(T('more')) + '</div>' : '';
    return '<div class="gs-tablewrap"><table class="gs-table"><thead><tr>' +
      head.join('') + '</tr></thead><tbody>' + body.join('') +
      '</tbody></table></div>' + more;
  }

  /* Flat object -> label/value rows. Nested arrays become their own tables. */
  function renderObject(obj) {
    var out = [], nested = [];
    keepKeys(obj).forEach(function (k) {
      var v = obj[k];
      if (Array.isArray(v)) {
        if (v.length && typeof v[0] === 'object') {
          nested.push('<div class="gs-sub">' + esc(humanize(k)) + '</div>' +
            renderTable(v));
        } else if (v.length) {
          out.push('<div class="gs-kv"><span>' + esc(humanize(k)) +
            '</span><b>' + esc(v.slice(0, 12).join(', ')) + '</b></div>');
        }
      } else {
        out.push('<div class="gs-kv"><span>' + esc(humanize(k)) +
          '</span><b>' + fmtValue(k, v) + '</b></div>');
      }
    });
    return out.join('') + nested.join('');
  }

  function renderPayload(d) {
    if (d === null || d === undefined) return '';
    if (typeof d !== 'object') {
      return '<div class="gs-kv"><b>' + esc(String(d)) + '</b></div>';
    }
    if (d.error) {
      return '<div class="gs-kv gs-kv-err"><b>' + esc(String(d.error)) + '</b></div>';
    }
    if (Array.isArray(d)) return renderTable(d);
    return renderObject(d);
  }

  /* Collapsed panel showing exactly which platform data backed the answer. */
  function sourceCard(used, data) {
    if (!used || !used.length) return '';
    var names = used.filter(function (v, i) { return used.indexOf(v) === i; });
    var body = names.map(function (n) {
      var html = '';
      try { html = renderPayload(data && data[n]); } catch (e) { html = ''; }
      if (!html) return '';
      return '<details class="gs-src"><summary>' + esc(T(TOOL_LABEL[n] || n)) +
        '</summary><div class="gs-srcbody">' + html + '</div></details>';
    }).join('');
    if (!body) return '';
    return '<div class="gs-sources"><div class="gs-srchead">' +
      esc(T('Data used')) + '</div>' + body + '</div>';
  }

  /* ------------------------------ send / stream ---------------------------- */
  function send(text, forceLang) {
    if (busy) return;
    var input = $('gsInput');
    var q = (text != null ? text : (input ? input.value : '')).trim();
    if (!q) return;
    if (input) input.value = '';
    hideChips();

    stick = true;
    addMsg('me', '<p>' + esc(q) + '</p>');
    scroll(true);
    busy = true;
    setSendState(true);
    typing(true);

    // Explicit language selection always wins; a language detected by voice
    // input for this one turn is used only when the picker is on 'auto', so
    // the answer is not re-detected independently at every stage.
    var effectiveReplyLang = (replyLang && replyLang !== 'auto')
      ? replyLang : (forceLang || replyLang);

    var bubble = null, acc = '', usedTools = [], toolData = {}, answeredIn = null;

    fetch('/api/ai/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + authToken()
      },
      body: JSON.stringify({
        message: q, lang: lang(), reply_lang: effectiveReplyLang,
        session_id: SESSION, state: w.currentState || null
      })
    }).then(function (r) {
      if (!r.ok || !r.body) throw new Error('HTTP ' + r.status);
      var reader = r.body.getReader(), dec = new TextDecoder(), buf = '';

      function pump() {
        return reader.read().then(function (res) {
          if (res.done) return finish();
          buf += dec.decode(res.value, { stream: true });
          var frames = buf.split('\n\n');
          buf = frames.pop();
          frames.forEach(handleFrame);
          return pump();
        });
      }

      function handleFrame(frame) {
        var ev = 'message', payload = '';
        frame.split('\n').forEach(function (line) {
          if (line.indexOf('event:') === 0) ev = line.slice(6).trim();
          else if (line.indexOf('data:') === 0) payload += line.slice(5).trim();
        });
        if (!payload) return;
        var d;
        try { d = JSON.parse(payload); } catch (e) { return; }

        if (ev === 'lang') { answeredIn = d.lang; showAnswerLang(d); return; }
        if (ev === 'tool') { toolNote(d.name); return; }
        if (ev === 'data') { usedTools = d.used_tools || []; toolData = d.data || {}; return; }
        if (ev === 'token') {
          clearToolNote();
          if (!bubble) { typing(false); bubble = addMsg('bot', ''); }
          acc += d.t;
          bubble.querySelector('.gs-bubble').innerHTML = md(acc);
          scroll();
          return;
        }
        if (ev === 'done') {
          if (bubble && usedTools.length) {
            bubble.querySelector('.gs-bubble')
              .insertAdjacentHTML('beforeend', sourceCard(usedTools, toolData));
          }
          if (d.fallback && bubble) bubble.classList.add('gs-fallback');
        }
      }

      return pump();
    }).catch(function (e) {
      typing(false);
      if (!bubble) {
        addMsg('bot', '<p>' + esc(T('I could not reach the assistant. Please try again.')) +
          '</p><p class="gs-err">' + esc(e.message) + '</p>', 'gs-error');
      }
      finish();
    });

    function finish() {
      typing(false);
      clearToolNote();
      busy = false;
      setSendState(false);
      if (acc) {
        lastAnswer = acc;
        lastAnswerLang = answeredIn;
        if (bubble) addMsgActions(bubble, acc, answeredIn);
        if (speakOn) speak(acc, answeredIn);
      }
      if (handsFree && !speakOn) startVoice();
    }
  }

  function addMsgActions(wrap, raw, forLang) {
    var b = wrap.querySelector('.gs-bubble');
    var bar = document.createElement('div');
    bar.className = 'gs-actions';
    bar.innerHTML =
      '<button title="' + esc(T('Read aloud')) + '">🔊</button>' +
      '<button title="' + esc(T('Copy')) + '">⧉</button>';
    bar.children[0].onclick = function () { speak(raw, forLang); };
    bar.children[1].onclick = function () {
      try { navigator.clipboard.writeText(raw); } catch (e) {}
      bar.children[1].textContent = '✓';
      setTimeout(function () { bar.children[1].textContent = '⧉'; }, 1200);
    };
    b.appendChild(bar);
  }

  function setSendState(on) {
    var b = $('gsSend');
    if (b) { b.disabled = on; b.textContent = on ? '…' : '➤'; }
  }

  /* --------------------------------- voice --------------------------------- */
  function setHint(text) {
    var h = $('gsHint');
    if (h) h.textContent = text;
  }

  function micSupported() {
    return !!(w.MediaRecorder && navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia);
  }

  /* Tap to start recording, tap again to stop and send - a plain toggle so
     "stop recording when requested" is an explicit user action. */
  function startVoice() {
    if (listening) { stopVoiceRecording(true); return; }

    // getUserMedia only exists on a secure origin (https:// or localhost).
    // Diagnose this explicitly - "mediaDevices is undefined" otherwise looks
    // identical to "unsupported browser" and is much more common in practice.
    if (w.isSecureContext === false) {
      alert(T('Voice input needs a secure connection (https:// or localhost). ' +
        'Open the site that way to use the microphone.'));
      return;
    }
    if (!micSupported()) {
      alert(T('Voice input needs microphone access in a modern browser.'));
      return;
    }
    stopSpeaking();
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      mediaStream = stream;
      mediaChunks = [];
      var mime = (w.MediaRecorder.isTypeSupported &&
        w.MediaRecorder.isTypeSupported('audio/webm')) ? 'audio/webm' : '';
      try {
        mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime })
                              : new MediaRecorder(stream);
      } catch (e) {
        setHint(T('Recording is not supported on this device.'));
        stream.getTracks().forEach(function (t) { t.stop(); });
        return;
      }
      mediaRecorder.ondataavailable = function (e) {
        if (e.data && e.data.size) mediaChunks.push(e.data);
      };
      mediaRecorder.onstop = onRecordingStop;
      mediaRecorder.start();
      listening = true;
      var m = $('gsMic');
      if (m) m.classList.add('gs-listening');
      setHint('🔴 ' + T('Listening… tap the mic to stop'));
    }).catch(function (e) {
      if (e && e.name === 'NotAllowedError') {
        setHint(T('Microphone permission was denied. Allow it in the browser\'s site settings.'));
      } else if (e && e.name === 'NotFoundError') {
        setHint(T('No microphone was found on this device.'));
      } else {
        setHint(T('Could not start the microphone.') + (e && e.message ? ' (' + e.message + ')' : ''));
      }
    });
  }

  function stopVoiceRecording(shouldSend) {
    listening = false;
    var m = $('gsMic');
    if (m) m.classList.remove('gs-listening');
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder._shouldSend = shouldSend !== false;
      try { mediaRecorder.stop(); } catch (e) {}
    } else {
      setHint(defaultHint());
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(function (t) { t.stop(); });
      mediaStream = null;
    }
  }

  /* Sends the recorded clip to the backend for transcription, then feeds the
     transcript into the existing chat pipeline like a typed message. */
  function onRecordingStop() {
    var shouldSend = mediaRecorder && mediaRecorder._shouldSend !== false;
    var mimeType = mediaChunks.length ? mediaChunks[0].type : 'audio/webm';
    var blob = new Blob(mediaChunks, { type: mimeType });
    mediaChunks = [];
    mediaRecorder = null;

    if (!shouldSend || !blob.size) { setHint(defaultHint()); return; }

    setHint('⏳ ' + T('Transcribing…'));
    var form = new FormData();
    form.append('audio', blob, 'speech.webm');
    // A language hint sharply improves Whisper's accuracy on short clips -
    // without one it can badly mis-transcribe (and mis-detect) non-English
    // speech. Explicit language selection wins; otherwise use the interface
    // language as the best guess, same bias detect_language() uses for text.
    var hint = (replyLang && replyLang !== 'auto') ? replyLang : lang();
    if (hint) form.append('language', hint);

    fetch('/api/voice/transcribe', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + authToken() },
      body: form
    }).then(function (r) {
      return r.json().then(function (d) { return { ok: r.ok, d: d }; });
    }).then(function (res) {
      setHint(defaultHint());
      if (!res.ok) {
        setHint(T(res.d && res.d.detail || 'Could not transcribe audio'));
        return;
      }
      var input = $('gsInput');
      if (input) input.value = res.d.text;
      send(res.d.text, res.d.language);
    }).catch(function () {
      setHint(T('Voice input failed. You can still type.'));
    });
  }

  function pickBrowserVoice(bcp) {
    var all = w.speechSynthesis ? speechSynthesis.getVoices() : [];
    if (!all.length) return null;
    var exact = all.filter(function (v) { return v.lang === bcp; });
    if (exact.length) return exact[0];
    var base = bcp.split('-')[0];
    var near = all.filter(function (v) { return v.lang.indexOf(base) === 0; });
    if (near.length) return near[0];
    var indian = all.filter(function (v) { return v.lang.indexOf('-IN') > 0; });
    return indian.length ? indian[0] : null;
  }

  function setSpeaking(on) {
    var stop = $('gsStopSpeak');
    if (stop) stop.classList.toggle('hidden', !on);
    var m = $('gsSpeak');
    if (m) m.classList.toggle('gs-speaking', on);
  }

  /* Browser speechSynthesis fallback, used only when the backend TTS call
     fails, so voice replies keep working even if gTTS or Groq is down. */
  function speakBrowser(clean, forLang) {
    if (!w.speechSynthesis) { setSpeaking(false); return; }
    var utt = new SpeechSynthesisUtterance(clean);
    var v = pickBrowserVoice(tag(forLang));
    if (v) { utt.voice = v; utt.lang = v.lang; } else { utt.lang = tag(forLang); }
    utt.rate = 0.95;
    utt.onstart = function () { setSpeaking(true); };
    utt.onend = function () { setSpeaking(false); if (handsFree) startVoice(); };
    utt.onerror = function () { setSpeaking(false); };
    speechSynthesis.speak(utt);
  }

  /* Reads an answer aloud in the same language it was answered in, via the
     backend TTS endpoint, falling back to the browser's own voices. */
  function speak(text, forLang) {
    stopSpeaking();
    var clean = String(text == null ? '' : text).replace(/[*#`|_>]/g, ' ')
      .replace(/\s{2,}/g, ' ').trim().slice(0, 1200);
    if (!clean) return;
    var speakLang = forLang || lang();
    setSpeaking(true);
    fetch('/api/voice/speak', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + authToken()
      },
      body: JSON.stringify({ text: clean, lang: speakLang })
    }).then(function (r) {
      if (!r.ok) throw new Error('tts-failed');
      return r.blob();
    }).then(function (blob) {
      var url = URL.createObjectURL(blob);
      ttsAudio = new Audio(url);
      ttsAudio.onended = function () {
        setSpeaking(false); URL.revokeObjectURL(url);
        if (handsFree) startVoice();
      };
      ttsAudio.onerror = function () { setSpeaking(false); URL.revokeObjectURL(url); };
      var p = ttsAudio.play();
      if (p && p.catch) p.catch(function () { speakBrowser(clean, speakLang); });
    }).catch(function () {
      if (!w.speechSynthesis) { setSpeaking(false); setHint(T('Voice is not available right now')); return; }
      speakBrowser(clean, speakLang);
    });
  }

  function stopSpeaking() {
    if (ttsAudio) { try { ttsAudio.pause(); } catch (e) {} ttsAudio = null; }
    if (w.speechSynthesis) { try { speechSynthesis.cancel(); } catch (e) {} }
    setSpeaking(false);
  }

  /* The speaker button reads the latest answer aloud right away, and keeps voice replies on
     for the answers that follow. Clicking it while it is speaking stops the voice and turns
     voice replies off again. */
  function readableLastMessage() {
    if (lastAnswer) return { text: lastAnswer, lang: lastAnswerLang || lang() };
    var bots = document.querySelectorAll('#gsBody .gs-bot');
    var el = bots.length ? bots[bots.length - 1] : null;
    return el ? { text: el.innerText || el.textContent || '', lang: lang() } : null;
  }

  function setSpeakOn(on) {
    speakOn = on;
    localStorage.setItem('gram_tts', on ? '1' : '0');
    var b = $('gsSpeak');
    b.classList.toggle('gs-on', on);
    b.title = on ? T('Voice replies on. Click to stop') : T('Read the answer aloud');
  }

  function toggleSpeak() {
    var b = $('gsSpeak');
    if (b.classList.contains('gs-speaking')) {
      stopSpeaking();
      setSpeakOn(false);
      return;
    }
    setSpeakOn(true);
    var m = readableLastMessage();
    if (m && m.text.trim()) speak(m.text, m.lang);
  }

  function toggleHandsFree() {
    // Hands-free now means the full voice agent that drives the app.
    if (w.SaathiVoice) {
      close();
      if (w.SaathiVoice.state.active) w.SaathiVoice.stop(); else w.SaathiVoice.start();
      return;
    }
    handsFree = !handsFree;
    var b = $('gsHands');
    b.classList.toggle('gs-on', handsFree);
    if (handsFree) {
      if (!speakOn) setSpeakOn(true);
      $('gsHint').textContent = T('Hands-free mode on');
      startVoice();
    } else {
      stopVoiceRecording(false); stopSpeaking();
      $('gsHint').textContent = defaultHint();
    }
  }

  /* ------------------------------- chips / shell --------------------------- */
  function defaultHint() {
    // One complete sentence: translating 'Ask in' as a fragment reads wrong.
    return T('Ask by voice or text in your own language.');
  }

  function hideChips() {
    var c = $('gsChips');
    if (c) c.classList.add('hidden');
  }

  function loadChips() {
    var c = $('gsChips');
    if (!c) return;
    fetch('/api/ai/suggestions?lang=' + encodeURIComponent(lang()),
      { headers: { 'Authorization': 'Bearer ' + authToken() } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.suggestions) return;
        c.innerHTML = d.suggestions.map(function (s) {
          return '<button data-no-i18n>' + esc(s) + '</button>';
        }).join('');
        Array.prototype.forEach.call(c.children, function (b) {
          b.onclick = function () { send(b.textContent); };
        });
        c.classList.remove('hidden');
      }).catch(function () {});
  }

  var WELCOME = 'Namaste! I am GRAM Saathi. I can read your listings, orders, ' +
    'prices, forecasts, rewards and payments. Ask me anything, by voice or text.';

  function welcome() {
    var box = $('gsBody');
    if (!box) return;
    box.innerHTML = '';
    // The transcript is data-no-i18n, so the DOM walker will never repaint this.
    // Wait for the translation before drawing it.
    var draw = function () { box.innerHTML = ''; addMsg('bot', '<p>' + esc(T(WELCOME)) + '</p>'); };
    if (w.I18N) w.I18N.ensure([WELCOME, defaultHint()]).then(function () {
      draw();
      var h = $('gsHint');
      if (h && !listening) h.textContent = defaultHint();
    });
    else draw();
    draw();
    loadChips();
  }

  function open() {
    $('gsPanel').classList.remove('hidden');
    $('gsFab').classList.add('gs-open');
    if (!$('gsBody').children.length) welcome();
    setTimeout(function () { var i = $('gsInput'); if (i) i.focus(); }, 60);
    updateLangPill();
  }

  function close() {
    $('gsPanel').classList.add('hidden');
    $('gsFab').classList.remove('gs-open');
    stopVoiceRecording(false); stopSpeaking();
    handsFree = false;
    var h = $('gsHands');
    if (h) h.classList.remove('gs-on');
  }

  function toggle() {
    var p = $('gsPanel');
    if (p.classList.contains('hidden')) open(); else close();
  }

  function expand() {
    $('gsPanel').classList.toggle('gs-full');
    scroll();
  }

  function reset() {
    fetch('/api/ai/reset?session_id=' + SESSION, {
      method: 'POST', headers: { 'Authorization': 'Bearer ' + authToken() }
    }).catch(function () {});
    welcome();
  }

  function showAnswerLang(d) {
    var p = $('gsLang');
    if (!p || replyLang !== 'auto') return;
    // Auto mode: show what the answer is actually coming back in.
    p.value = 'auto';
    p.title = T('Detected') + ': ' + (d.name || d.lang);
  }

  function buildLangPicker() {
    var sel = $('gsLang');
    if (!sel || sel.tagName !== 'SELECT') return;
    var opts = ['<option value="auto">' + esc(T('Auto')) + '</option>'];
    var L = w.LANGS || { en: ['English'] };
    Object.keys(L).forEach(function (k) {
      opts.push('<option value="' + k + '">' + esc(L[k][0]) + '</option>');
    });
    sel.innerHTML = opts.join('');
    sel.value = replyLang;
    sel.onchange = function () {
      replyLang = sel.value;
      localStorage.setItem('gram_reply_lang', replyLang);
      sel.title = replyLang === 'auto'
        ? T('Answers follow the language you type in')
        : T('Answers are always in this language');
      welcome();
    };
  }

  function updateLangPill() {
    buildLangPicker();
    var hint = $('gsHint');
    if (hint && !listening) hint.textContent = defaultHint();
    var input = $('gsInput');
    if (input) input.setAttribute('placeholder', T('Type your question here'));
  }

  /* --------------------------------- wiring -------------------------------- */
  /* --------------------------- produce photo upload ------------------------ */
  /* Runs the same YOLO grading and certificate pipeline the WhatsApp flow uses,
     but renders the outcome as a chat message instead of a WhatsApp reply. */
  function sendProducePhoto(file) {
    if (!file || busy) return;
    busy = true;
    setSendState(true);
    stick = true;
    addMsg('me', '<p>📷 ' + esc(T('Produce photo sent')) + '</p>');
    typing(true);

    var fd = new FormData();
    fd.append('photo', file);

    fetch('/api/ai/produce-photo', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + authToken() },
      body: fd
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
        return d;
      });
    }).then(function (d) {
      typing(false);
      if (!d.ok) {
        var why = d.reason === 'no_declaration'
          ? T('Tell me the crop and quantity first, for example: I have 20 kg rice.')
          : (d.error || T('The photo could not be inspected.'));
        addMsg('bot', '<p>' + esc(why) + '</p>', 'gs-error');
        return;
      }
      var lines =
        '<p><b>' + esc(T('Quality inspection complete')) + '</b></p>' +
        '<div class="gs-kv"><span>' + esc(T('Crop')) + '</span><b>' + esc(d.crop) + '</b></div>' +
        '<div class="gs-kv"><span>' + esc(T('Quantity')) + '</span><b>' +
          esc(d.quantity + ' ' + d.unit) + '</b></div>' +
        '<div class="gs-kv"><span>' + esc(T('Quality grade')) + '</span><b>' +
          esc(d.grade) + '</b></div>' +
        '<div class="gs-kv"><span>' + esc(T('Confidence')) + '</span><b>' +
          esc(d.confidence_percent) + '%</b></div>' +
        '<div class="gs-kv"><span>' + esc(T('Certificate')) + '</span><b>' +
          esc(d.certificate_number || '-') + '</b></div>';
      if (d.verification_status === 'mismatch') {
        lines += '<p>⚠️ ' + esc(T('The image suggests a different crop:')) + ' ' +
          esc(d.detected_crop || '') + '</p>';
      } else {
        lines += '<p>✅ ' + esc(T('Your KISANSETU inventory has been updated.')) + '</p>';
      }
      addMsg('bot', lines);
    }).catch(function (e) {
      typing(false);
      addMsg('bot', '<p>' + esc(T('Photo upload failed.')) + '</p><p class="gs-err">' +
        esc(e.message) + '</p>', 'gs-error');
    }).then(function () {
      busy = false;
      setSendState(false);
    });
  }

  function bind() {
    $('gsFab').onclick = toggle;
    $('gsClose').onclick = close;
    $('gsExpand').onclick = expand;
    $('gsReset').onclick = reset;
    $('gsSend').onclick = function () { send(); };
    $('gsMic').onclick = startVoice;
    $('gsPhoto').onclick = function () { $('gsPhotoInput').click(); };
    $('gsPhotoInput').onchange = function (e) {
      var f = e.target.files && e.target.files[0];
      e.target.value = '';
      sendProducePhoto(f);
    };
    $('gsSpeak').onclick = toggleSpeak;
    $('gsHands').onclick = toggleHandsFree;
    if ($('gsStopSpeak')) $('gsStopSpeak').onclick = stopSpeaking;
    $('gsBody').addEventListener('scroll', function () { stick = atBottom(); });
    $('gsInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    if (speakOn) $('gsSpeak').classList.add('gs-on');
    updateLangPill();
    if (w.speechSynthesis) speechSynthesis.onvoiceschanged = function () {};
  }

  w.GramSaathi = {
    toggle: toggle, open: open, close: close, send: send,
    onLanguageChange: function () {
      updateLangPill();
      stopSpeaking();
      if (!$('gsPanel').classList.contains('hidden')) welcome();
    }
  };

  // Keep the legacy entry points working for any existing markup or code.
  w.toggleChat = toggle;
  w.sendChat = function () { send(); };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else { bind(); }
})(window);
