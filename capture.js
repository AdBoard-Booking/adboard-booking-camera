import express from 'express';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
  
const app = express.Router()

const imageDir = path.join(__dirname, 'camera-images');
const imagePath = path.join(imageDir, 'image.jpg');

// Ensure the directory exists
if (!fs.existsSync(imageDir)) {
  fs.mkdirSync(imageDir);
}

// Function to capture image using raspistill
function captureImage() {
  return new Promise((resolve,reject)=>{
    const raspistill = spawn('raspistill', [
      '-o', imagePath,
      '-t', '1',
      '-br', '60', // Increase brightness (range 0 to 100)
    ]);
    raspistill.on('error', (err) => {
      console.error('Failed to start subprocess.', err);
      reject(err);
    });
    raspistill.on('exit', (code) => {
      console.log(`child process exited with code ${code}`);
      resolve();
    }); 
  })
 
}

// Capture image every 5 seconds
//setInterval(captureImage, 1000);
// captureImage(); // Initial capture

// Serve the captured image
app.get('/image', async (req, res) => {
  await captureImage();
  res.sendFile(imagePath);
});

// Serve the HTML page
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Raspberry Pi Camera Stream</title>
    </head>
    <body>
      <h1>Raspberry Pi Camera Stream</h1>
      <img id="cameraImage" src="/image" alt="Camera Image">
      <script>
        const imageElement = document.getElementById('cameraImage');
        const fetchImage = () => {
          imageElement.src = '/image?t=' + new Date().getTime();
        };
        setInterval(fetchImage, 1000);
      </script>
    </body>
    </html>
  `);
});

export default app;