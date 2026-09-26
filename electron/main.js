const { app, BrowserWindow, ipcMain, Tray, Menu, globalShortcut, screen } = require('electron');
const path = require('path');

let mainWindow;
let tray;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  const windowWidth = 400;
  const windowHeight = 600;

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: width - windowWidth - 20,
    y: height - windowHeight - 20,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    resizable: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  globalShortcut.register('CommandOrControl+Shift+A', () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
    }
  });
}

function createTray() {
  try {
    const { nativeImage } = require('electron');
    // Create a simple 16x16 tray icon programmatically
    const icon = nativeImage.createEmpty();
    tray = new Tray(icon);
    const contextMenu = Menu.buildFromTemplate([
      { label: '表示する', click: () => mainWindow && !mainWindow.isDestroyed() && mainWindow.show() },
      { label: '隠す', click: () => mainWindow && !mainWindow.isDestroyed() && mainWindow.hide() },
      { type: 'separator' },
      { label: '開発者ツール', click: () => mainWindow && !mainWindow.isDestroyed() && mainWindow.webContents.openDevTools({ mode: 'detach' }) },
      { type: 'separator' },
      { label: '終了', click: () => app.quit() }
    ]);
    tray.setToolTip('AI Desktop Assistant');
    tray.setContextMenu(contextMenu);
    tray.on('click', () => {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
      }
    });
  } catch (e) {
    console.log('Tray creation skipped:', e.message);
  }
}

app.whenReady().then(() => {
  createWindow();
  createTray();

  ipcMain.on('toggle-click-through', (event, ignore) => {
    mainWindow.setIgnoreMouseEvents(ignore, { forward: true });
  });

  ipcMain.on('minimize-window', () => {
    mainWindow.minimize();
  });

  ipcMain.on('set-always-on-top', (event, value) => {
    mainWindow.setAlwaysOnTop(value);
  });

  ipcMain.on('open-dev-tools', () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.openDevTools({ mode: 'detach' });
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('before-quit', () => {
  if (tray) tray.destroy();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
