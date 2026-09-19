// BiteCheck Chrome Extension UI Controller
// Renders the Inline Buy-Box Safety Pill & Slide-Over Detail Drawer inside an isolated Shadow DOM.
// Guarantees zero style conflicts with Amazon's host page.

import { STATUS_COLORS, STATUS_LABELS, STATUS_ICONS, SEVERITY_COLORS, NOVA_DESCRIPTIONS } from './config.js';
import { findBuyBoxAnchor } from './dom.js';

let shadowRoot = null;
let hostElement = null;
let currentData = null;
let isDrawerOpen = false;

/**
 * Initializes or retrieves the Shadow DOM host
 */
export function getOrCreateShadowRoot() {
  if (shadowRoot && document.body.contains(hostElement)) {
    return shadowRoot;
  }

  // Remove stale host if any
  const existing = document.getElementById('bitecheck-extension-root');
  if (existing) existing.remove();

  hostElement = document.createElement('div');
  hostElement.id = 'bitecheck-extension-root';
  document.body.appendChild(hostElement);

  shadowRoot = hostElement.attachShadow({ mode: 'open' });
  injectShadowStyles(shadowRoot);

  return shadowRoot;
}

/**
 * Tears down all existing extension UI (used during SPA variant transitions)
 */
export function removeExistingUI() {
  if (hostElement) {
    hostElement.remove();
    hostElement = null;
    shadowRoot = null;
    currentData = null;
    isDrawerOpen = false;
  }
}

/**
 * Renders an inline loading pill under the buy box while the analysis runs
 */
export function renderLoadingPill() {
  const root = getOrCreateShadowRoot();

  let container = root.getElementById('bc-inline-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'bc-inline-container';
    root.appendChild(container);
  }

  container.innerHTML = `
    <div class="bc-pill bc-pill-loading">
      <div class="bc-pill-left">
        <span class="bc-spinner"></span>
        <span class="bc-brand-label">BiteCheck AI</span>
        <span class="bc-loading-text">Scanning regulatory circulars...</span>
      </div>
    </div>
  `;

  positionInlinePill();
}

/**
 * Renders the full safety verdict pill and sets up the slide-over drawer
 * @param {object} data - AnalyzeResponse contract
 */
export function renderAnalysis(data) {
  currentData = data;
  const root = getOrCreateShadowRoot();

  const verdict = data.verdict || { status: 'NO_DATA', score: 100, headline: '', summary: '' };
  const status = verdict.status || 'NO_DATA';
  const statusColor = STATUS_COLORS[status] || STATUS_COLORS.NO_DATA;
  const statusLabel = STATUS_LABELS[status] || status;
  const statusIcon = STATUS_ICONS[status] || 'ℹ';
  const score = typeof verdict.score === 'number' ? verdict.score : 100;

  // 1. Render Inline Buy-Box Pill
  let pillContainer = root.getElementById('bc-inline-container');
  if (!pillContainer) {
    pillContainer = document.createElement('div');
    pillContainer.id = 'bc-inline-container';
    root.appendChild(pillContainer);
  }

  pillContainer.innerHTML = `
    <div class="bc-pill bc-status-${status.toLowerCase()}" id="bc-trigger-btn" tabindex="0" role="button" aria-label="Open BiteCheck Safety Report">
      <div class="bc-pill-left">
        <svg class="bc-barcode-icon" width="20" height="15" viewBox="0 0 28 22" fill="none">
          <rect x="0" y="0" width="2" height="22" fill="#ffffff" />
          <rect x="3" y="0" width="1.5" height="22" fill="#ffffff" />
          <rect x="5.5" y="0" width="3" height="22" fill="#ffffff" />
          <rect x="9.5" y="0" width="1" height="22" fill="#ffffff" />
          <rect x="11.5" y="0" width="2" height="22" fill="#ffffff" />
          <rect x="14.5" y="0" width="1.5" height="11" fill="#ffffff" />
          <rect x="17" y="0" width="2" height="11" fill="#ffffff" />
          <rect x="20" y="0" width="1" height="11" fill="#ffffff" />
          <rect x="22" y="0" width="3" height="22" fill="#ffffff" />
          <rect x="26" y="0" width="1.5" height="22" fill="#ffffff" />
          <path d="M18.5 21C16.5 17.5 14 14.5 15.5 12.5C17.5 14.5 18 18 18.5 21Z" fill="#22c55e" />
          <path d="M18.5 21C20.5 17.5 23 14.5 21.5 12.5C19.5 14.5 19 18 18.5 21Z" fill="#16a34a" />
        </svg>
        <span class="bc-pill-status-tag" style="background-color: ${statusColor}22; color: ${statusColor}; border-color: ${statusColor}55;">
          <span class="bc-icon">${statusIcon}</span>
          <span>${statusLabel}</span>
        </span>
        <span class="bc-score-tag" style="color: ${statusColor};">
          <strong>${score}</strong><span class="bc-score-sub">/100</span>
        </span>
      </div>
      <div class="bc-pill-right">
        <span class="bc-cta-text">Safety Report</span>
        <svg class="bc-arrow-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </div>
    </div>
  `;

  // Attach click to open drawer
  const triggerBtn = pillContainer.querySelector('#bc-trigger-btn');
  if (triggerBtn) {
    triggerBtn.addEventListener('click', () => toggleDrawer(true));
    triggerBtn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleDrawer(true);
      }
    });
  }

  positionInlinePill();

  // 2. Render Slide-Over Detail Drawer
  renderDrawer(data);
}

/**
 * Inserts the inline pill into the Amazon buy box
 */
function positionInlinePill() {
  const root = getOrCreateShadowRoot();
  const pillContainer = root.getElementById('bc-inline-container');
  if (!pillContainer) return;

  const anchor = findBuyBoxAnchor();
  if (anchor) {
    // Inject near top of buy box
    if (!anchor.contains(hostElement)) {
      anchor.prepend(hostElement);
    }
  } else {
    // Floating badge fallback if no buy box detected
    pillContainer.classList.add('bc-floating-fallback');
  }
}

/**
 * Toggles drawer open/closed state
 */
export function toggleDrawer(open) {
  isDrawerOpen = typeof open === 'boolean' ? open : !isDrawerOpen;
  const root = getOrCreateShadowRoot();
  const drawer = root.getElementById('bc-drawer');
  const backdrop = root.getElementById('bc-backdrop');

  if (drawer && backdrop) {
    if (isDrawerOpen) {
      drawer.classList.add('bc-open');
      backdrop.classList.add('bc-open');
      document.body.style.overflow = 'hidden';
    } else {
      drawer.classList.remove('bc-open');
      backdrop.classList.remove('bc-open');
      document.body.style.overflow = '';
    }
  }
}

/**
 * Renders the Slide-Over Drawer DOM structure
 */
function renderDrawer(data) {
  const root = getOrCreateShadowRoot();

  let drawerWrapper = root.getElementById('bc-drawer-wrapper');
  if (!drawerWrapper) {
    drawerWrapper = document.createElement('div');
    drawerWrapper.id = 'bc-drawer-wrapper';
    root.appendChild(drawerWrapper);
  }

  const prod = data.product || {};
  const verdict = data.verdict || {};
  const status = verdict.status || 'NO_DATA';
  const statusColor = STATUS_COLORS[status] || STATUS_COLORS.NO_DATA;
  const statusLabel = STATUS_LABELS[status] || status;
  const statusIcon = STATUS_ICONS[status] || 'ℹ';
  const score = typeof verdict.score === 'number' ? verdict.score : 100;
  const findings = data.findings || [];
  const nut = data.nutrition;

  // Build findings HTML
  let findingsHtml = '';
  if (findings.length === 0) {
    findingsHtml = `
      <div class="bc-clean-banner">
        <div class="bc-clean-icon">✓</div>
        <div>
          <strong>Clean Regulatory Record</strong>
          <p>No adverse recall, contamination, or misbranding orders found for this product or brand across official regulator records.</p>
        </div>
      </div>
    `;
  } else {
    findingsHtml = findings.map((f) => {
      const sevColor = SEVERITY_COLORS[f.severity] || '#EA580C';
      const hasBatches = f.batches && f.batches.length > 0;
      
      const batchesHtml = hasBatches
        ? `<div class="bc-batch-alert">
             <span class="bc-batch-title">⚠️ Affected Batches:</span>
             <span class="bc-batch-codes">${f.batches.join(', ')}</span>
             <p class="bc-batch-hint">Check the batch code printed on your physical pack before consumption.</p>
           </div>`
        : '';

      const citationsHtml = (f.citations || []).map((c) => `
        <div class="bc-citation-card">
          <div class="bc-citation-header">
            <span class="bc-cit-label">${escapeHtml(c.label)}</span>
            <span class="bc-cit-issuer">${escapeHtml(c.issuer || '')}</span>
            <span class="bc-cit-date">${escapeHtml(c.date || '')}</span>
          </div>
          ${c.excerpt ? `<div class="bc-cit-excerpt">"${escapeHtml(c.excerpt)}"</div>` : ''}
          ${c.sourceUrl ? `<a href="${escapeHtml(c.sourceUrl)}" target="_blank" rel="noopener noreferrer" class="bc-cit-link">View Official Circular →</a>` : ''}
        </div>
      `).join('');

      return `
        <div class="bc-finding-card">
          <div class="bc-finding-header">
            <span class="bc-sev-tag" style="background-color: ${sevColor}22; color: ${sevColor}; border-color: ${sevColor}55;">
              ${f.severity}
            </span>
            <span class="bc-type-tag">${f.type}</span>
            <span class="bc-scope-tag">${f.scope} SCOPE</span>
          </div>
          <h4 class="bc-finding-title">${escapeHtml(f.title)}</h4>
          <p class="bc-finding-detail">${escapeHtml(f.detail)}</p>
          ${batchesHtml}
          ${citationsHtml ? `<div class="bc-citations-section">${citationsHtml}</div>` : ''}
        </div>
      `;
    }).join('');
  }

  // Build nutrition / NOVA HTML
  let nutritionHtml = '';
  if (nut) {
    const novaInfo = NOVA_DESCRIPTIONS[nut.novaGroup] || NOVA_DESCRIPTIONS[1];
    const additivesHtml = nut.additives && nut.additives.length > 0
      ? nut.additives.map(a => `<span class="bc-additive-pill bc-risk-${(a.risk || 'watch').toLowerCase()}">${escapeHtml(a.name)} (${escapeHtml(a.ins || 'INS')})</span>`).join('')
      : '<span class="bc-empty-text">No flagged additives detected</span>';

    nutritionHtml = `
      <div class="bc-section">
        <h3 class="bc-section-title">Composition & Additives Intelligence</h3>
        <div class="bc-nova-box">
          <div class="bc-nova-badge bc-nova-${nut.novaGroup || 1}">NOVA ${nut.novaGroup || 1}</div>
          <div class="bc-nova-text">
            <strong>${novaInfo.label}</strong>
            <p>${novaInfo.desc}</p>
          </div>
        </div>
        <div class="bc-additives-box">
          <span class="bc-sub-label">Detected Additives:</span>
          <div class="bc-tags-flex">${additivesHtml}</div>
        </div>
      </div>
    `;
  }

  // Build Grievance CTA
  const grievanceHtml = data.grievance && data.grievance.eligible
    ? `<div class="bc-grievance-banner">
         <div class="bc-grievance-header">
           <span class="bc-alert-badge">FoSCoS Grievance Eligible</span>
           <p>This product holds verifiable regulator violations. You can generate a pre-formatted consumer complaint for the national FoSCoS portal.</p>
         </div>
         <button id="bc-draft-grievance-btn" class="bc-btn-danger">Draft Complaint Form</button>
       </div>`
    : '';

  drawerWrapper.innerHTML = `
    <div id="bc-backdrop" class="bc-backdrop"></div>
    <aside id="bc-drawer" class="bc-drawer" aria-label="BiteCheck Safety Inspection Bay">
      <!-- Drawer Header -->
      <div class="bc-drawer-header">
        <div class="bc-drawer-brand">
          <svg class="bc-barcode-icon" width="24" height="18" viewBox="0 0 28 22" fill="none">
            <rect x="0" y="0" width="2" height="22" fill="#ffffff" />
            <rect x="3" y="0" width="1.5" height="22" fill="#ffffff" />
            <rect x="5.5" y="0" width="3" height="22" fill="#ffffff" />
            <rect x="9.5" y="0" width="1" height="22" fill="#ffffff" />
            <rect x="11.5" y="0" width="2" height="22" fill="#ffffff" />
            <rect x="14.5" y="0" width="1.5" height="11" fill="#ffffff" />
            <rect x="17" y="0" width="2" height="11" fill="#ffffff" />
            <rect x="20" y="0" width="1" height="11" fill="#ffffff" />
            <rect x="22" y="0" width="3" height="22" fill="#ffffff" />
            <rect x="26" y="0" width="1.5" height="22" fill="#ffffff" />
            <path d="M18.5 21C16.5 17.5 14 14.5 15.5 12.5C17.5 14.5 18 18 18.5 21Z" fill="#22c55e" />
            <path d="M18.5 21C20.5 17.5 23 14.5 21.5 12.5C19.5 14.5 19 18 18.5 21Z" fill="#16a34a" />
          </svg>
          <span class="bc-brand-title">BiteCheck</span>
          <span class="bc-brand-badge">Food Safety AI</span>
        </div>
        <button id="bc-close-drawer-btn" class="bc-close-btn" title="Close Drawer (Esc)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <!-- Drawer Scrollable Body -->
      <div class="bc-drawer-body">
        <!-- Product Identity -->
        <div class="bc-identity-box">
          <div class="bc-brand-category">
            <span>${escapeHtml(prod.brand || 'Food Product')}</span>
            <span class="bc-dot-sep">•</span>
            <span>ASIN: ${escapeHtml(data.asin || '')}</span>
          </div>
          <h2 class="bc-prod-title">${escapeHtml(prod.name || 'Amazon Product')}</h2>
          <div class="bc-meta-pills">
            ${prod.netQuantity ? `<span class="bc-meta-tag">Net: ${escapeHtml(prod.netQuantity)}</span>` : ''}
            <span class="bc-meta-tag bc-fssai-tag">FSSAI: ${escapeHtml(prod.fssaiLicense || 'Not declared')}</span>
          </div>
        </div>

        <!-- Primary Verdict Card -->
        <div class="bc-verdict-card">
          <div class="bc-gauge-container">
            <svg viewBox="0 0 36 36" class="bc-circular-chart">
              <path class="bc-circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              <path class="bc-circle-progress" stroke-dasharray="${score}, 100" style="stroke: ${statusColor};" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            </svg>
            <div class="bc-gauge-number" style="color: ${statusColor};">
              <span>${score}</span>
              <small>/100</small>
            </div>
          </div>

          <div class="bc-verdict-info">
            <span class="bc-status-badge" style="background-color: ${statusColor}22; color: ${statusColor}; border-color: ${statusColor}55;">
              ${statusIcon} ${statusLabel}
            </span>
            <h3 class="bc-verdict-headline">${escapeHtml(verdict.headline || '')}</h3>
            <p class="bc-verdict-summary">${escapeHtml(verdict.summary || '')}</p>
          </div>
        </div>

        <!-- Findings Section -->
        <div class="bc-section">
          <div class="bc-section-header-row">
            <h3 class="bc-section-title">Grounded Regulatory Records (${findings.length})</h3>
          </div>
          <div class="bc-findings-list">${findingsHtml}</div>
        </div>

        <!-- Nutrition & Additives -->
        ${nutritionHtml}

        <!-- FoSCoS Grievance Action -->
        ${grievanceHtml}

        <!-- FoSCoS Modal (Hidden by default) -->
        <div id="bc-grievance-modal" class="bc-modal" style="display: none;">
          <div class="bc-modal-dialog">
            <div class="bc-modal-head">
              <h4>FoSCoS Consumer Grievance Draft</h4>
              <button id="bc-close-modal-btn" class="bc-close-btn">✕</button>
            </div>
            <textarea id="bc-grievance-textarea" class="bc-textarea" readonly></textarea>
            <div class="bc-modal-foot">
              <button id="bc-copy-grievance-btn" class="bc-btn-primary">Copy Complaint Text</button>
              <a href="https://foscos.fssai.gov.in" target="_blank" rel="noopener noreferrer" class="bc-btn-secondary">Open FoSCoS Portal ↗</a>
            </div>
          </div>
        </div>

        <!-- Disclaimer Footer -->
        <footer class="bc-footer">
          <p>${escapeHtml(data.disclaimer || 'Informational only, compiled from public regulator records. Not a laboratory result for the specific pack you are viewing. Always check the batch code printed on your package.')}</p>
        </footer>
      </div>
    </aside>
  `;

  // Attach Drawer Listeners
  const closeBtn = drawerWrapper.querySelector('#bc-close-drawer-btn');
  const backdrop = drawerWrapper.querySelector('#bc-backdrop');
  if (closeBtn) closeBtn.addEventListener('click', () => toggleDrawer(false));
  if (backdrop) backdrop.addEventListener('click', () => toggleDrawer(false));

  // Grievance drafting trigger
  const draftBtn = drawerWrapper.querySelector('#bc-draft-grievance-btn');
  const modal = drawerWrapper.querySelector('#bc-grievance-modal');
  const closeModalBtn = drawerWrapper.querySelector('#bc-close-modal-btn');
  const textarea = drawerWrapper.querySelector('#bc-grievance-textarea');
  const copyBtn = drawerWrapper.querySelector('#bc-copy-grievance-btn');

  if (draftBtn && modal && textarea) {
    draftBtn.addEventListener('click', () => {
      chrome.runtime.sendMessage(
        {
          type: 'DRAFT_GRIEVANCE',
          requestId: data.requestId,
          product: data.product,
          findings: data.findings,
        },
        (res) => {
          if (res && res.success && res.data) {
            textarea.value = res.data.grievanceText || '';
            modal.style.display = 'flex';
          }
        }
      );
    });

    if (closeModalBtn) {
      closeModalBtn.addEventListener('click', () => {
        modal.style.display = 'none';
      });
    }

    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        textarea.select();
        navigator.clipboard.writeText(textarea.value);
        copyBtn.textContent = 'Copied to Clipboard!';
        setTimeout(() => (copyBtn.textContent = 'Copy Complaint Text'), 2500);
      });
    }
  }

  // Escape key listener to close drawer
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isDrawerOpen) {
      toggleDrawer(false);
    }
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Injects self-contained styles into the Shadow DOM
 */
function injectShadowStyles(shadow) {
  const style = document.createElement('style');
  style.textContent = `
    /* CSS Reset for Shadow DOM */
    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
      -webkit-font-smoothing: antialiased;
    }

    /* 1. Inline Buy-Box Safety Pill */
    #bc-inline-container {
      margin: 10px 0 14px 0;
      width: 100%;
      z-index: 100;
    }

    .bc-pill {
      background: rgba(10, 15, 28, 0.94);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 12px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      cursor: pointer;
      color: #f8fafc;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .bc-pill:hover {
      background: rgba(15, 23, 42, 0.98);
      border-color: rgba(56, 189, 248, 0.4);
      transform: translateY(-1.5px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }

    .bc-pill-loading {
      cursor: default;
      background: rgba(10, 15, 28, 0.85);
    }

    .bc-pill-left {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .bc-barcode-icon {
      flex-shrink: 0;
    }

    .bc-pill-status-tag {
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .bc-score-tag {
      font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
      font-size: 13px;
    }

    .bc-score-sub {
      font-size: 10px;
      color: #94a3b8;
    }

    .bc-pill-right {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #38bdf8;
      font-size: 12px;
      font-weight: 600;
    }

    .bc-spinner {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(56, 189, 248, 0.2);
      border-top-color: #38bdf8;
      border-radius: 50%;
      animation: bc-spin 0.8s linear infinite;
    }

    .bc-loading-text {
      font-size: 12px;
      color: #94a3b8;
    }

    .bc-floating-fallback {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 340px;
      z-index: 2147483640;
    }

    /* 2. Slide-Over Detail Drawer */
    .bc-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      z-index: 2147483646;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
    }

    .bc-backdrop.bc-open {
      opacity: 1;
      pointer-events: auto;
    }

    .bc-drawer {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      width: 440px;
      max-width: 96vw;
      background: rgba(8, 12, 22, 0.96);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      border-left: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: -15px 0 45px rgba(0, 0, 0, 0.8);
      z-index: 2147483647;
      display: flex;
      flex-direction: column;
      transform: translateX(100%);
      transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
      color: #f8fafc;
    }

    .bc-drawer.bc-open {
      transform: translateX(0);
    }

    .bc-drawer-header {
      padding: 16px 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .bc-drawer-brand {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .bc-brand-title {
      font-size: 16px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #ffffff;
    }

    .bc-brand-badge {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 2px 6px;
      border-radius: 12px;
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }

    .bc-close-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #94a3b8;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }

    .bc-close-btn:hover {
      background: rgba(255, 255, 255, 0.15);
      color: #ffffff;
    }

    .bc-drawer-body {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .bc-drawer-body::-webkit-scrollbar {
      width: 5px;
    }

    .bc-drawer-body::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 3px;
    }

    /* Identity */
    .bc-identity-box {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .bc-brand-category {
      font-size: 12px;
      color: #94a3b8;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .bc-dot-sep {
      color: #64748b;
    }

    .bc-prod-title {
      font-size: 16px;
      font-weight: 700;
      line-height: 1.3;
      color: #f8fafc;
    }

    .bc-meta-pills {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 4px;
    }

    .bc-meta-tag {
      font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.05);
      color: #94a3b8;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .bc-fssai-tag {
      color: #38bdf8;
      border-color: rgba(56, 189, 248, 0.25);
    }

    /* Verdict Card */
    .bc-verdict-card {
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 14px;
      padding: 16px;
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .bc-gauge-container {
      position: relative;
      width: 72px;
      height: 72px;
      flex-shrink: 0;
    }

    .bc-circular-chart {
      display: block;
      width: 100%;
      height: 100%;
    }

    .bc-circle-bg {
      fill: none;
      stroke: rgba(255, 255, 255, 0.08);
      stroke-width: 3.4;
    }

    .bc-circle-progress {
      fill: none;
      stroke-width: 3.4;
      stroke-linecap: round;
      transition: stroke-dasharray 0.8s ease;
    }

    .bc-gauge-number {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
      font-size: 18px;
      font-weight: 800;
      line-height: 1;
    }

    .bc-gauge-number small {
      font-size: 9px;
      color: #64748b;
    }

    .bc-verdict-info {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .bc-status-badge {
      align-self: flex-start;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid transparent;
    }

    .bc-verdict-headline {
      font-size: 13px;
      font-weight: 700;
      line-height: 1.25;
      color: #ffffff;
    }

    .bc-verdict-summary {
      font-size: 12px;
      color: #94a3b8;
      line-height: 1.4;
    }

    /* Sections & Findings */
    .bc-section {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .bc-section-title {
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.02em;
      color: #e2e8f0;
    }

    .bc-findings-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .bc-finding-card {
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .bc-finding-header {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .bc-sev-tag, .bc-type-tag, .bc-scope-tag {
      font-size: 10px;
      font-weight: 700;
      padding: 1px 5px;
      border-radius: 3px;
      border: 1px solid transparent;
    }

    .bc-type-tag, .bc-scope-tag {
      background: rgba(255, 255, 255, 0.06);
      color: #94a3b8;
    }

    .bc-finding-title {
      font-size: 13px;
      font-weight: 700;
      color: #f1f5f9;
      line-height: 1.3;
    }

    .bc-finding-detail {
      font-size: 12px;
      color: #94a3b8;
      line-height: 1.4;
    }

    .bc-batch-alert {
      background: rgba(220, 38, 38, 0.12);
      border-left: 3px solid #dc2626;
      padding: 8px 10px;
      border-radius: 0 4px 4px 0;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .bc-batch-title {
      font-size: 11px;
      font-weight: 700;
      color: #fca5a5;
    }

    .bc-batch-codes {
      font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
      font-size: 12px;
      font-weight: 800;
      color: #ffffff;
      background: rgba(0, 0, 0, 0.35);
      padding: 2px 6px;
      border-radius: 3px;
      align-self: flex-start;
    }

    .bc-batch-hint {
      font-size: 11px;
      color: #fca5a5;
    }

    /* Citations */
    .bc-citations-section {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 4px;
    }

    .bc-citation-card {
      background: rgba(5, 7, 12, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 6px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .bc-citation-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      gap: 6px;
    }

    .bc-cit-label {
      font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
      font-weight: 700;
      color: #38bdf8;
    }

    .bc-cit-issuer {
      background: rgba(255, 255, 255, 0.08);
      padding: 1px 5px;
      border-radius: 3px;
      color: #e2e8f0;
      font-size: 10px;
    }

    .bc-cit-date {
      color: #64748b;
      font-size: 10px;
    }

    .bc-cit-excerpt {
      font-size: 11px;
      color: #cbd5e1;
      font-style: italic;
      line-height: 1.35;
      border-left: 2px solid #38bdf8;
      padding-left: 6px;
    }

    .bc-cit-link {
      font-size: 11px;
      color: #38bdf8;
      text-decoration: none;
      align-self: flex-start;
    }

    .bc-cit-link:hover {
      text-decoration: underline;
    }

    .bc-clean-banner {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      gap: 12px;
      color: #34d399;
      font-size: 12px;
      line-height: 1.4;
    }

    .bc-clean-icon {
      font-size: 18px;
      font-weight: 800;
    }

    /* Nutrition & NOVA */
    .bc-nova-box {
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .bc-nova-badge {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
      font-size: 12px;
      font-weight: 800;
      flex-shrink: 0;
    }

    .bc-nova-1 { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 2px solid #10b981; }
    .bc-nova-2 { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 2px solid #0ea5e9; }
    .bc-nova-3 { background: rgba(234, 88, 12, 0.2); color: #fb923c; border: 2px solid #ea580c; }
    .bc-nova-4 { background: rgba(220, 38, 38, 0.2); color: #f87171; border: 2px solid #dc2626; }

    .bc-nova-text strong {
      font-size: 12px;
      color: #f1f5f9;
      display: block;
    }

    .bc-nova-text p {
      font-size: 11px;
      color: #94a3b8;
    }

    .bc-additives-box {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .bc-sub-label {
      font-size: 11px;
      color: #64748b;
      text-transform: uppercase;
      font-weight: 700;
    }

    .bc-tags-flex {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }

    .bc-additive-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 4px;
    }

    .bc-risk-ok { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .bc-risk-watch { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .bc-risk-avoid { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .bc-empty-text { font-size: 12px; color: #64748b; font-style: italic; }

    /* Grievance */
    .bc-grievance-banner {
      background: linear-gradient(135deg, rgba(220, 38, 38, 0.15) 0%, rgba(15, 23, 42, 0.6) 100%);
      border: 1px solid rgba(220, 38, 38, 0.4);
      border-radius: 10px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .bc-alert-badge {
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      color: #f87171;
    }

    .bc-grievance-header p {
      font-size: 12px;
      color: #cbd5e1;
      line-height: 1.35;
      margin-top: 4px;
    }

    .bc-btn-danger {
      background: #dc2626;
      color: #ffffff;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s;
    }

    .bc-btn-danger:hover {
      background: #ef4444;
    }

    /* Modal */
    .bc-modal {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      z-index: 2147483648;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .bc-modal-dialog {
      background: #0d1321;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 12px;
      width: 100%;
      max-width: 480px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .bc-modal-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .bc-modal-head h4 {
      font-size: 14px;
      font-weight: 700;
    }

    .bc-textarea {
      width: 100%;
      height: 180px;
      background: rgba(5, 7, 12, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      color: #f8fafc;
      font-family: ui-monospace, monospace;
      font-size: 11px;
      padding: 10px;
      line-height: 1.4;
      resize: none;
    }

    .bc-modal-foot {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }

    .bc-btn-primary {
      background: #2563eb;
      color: #ffffff;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    .bc-btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      color: #f8fafc;
      border: 1px solid rgba(255, 255, 255, 0.12);
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 12px;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
    }

    /* Footer */
    .bc-footer {
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .bc-footer p {
      font-size: 11px;
      color: #64748b;
      line-height: 1.4;
    }

    @keyframes bc-spin {
      to { transform: rotate(360deg); }
    }
  `;

  shadow.appendChild(style);
}
