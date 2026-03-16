function formatRelative(isoString) {
  if (!isoString) return "기록 없음";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "기록 없음";
  const diffMinutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (diffMinutes < 1) return "방금";
  if (diffMinutes < 60) return `${diffMinutes}분 전`;
  const hours = Math.floor(diffMinutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

function formatDate(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}.${m}.${d}`;
}

function isKorean(text) {
  if (!text) return false;
  const letters = (text.match(/[a-zA-Z가-힣]/g) || []);
  if (!letters.length) return false;
  const ko = letters.filter((c) => c >= "\uAC00" && c <= "\uD7A3").length;
  return ko / letters.length > 0.3;
}

function showToast(title, message, type = "success") {
  const container = document.querySelector("#toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<strong>${title}</strong><span>${message}</span>`;
  container.append(toast);
  window.setTimeout(() => toast.remove(), 3200);
}

function normalizeArray(value) {
  return Array.isArray(value) ? value : [];
}
