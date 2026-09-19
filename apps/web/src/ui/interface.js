// UI Controller for BiteCheck: Search, Demo Cards, Scanning HUD, Grounded Findings & FoSCoS Grievance
import { analyzeProduct, fetchTrending, draftGrievance, extractAsin } from '../api/client.js';
import { FIXTURES } from '../api/fixtures.js';
import { PARTICLE_STATES } from '../particles/particleEngine.js';
import { STATUS_COLORS, STATUS_LABELS, MACRO_CLASS_COLORS, ADDITIVE_RISK_COLORS } from '../config.js';

export function setupUI(engine) {
  // Navigation & Controls
  const topBar = document.getElementById('top-bar');
  const searchSection = document.getElementById('search-section');
  const linkInput = document.getElementById('link-input');
  const clearInputBtn = document.getElementById('clear-input-btn');
  const submitBtn = document.getElementById('submit-btn');
  const apiStatusText = document.getElementById('api-status-text');

  // Scanning HUD
  const scanningHud = document.getElementById('scanning-hud');
  const scanningStatus = document.getElementById('scanning-status');
  const pipeStepResolve = document.getElementById('step-resolve');
  const pipeStepKb = document.getElementById('step-kb');
  const pipeStepVerdict = document.getElementById('step-verdict');
  const pipeStepGround = document.getElementById('step-ground');

  // Left Macro Swarm HUD
  const molecularHud = document.getElementById('molecular-hud');
  const macroBadgesList = document.getElementById('macro-badges-list');

  // Right Inspection Bay
  const inspectionBay = document.getElementById('inspection-bay');
  const resetViewBtn = document.getElementById('reset-view-btn');

  // Identity & Verdict DOM Elements
  const bayBrand = document.getElementById('bay-brand');
  const bayCategory = document.getElementById('bay-category');
  const productName = document.getElementById('product-name');
  const productAsinBadge = document.getElementById('product-asin-badge');
  const productQuantity = document.getElementById('product-quantity');
  const productFssai = document.getElementById('product-fssai');

  const verdictStatusPill = document.getElementById('verdict-status-pill');
  const verdictCacheTag = document.getElementById('verdict-cache-tag');
  const verdictScore = document.getElementById('verdict-score');
  const scoreCirclePath = document.getElementById('score-circle-path');
  const verdictHeadline = document.getElementById('verdict-headline');
  const verdictSummary = document.getElementById('verdict-summary');

  const nonFoodNotice = document.getElementById('non-food-notice');
  const findingsSection = document.getElementById('findings-section');
  const findingsContainer = document.getElementById('findings-container');
  const findingsCount = document.getElementById('findings-count');

  const nutritionSection = document.getElementById('nutrition-section');
  const novaCard = document.getElementById('nova-card');
  const novaNumber = document.getElementById('nova-number');
  const novaLabel = document.getElementById('nova-label');
  const novaDesc = document.getElementById('nova-desc');
  const additivesTagsList = document.getElementById('additives-tags-list');
  const flagsContainer = document.getElementById('flags-container');

  const alternativesSection = document.getElementById('alternatives-section');
  const alternativesList = document.getElementById('alternatives-list');

  const grievanceActionCard = document.getElementById('grievance-action-card');
  const draftGrievanceBtn = document.getElementById('draft-grievance-btn');
  const bayDisclaimer = document.getElementById('bay-disclaimer');

  // Grievance Modal Elements
  const grievanceModal = document.getElementById('grievance-modal');
  const closeModalBtn = document.getElementById('close-modal-btn');
  const grievanceText = document.getElementById('grievance-text');
  const copyGrievanceBtn = document.getElementById('copy-grievance-btn');
  const copyBtnLabel = document.getElementById('copy-btn-label');

  // Demo Cards
  const demoCards = document.querySelectorAll('.demo-card');

  let currentAnalysis = null;
  let pipelineTimer = null;

  // 1. Engine Callbacks & Intro Sequencer
  engine.onIntroComplete = () => {
    topBar.classList.add('visible');
    searchSection.classList.add('visible');
    setTimeout(() => linkInput.focus(), 300);
  };

  // Input Clear Button toggle
  linkInput.addEventListener('input', () => {
    clearInputBtn.style.display = linkInput.value.trim() ? 'flex' : 'none';
  });

  clearInputBtn.addEventListener('click', () => {
    linkInput.value = '';
    clearInputBtn.style.display = 'none';
    linkInput.focus();
  });

  // Enter Key Submission
  linkInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      triggerAnalysis();
    }
  });

  submitBtn.addEventListener('click', () => triggerAnalysis());

  // Demo Cards Click Handling
  demoCards.forEach((card) => {
    card.addEventListener('click', () => {
      const fixtureKey = card.getAttribute('data-fixture');
      const fixture = FIXTURES[fixtureKey];
      if (fixture) {
        linkInput.value = `https://www.amazon.in/dp/${fixture.asin}`;
        clearInputBtn.style.display = 'flex';
        executeInspection(fixture);
      }
    });
  });

  // Reset Button
  if (resetViewBtn) {
    resetViewBtn.addEventListener('click', () => {
      engine.setInspectionActive(false);
      inspectionBay.classList.remove('visible');
      molecularHud.classList.remove('visible');
      scanningHud.classList.remove('visible');
      searchSection.classList.remove('moved-up');
      linkInput.value = '';
      clearInputBtn.style.display = 'none';
      setTimeout(() => linkInput.focus(), 500);

      engine.transitionToAmbient();
    });
  }

  // FoSCoS Grievance Modal Listeners
  if (draftGrievanceBtn) {
    draftGrievanceBtn.addEventListener('click', async () => {
      if (!currentAnalysis) return;
      grievanceModal.classList.add('visible');
      grievanceText.value = 'Drafting formal FoSCoS grievance citing official circulars...';

      const result = await draftGrievance(currentAnalysis.requestId);
      grievanceText.value = result.draftText;
    });
  }

  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
      grievanceModal.classList.remove('visible');
    });
  }

  grievanceModal.addEventListener('click', (e) => {
    if (e.target === grievanceModal) {
      grievanceModal.classList.remove('visible');
    }
  });

  if (copyGrievanceBtn) {
    copyGrievanceBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(grievanceText.value).then(() => {
        copyBtnLabel.textContent = 'Copied to Clipboard!';
        setTimeout(() => {
          copyBtnLabel.textContent = 'Copy Complaint Text';
        }, 2000);
      });
    });
  }

  /**
   * Main Trigger: Reads input and runs inspection
   */
  async function triggerAnalysis() {
    let url = linkInput.value.trim();
    if (!url) {
      // Default to the Everest Garam Masala demo recall case
      url = 'https://www.amazon.in/dp/B0FIXTURE1';
      linkInput.value = url;
      clearInputBtn.style.display = 'flex';
    }

    startScanningSequence();

    try {
      const response = await analyzeProduct(url);
      if (apiStatusText) {
        apiStatusText.textContent = response.source === 'live' ? 'Live API' : 'Demo / Fixture';
      }
      displayResults(response.data);
    } catch (err) {
      stopScanningSequence();
      alert(`Analysis failed: ${err.message}`);
      engine.transitionToAmbient();
    }
  }

  /**
   * Direct Fixture Inspection (for 1-click Demo Cards)
   */
  async function executeInspection(fixtureData) {
    startScanningSequence();
    // Simulate short network latency so judges can view the scanning convergence
    await new Promise((resolve) => setTimeout(resolve, 900));
    displayResults(fixtureData);
  }

  /**
   * Step 1: Start Scanning Animation & Progressive HUD
   */
  function startScanningSequence() {
    searchSection.classList.add('moved-up');
    inspectionBay.classList.remove('visible');
    molecularHud.classList.remove('visible');

    // Converge 3D particles to center core
    engine.startScanning();

    // Show Scanning HUD
    scanningHud.classList.add('visible');

    // Reset pipeline steps
    [pipeStepResolve, pipeStepKb, pipeStepVerdict, pipeStepGround].forEach((s) =>
      s.classList.remove('active', 'completed')
    );
    pipeStepResolve.classList.add('active');
    scanningStatus.textContent = 'Extracting product ASIN and metadata...';

    // Progressive step simulation
    let step = 1;
    clearInterval(pipelineTimer);
    pipelineTimer = setInterval(() => {
      step++;
      if (step === 2) {
        pipeStepResolve.classList.replace('active', 'completed');
        pipeStepKb.classList.add('active');
        scanningStatus.textContent = 'Querying Bedrock Knowledge Base (S3 Vectors)...';
      } else if (step === 3) {
        pipeStepKb.classList.replace('active', 'completed');
        pipeStepVerdict.classList.add('active');
        scanningStatus.textContent = 'Synthesizing regulatory circulars & batch codes...';
      } else if (step === 4) {
        pipeStepVerdict.classList.replace('active', 'completed');
        pipeStepGround.classList.add('active');
        scanningStatus.textContent = 'Enforcing zero-hallucination citation guard...';
      }
    }, 450);
  }

  function stopScanningSequence() {
    clearInterval(pipelineTimer);
    scanningHud.classList.remove('visible');
  }

  /**
   * Step 2: Display Results & Partition Particles
   */
  function displayResults(data) {
    stopScanningSequence();
    currentAnalysis = data;

    // 1. Partition 3D Particles into Macros (or non-food)
    if (data.product && !data.product.isFoodProduct) {
      engine.transitionToNonFoodState();
    } else if (data.nutrition) {
      engine.decomposeIntoMacros(data.nutrition);
      renderMacroBadges(data.nutrition.macros);
      setTimeout(() => molecularHud.classList.add('visible'), 500);
    } else {
      engine.transitionToNonFoodState();
    }

    // 2. Populate Identity Header
    const prod = data.product || {};
    bayBrand.textContent = prod.brand || 'Unspecified Brand';
    bayCategory.textContent = formatCategory(prod.category);
    productName.textContent = prod.name || 'Amazon Product';
    productAsinBadge.textContent = `ASIN: ${data.asin || 'N/A'}`;
    productQuantity.textContent = prod.netQuantity ? `Net: ${prod.netQuantity}` : 'Pack size not declared';
    productFssai.textContent = prod.fssaiLicense
      ? `FSSAI: ${prod.fssaiLicense}`
      : 'FSSAI: Not declared on listing';

    // 3. Verdict Card
    const verdict = data.verdict || { status: 'NO_DATA', score: 100, headline: '', summary: '' };
    const statusKey = verdict.status || 'NO_DATA';
    const statusColor = STATUS_COLORS[statusKey] || STATUS_COLORS.NO_DATA;
    const statusLabel = STATUS_LABELS[statusKey] || statusKey;

    verdictStatusPill.textContent = statusLabel;
    verdictStatusPill.style.backgroundColor = `${statusColor}25`;
    verdictStatusPill.style.borderColor = `${statusColor}60`;
    verdictStatusPill.style.color = statusColor;

    verdictCacheTag.textContent = data.cached ? '⚡ Cached Advisory (Instant)' : '🔍 Live Bedrock Grounded';
    verdictScore.textContent = verdict.score;
    verdictScore.style.color = statusColor;

    // Set SVG gauge progress
    scoreCirclePath.setAttribute('stroke-dasharray', `${verdict.score}, 100`);
    scoreCirclePath.style.stroke = statusColor;

    verdictHeadline.textContent = verdict.headline || 'No findings recorded';
    verdictSummary.textContent = verdict.summary || '';

    // Non-Food Alert Banner
    if (prod.isFoodProduct === false) {
      nonFoodNotice.style.display = 'flex';
      findingsSection.style.display = 'none';
      nutritionSection.style.display = 'none';
    } else {
      nonFoodNotice.style.display = 'none';
      findingsSection.style.display = 'flex';
      nutritionSection.style.display = 'flex';
    }

    // 4. Grounded Findings & Citations
    const findings = data.findings || [];
    findingsCount.textContent = findings.length;
    findingsContainer.innerHTML = '';

    if (findings.length === 0) {
      findingsContainer.innerHTML = `
        <div class="notice-box" style="background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); color: #34d399;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <div>
            <strong>Clean Regulatory Record</strong>
            <p>No adverse recall, contamination, or misbranding orders found for this product or brand across FSSAI, RASFF, FDA, or CFS records.</p>
          </div>
        </div>
      `;
    } else {
      findings.forEach((finding) => {
        const fCard = document.createElement('div');
        fCard.className = 'finding-card';

        const severityClass = `severity-${(finding.severity || 'info').toLowerCase()}`;
        const hasBatches = finding.batches && finding.batches.length > 0;

        let batchHtml = '';
        if (hasBatches) {
          batchHtml = `
            <div class="batch-warning-box">
              <span>⚠️ Recalled Batches:</span>
              <span class="batch-codes">${finding.batches.join(', ')}</span>
              <span style="font-size: 0.72rem; color: #fca5a5;">(Check physical pack)</span>
            </div>
          `;
        }

        // Citations HTML
        let citationsHtml = '';
        (finding.citations || []).forEach((c) => {
          citationsHtml += `
            <div class="citation-chip">
              <div class="citation-meta-row">
                <div class="citation-label-wrapper">
                  <span class="citation-issuer">${escapeHtml(c.issuer || 'Regulator')}</span>
                  <span class="citation-label">${escapeHtml(c.label || 'Circular')}</span>
                </div>
                <span class="citation-date">${c.date || ''}</span>
              </div>
              ${c.excerpt ? `<p class="citation-excerpt">“${escapeHtml(c.excerpt)}”</p>` : ''}
              ${
                c.sourceUrl
                  ? `<a href="${c.sourceUrl}" target="_blank" rel="noopener noreferrer" class="citation-link">
                      View Official Regulator Document
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                      </svg>
                    </a>`
                  : ''
              }
            </div>
          `;
        });

        fCard.innerHTML = `
          <div class="finding-header-row">
            <div class="finding-tags-left">
              <span class="severity-pill ${severityClass}">${finding.severity}</span>
              <span class="type-pill">${finding.type}</span>
              <span class="scope-pill ${finding.scope === 'BATCH' ? 'scope-batch' : ''}">Scope: ${finding.scope}</span>
            </div>
          </div>
          <div class="finding-title">${escapeHtml(finding.title)}</div>
          <p class="finding-detail">${escapeHtml(finding.detail)}</p>
          ${batchHtml}
          <div class="citations-box">${citationsHtml}</div>
        `;

        findingsContainer.appendChild(fCard);
      });
    }

    // 5. NOVA & Additives Section
    if (data.nutrition) {
      const nut = data.nutrition;
      const nova = nut.novaGroup || 1;
      novaNumber.textContent = `NOVA ${nova}`;
      novaNumber.className = `nova-badge-circle nova-badge-${nova}`;

      if (nova === 1) {
        novaLabel.textContent = 'Unprocessed / Minimally Processed';
        novaDesc.textContent = 'Natural whole foods without industrial formulations.';
      } else if (nova === 2) {
        novaLabel.textContent = 'Processed Culinary Ingredients';
        novaDesc.textContent = 'Oils, butter, sugar, and salt obtained from natural sources.';
      } else if (nova === 3) {
        novaLabel.textContent = 'Processed Food';
        novaDesc.textContent = 'Manufactured with added salt, sugar, or fats.';
      } else {
        novaLabel.textContent = 'Ultra-Processed Formulation';
        novaDesc.textContent = 'Industrial formulations with additives, sweeteners, or emulsifiers.';
      }

      // Additives
      additivesTagsList.innerHTML = '';
      if (nut.additives && nut.additives.length > 0) {
        nut.additives.forEach((add) => {
          const tag = document.createElement('span');
          const riskClass = `risk-${(add.risk || 'watch').toLowerCase()}`;
          tag.className = `additive-tag ${riskClass}`;
          tag.textContent = `${add.name} (${add.ins || 'INS'}) • ${add.risk}`;
          additivesTagsList.appendChild(tag);
        });
      } else {
        additivesTagsList.innerHTML = '<span class="empty-tag">No flagged additives detected</span>';
      }

      // Flags
      flagsContainer.innerHTML = '';
      if (nut.flags && nut.flags.length > 0) {
        flagsContainer.style.display = 'flex';
        nut.flags.forEach((f) => {
          const fb = document.createElement('div');
          fb.className = 'flag-badge';
          fb.textContent = `⚠️ Flag: ${f.label}`;
          flagsContainer.appendChild(fb);
        });
      } else {
        flagsContainer.style.display = 'none';
      }
    }

    // 6. Alternatives Section
    if (data.alternatives && data.alternatives.length > 0) {
      alternativesSection.style.display = 'flex';
      alternativesList.innerHTML = '';
      data.alternatives.forEach((alt) => {
        const altCard = document.createElement('div');
        altCard.className = 'alternative-card';
        altCard.innerHTML = `
          <span class="alt-title">${escapeHtml(alt.brand)} — ${escapeHtml(alt.name)}</span>
          <span class="alt-why">${escapeHtml(alt.why)}</span>
        `;
        alternativesList.appendChild(altCard);
      });
    } else {
      alternativesSection.style.display = 'none';
    }

    // 7. Grievance Banner
    if (data.grievance && data.grievance.eligible) {
      grievanceActionCard.style.display = 'flex';
    } else {
      grievanceActionCard.style.display = 'none';
    }

    // 8. Disclaimer
    if (data.disclaimer) {
      bayDisclaimer.textContent = data.disclaimer;
    }

    // Open Inspection Bay Drawer
    setTimeout(() => {
      engine.setInspectionActive(true);
      inspectionBay.classList.add('visible');
    }, 400);
  }

  /**
   * Render dynamic macro pills in the left 3D overlay HUD
   */
  function renderMacroBadges(macros) {
    macroBadgesList.innerHTML = '';
    if (!macros || macros.length === 0) return;

    macros.forEach((m) => {
      const pill = document.createElement('div');
      pill.className = 'hud-macro-pill';

      const colorToken = MACRO_CLASS_COLORS[m.class] || MACRO_CLASS_COLORS.UNKNOWN;

      pill.innerHTML = `
        <div class="macro-pill-left">
          <span class="macro-dot" style="background: ${colorToken.hex}; box-shadow: 0 0 8px ${colorToken.hex};"></span>
          <span class="macro-label">${escapeHtml(m.label)}</span>
        </div>
        <div class="macro-pill-right">
          <span class="macro-pct" style="color: ${colorToken.hex};">${m.pct.toFixed(1)}%</span>
          <span class="macro-grams">(${m.grams}g)</span>
        </div>
      `;
      macroBadgesList.appendChild(pill);
    });
  }

  function formatCategory(cat) {
    if (!cat) return 'Food & Beverage';
    return cat
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}
