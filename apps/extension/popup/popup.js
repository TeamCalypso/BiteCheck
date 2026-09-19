// BiteCheck Extension Action Popup Controller

document.addEventListener('DOMContentLoaded', async () => {
  const asinEl = document.getElementById('current-asin');
  const apiInput = document.getElementById('api-url');
  const saveBtn = document.getElementById('save-btn');
  const msgSaved = document.getElementById('msg-saved');

  // Load configured API URL
  chrome.runtime.sendMessage({ type: 'GET_API_URL' }, (res) => {
    if (res && res.url) {
      apiInput.value = res.url;
    }
  });

  // Query active tab for ASIN
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0 && tabs[0].url) {
      const url = tabs[0].url;
      const match = url.match(/(?:\/dp\/|\/gp\/product\/|\/product\/|\/asin\/)([A-Z0-9]{10})/i);
      if (match) {
        asinEl.textContent = match[1].toUpperCase();
      } else if (url.includes('amazon.in')) {
        asinEl.textContent = 'Amazon (Browse)';
      } else {
        asinEl.textContent = 'Non-Amazon Tab';
      }
    }
  } catch (err) {
    asinEl.textContent = 'Ready';
  }

  // Save new API base URL
  saveBtn.addEventListener('click', () => {
    const newUrl = apiInput.value.trim() || 'http://localhost:8000';
    chrome.runtime.sendMessage({ type: 'SET_API_URL', url: newUrl }, (res) => {
      msgSaved.style.display = 'block';
      setTimeout(() => {
        msgSaved.style.display = 'none';
      }, 2000);
    });
  });
});
