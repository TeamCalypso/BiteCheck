/**
 * BiteCheck Web Application Configuration
 * Mirrors status colors, severity order, and macro class colors from contract and docs/ui-ux-brief.md.
 */

// Reads Vite env variable, fallback to relative /v1 for dev proxy or local SAM / production API Gateway
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const ENDPOINTS = {
  ANALYZE: `${API_BASE_URL}/v1/analyze`,
  TRENDING: `${API_BASE_URL}/v1/trending`,
  GRIEVANCE: `${API_BASE_URL}/v1/grievance`,
  HEALTH: `${API_BASE_URL}/v1/health`,
};

// Colors defined in docs/ui-ux-brief.md
export const STATUS_COLORS = {
  CRITICAL: '#DC2626',
  WARNING: '#EA580C',
  CAUTION: '#D97706',
  CLEAR: '#059669',
  NO_DATA: '#64748B',
};

export const STATUS_LABELS = {
  CRITICAL: 'Critical Safety Alert',
  WARNING: 'Regulatory Warning',
  CAUTION: 'Caution Advised',
  CLEAR: 'Verified Clean',
  NO_DATA: 'No Regulatory Records',
};

export const SEVERITY_COLORS = {
  CRITICAL: '#EF4444',
  HIGH: '#F97316',
  MEDIUM: '#F59E0B',
  INFO: '#3B82F6',
};

export const MACRO_CLASS_COLORS = {
  GOOD: { hex: '#10B981', rgb: [0.06, 0.72, 0.50] },     // Emerald
  NEUTRAL: { hex: '#38BDF8', rgb: [0.22, 0.74, 0.97] },  // Sky
  WATCH: { hex: '#F59E0B', rgb: [0.96, 0.62, 0.04] },    // Amber
  UNKNOWN: { hex: '#94A3B8', rgb: [0.58, 0.64, 0.72] },  // Slate
};

export const ADDITIVE_RISK_COLORS = {
  OK: '#10B981',
  WATCH: '#F59E0B',
  AVOID: '#EF4444',
};
