// API client functions

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`);
  if (!response.ok) throw new Error('Failed to fetch sessions');
  return response.json();
}

export async function fetchSession(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
  if (!response.ok) throw new Error('Failed to fetch session');
  return response.json();
}

export async function deleteSession(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete session');
  return response.json();
}

export async function listFiles(sessionId: string, path: string = '') {
  const url = new URL(`${API_BASE}/api/files/${sessionId}/list`);
  if (path) url.searchParams.set('path', path);
  const response = await fetch(url.toString());
  if (!response.ok) throw new Error('Failed to list files');
  return response.json();
}

export async function readFile(sessionId: string, path: string) {
  const url = new URL(`${API_BASE}/api/files/${sessionId}/read`);
  url.searchParams.set('path', path);
  const response = await fetch(url.toString());
  if (!response.ok) throw new Error('Failed to read file');
  return response.json();
}

export async function listOutputs(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/files/${sessionId}/outputs`);
  if (!response.ok) throw new Error('Failed to list outputs');
  return response.json();
}

export function getWebSocketUrl(sessionId?: string): string {
  const wsBase = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://');
  return sessionId ? `${wsBase}/api/ws/${sessionId}` : `${wsBase}/api/ws`;
}

export function getDownloadUrl(sessionId: string, path: string): string {
  return `${API_BASE}/api/files/${sessionId}/download?path=${encodeURIComponent(path)}`;
}

export function getFilePreviewUrl(sessionId: string, path: string): string {
  return `${API_BASE}/api/files/${sessionId}/download?path=${encodeURIComponent(path)}`;
}
