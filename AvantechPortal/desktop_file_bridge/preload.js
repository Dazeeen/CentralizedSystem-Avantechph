const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('bridgeApi', {
  pickFolder: () => ipcRenderer.invoke('pick-folder'),
});
