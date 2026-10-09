const APP = "http://127.0.0.1:8765/";

chrome.action.onClicked.addListener(tab => {
  chrome.tabs.create({ url: APP + "#" + encodeURIComponent(tab.url), index: tab.index + 1 });
});
