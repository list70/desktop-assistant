const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  toggleClickThrough: (ignore) => ipcRenderer.send('toggle-click-through', ignore),
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  setAlwaysOnTop: (value) => ipcRenderer.send('set-always-on-top', value),
  openDevTools: () => ipcRenderer.send('open-dev-tools'),
  onMainMessage: (callback) => ipcRenderer.on('main-message', (_event, value) => callback(value))
});
