/**
 * Renders the inline pill + slide-over drawer inside a Shadow DOM host, per the UI/UX
 * brief: Amazon's global CSS will otherwise warp our typography and buttons, and a plain
 * <div> injected into document.body risks collisions with Amazon's own class names.
 */

import { getBuyBoxAnchor } from "./dom.js";
import { STATUS_COLORS } from "./config.js";

const HOST_ID = "bitecheck-extension-root";

export function removeExisting() {
  document.getElementById(HOST_ID)?.remove();
}

function statusLabel(status) {
  return (
    {
      CRITICAL: "Critical safety alert",
      WARNING: "Safety warning",
      CAUTION: "Caution advised",
      CLEAR: "Verified clean",
      NO_DATA: "No adverse records",
    }[status] || status
  );
}

function buildShadowRoot(anchor) {
  const host = document.createElement("div");
  host.id = HOST_ID;
  anchor.prepend(host);
  return host.attachShadow({ mode: "open" });
}

const STYLES = `
  :host { all: initial; }
  * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

  .pill {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 14px; margin: 10px 0; border-radius: 10px;
    font-size: 13px; font-weight: 600; color: #fff; cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15); border: none; width: fit-content;
  }
  .pill:hover { filter: brightness(1.05); }
  .pill .icon { font-size: 16px; }

  .drawer {
    position: fixed; top: 0; right: -420px; width: 380px; height: 100vh;
    background: #ffffff; box-shadow: -6px 0 24px rgba(0,0,0,0.18);
    z-index: 2147483647; transition: right 0.32s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex; flex-direction: column; padding: 20px; overflow-y: auto;
  }
  .drawer.open { right: 0; }
  .drawer h2 { margin: 0; font-size: 17px; color: #111827; }
  .drawer .close { border: none; background: none; font-size: 18px; cursor: pointer; color: #6b7280; }
  .drawer .headline { font-size: 14px; font-weight: 600; margin: 14px 0 4px; color: #111827; }
  .drawer .summary { font-size: 13px; color: #374151; line-height: 1.5; margin-bottom: 14px; }
  .finding { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; margin-bottom: 8px; }
  .finding .title { font-size: 13px; font-weight: 600; color: #111827; margin-bottom: 4px; }
  .finding .detail { font-size: 12px; color: #4b5563; margin-bottom: 6px; }
  .finding .citation { font-size: 11px; color: #6b7280; }
  .disclaimer { font-size: 10px; color: #9ca3af; margin-top: auto; padding-top: 12px; }
`;

export function renderPill(analysis, onOpenDrawer) {
  const anchor = getBuyBoxAnchor();
  if (!anchor) return;

  const shadow = buildShadowRoot(anchor);
  const style = document.createElement("style");
  style.textContent = STYLES;

  const pill = document.createElement("button");
  pill.className = "pill";
  pill.style.background = STATUS_COLORS[analysis.verdict.status] || STATUS_COLORS.NO_DATA;
  pill.innerHTML = `<span class="icon">${analysis.verdict.status === "CLEAR" ? "✓" : "⚠"}</span>
    <span>${statusLabel(analysis.verdict.status)}</span>`;
  pill.addEventListener("click", onOpenDrawer);

  shadow.appendChild(style);
  shadow.appendChild(pill);
  // host is already positioned inside `anchor` by buildShadowRoot(); nothing left to do
  // here. The drawer itself uses position:fixed so it escapes the buy-box layout anyway,
  // as long as no Amazon ancestor sets a CSS transform (none currently does).
}

export function renderDrawer(analysis) {
  const host = document.getElementById(HOST_ID);
  if (!host) return;
  const shadow = host.shadowRoot;

  let drawer = shadow.querySelector(".drawer");
  if (drawer) {
    drawer.classList.toggle("open");
    return;
  }

  drawer = document.createElement("div");
  drawer.className = "drawer open";

  const findingsHtml = analysis.findings
    .map(
      (f) => `
      <div class="finding">
        <div class="title">${f.title}</div>
        <div class="detail">${f.detail}</div>
        ${f.citations
          .map((c) => `<div class="citation">Source: ${c.label} (${c.issuer}${c.date ? ", " + c.date : ""})</div>`)
          .join("")}
      </div>`
    )
    .join("");

  drawer.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <h2>BiteCheck Safety Audit</h2>
      <button class="close">&times;</button>
    </div>
    <div class="headline">${analysis.verdict.headline}</div>
    <div class="summary">${analysis.verdict.summary}</div>
    ${findingsHtml}
    <div class="disclaimer">${analysis.disclaimer}</div>
  `;

  drawer.querySelector(".close").addEventListener("click", () => drawer.classList.remove("open"));
  shadow.appendChild(drawer);
}
