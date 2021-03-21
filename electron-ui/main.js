const {app, BrowserWindow, ipcMain} = require('electron')
const path = require('path')
const zmq = require('zeromq')

const AUDIO_STREAM = process.env.AUDIO_STREAM || 'ipc:///tmp/audio-in'
const COMMANDS_STREAM = process.env.COMMANDS_STREAM || 'ipc:///tmp/commands-out'

var audio_sock = zmq.socket("pub");
audio_sock.connect(AUDIO_STREAM);
var commands_sock = zmq.socket("sub");
commands_sock.subscribe("");
commands_sock.connect(COMMANDS_STREAM);

function createWindow () {
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: false, // is default value after Electron v5
      contextIsolation: true, // protect against prototype pollution
      enableRemoteModule: false, // turn off remote
      preload: path.join(__dirname, "preload.js") // use a preload script
    }
  })

  commands_sock.on('message', (data) => {
    var msg = JSON.parse(data);
    console.log(msg);
    mainWindow.webContents.send('fromMain', msg);
  })

  ipcMain.on('toMain', (event, args) => {
    audio_sock.send(Buffer.from(args));
  })

  mainWindow.loadFile('index.html')
  mainWindow.webContents.openDevTools()
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit()
})
