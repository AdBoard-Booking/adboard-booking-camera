import axios from 'axios';
import { exec } from 'child_process';
import express from 'express';
import { networkInterfaces } from 'os';
import { publicIpv4 } from 'public-ip';
import pLimit from 'p-limit';

// Get the local IP address
function getLocalIp() {
  const interfaces = networkInterfaces();
  for (const interfaceName in interfaces) {
    const iface = interfaces[interfaceName]; 
    for (const alias of iface) {  
      if (alias.family === 'IPv4' && !alias.internal) {
        return alias.address;
      }
    }
  }
  throw new Error('Unable to determine local IP address.');
}

// Scan the IP range and get the cpuSerialNumber
async function scanIpRange(baseIp) {
  const limit = pLimit(10); // Limit to 10 concurrent requests
  const ipChecks = [];

  for (let i = 0; i < 256; i++) {
    
    const ip = `pi:pi@${baseIp}.${i}:8000/api/status`;
    ipChecks.push(limit(async () => {
      console.log(`Scanning ${ip}`);
      try {
        const response = await axios.get(`http://${ip}`, { timeout: 1000 });
        if (response.status === 200 && response.data.data.cpuSerialNumber) {
          console.log(`Found CPU Serial Number: ${response.data.cpuSerialNumber} at ${ip}`);
          return response.data.data.cpuSerialNumber;
        }
      } catch (error) {

      }
      return null;
    }));
  }

  // Wait for all promises to settle and filter out null results
  const results = await Promise.all(ipChecks);
  const validResults = results.filter(result => result !== null);

  if (validResults.length > 0) {
    return validResults[0]; // Return the first valid result
  }

  throw new Error('No valid IP found in the range.');
}

// Start the web server
function startWebServer() {
  const app = express();
  const port = 3000;

  app.get('/', (req, res) => {
    res.send('Hello World!');
  });

  app.listen(port, () => {
    console.log(`Web server running at http://localhost:${port}`);
  });
}

// Set up the tunnel
function setupTunnel(cpuSerialNumber) {
  return new Promise((resolve, reject) => {
    exec(`pitunnel --port=3000 --http --name=${cpuSerialNumber} --persist`, (error, stdout, stderr) => {
      if (error) {
        reject(`Tunnel setup failed: ${stderr}`);
      } else {
        console.log(`Tunnel setup successful: ${stdout}`);
        resolve();
      }
    });
  });
}

// Register with the server
async function registerServer(cpuSerialNumber) {
  const publicIpAddress = await publicIpv4();
  const registrationUrl = `http://your-registration-server.com/register`;
  try {
    const response = await axios.post(registrationUrl, {
      cpuSerialNumber: cpuSerialNumber,
      ipAddress: publicIpAddress
    });
    if (response.status === 200) {
      console.log(`Registration successful: ${response.data}`);
    } else {
      console.log(`Registration failed: ${response.statusText}`);
    }
  } catch (error) {
    console.error(`Registration error: ${error.message}`);
  }
}

// Main function
(async function main() {
  try {
    const localIp = getLocalIp();
    const baseIp = localIp.split('.').slice(0, 3).join('.');
    const cpuSerialNumber = await scanIpRange(baseIp);

    startWebServer();

    await setupTunnel(cpuSerialNumber);

    await registerServer(cpuSerialNumber);
  } catch (error) {
    console.error(error.message);
  }
})();
