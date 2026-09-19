/**
 * Extension-wide config. The API base URL is the one thing that changes between local
 * testing and the deployed stack - update it here after `sam deploy` prints the ApiUrl
 * output, or after Phase 1 wires this up to build-time env injection.
 */
export const API_BASE_URL = "https://REPLACE_ME.execute-api.us-east-1.amazonaws.com/prod";

export const ANALYZE_ENDPOINT = `${API_BASE_URL}/v1/analyze`;
export const GRIEVANCE_ENDPOINT = `${API_BASE_URL}/v1/grievance`;

export const STATUS_COLORS = {
  CRITICAL: "#DC2626",
  WARNING: "#EA580C",
  CAUTION: "#D97706",
  CLEAR: "#059669",
  NO_DATA: "#64748B",
};
