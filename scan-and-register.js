import axios from 'axios';
import { exec } from 'child_process';
import express from 'express';
import { networkInterfaces } from 'os';
import pLimit from 'p-limit';
import capture from './capture.js';

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
async function scanIpRange(baseIp,lastValue) {
  const limit = pLimit(10); // Limit to 10 concurrent requests
  const ipChecks = [];

  for (let i = lastValue; i >= 0; i--) {
    
    const ip = `pi:pi@${baseIp}.${i}:8000/api/status`;
    ipChecks.push(limit(async () => {
      console.log(`Scanning ${ip}`);
      try {
        const response = await axios.get(`http://${ip}`, { timeout: 1000 });
        let cpuSerialNumber = response.data.data.cpuSerialNumber
        if (response.status === 200 && cpuSerialNumber) {
          console.log(`Found CPU Serial Number: ${cpuSerialNumber} at ${ip}`);
          return cpuSerialNumber;
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

  ipChecks = [];

  for (let i = lastValue; i < 256; i++) {
    
    const ip = `pi:pi@${baseIp}.${i}:8000/api/status`;
    ipChecks.push(limit(async () => {
      console.log(`Scanning ${ip}`);
      try {
        const response = await axios.get(`http://${ip}`, { timeout: 1000 });
        let cpuSerialNumber = response.data.data.cpuSerialNumber
        if (response.status === 200 && cpuSerialNumber) {
          console.log(`Found CPU Serial Number: ${cpuSerialNumber} at ${ip}`);
          return cpuSerialNumber;
        }
      } catch (error) {

      }
      return null;
    }));
  }


  // Wait for all promises to settle and filter out null results
  results = await Promise.all(ipChecks);
  validResults = results.filter(result => result !== null);

  if (validResults.length > 0) {
    return validResults[0]; // Return the first valid result
  }

  throw new Error('No valid IP found in the range.');
}

// Start the web server
function startWebServer() {
  const app = express();
  const port = 3000;

  app.use('/', capture)

  app.listen(port, () => {
    console.log(`Web server running at http://localhost:${port}`);
  });

}

// Set up the tunnel
function setupTunnel(cpuSerialNumber) {
  return new Promise((resolve, reject) => {
    exec(`pitunnel --port=3000 --http --name=picam-${cpuSerialNumber} --persist`, (error, stdout, stderr) => {
      console.log(`Tunnel setup successful`);
      resolve();
    });
  });
}

// Main function
(async function main() {
  try {
    const localIp = getLocalIp();
    const baseIp = localIp.split('.').slice(0, 3).join('.');
    const lastValue = localIp.split('.').pop();
    const cpuSerialNumber = await scanIpRange(baseIp,lastValue);

    setupTunnel(cpuSerialNumber);
    startWebServer();

  } catch (error) {
    console.error('Failed: ', error);
  }
})();
