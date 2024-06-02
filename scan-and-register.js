import axios from 'axios';
import { exec } from 'child_process';
import express from 'express';
import { networkInterfaces } from 'os';
import pLimit from 'p-limit';
import capture from './capture.js';
import machineId from 'node-machine-id';

let deviceId = machineId.machineIdSync({original: true});

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
  let cred = "adboardbooking:adboardbooking";

  for (let i = 0; i < 256; i++) {
    
    const ip = `${cred}@${baseIp}.${i}:8000/api/status`;
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

  const results = await Promise.all(ipChecks);
  const validResults = results.filter(result => result !== null);

  if (validResults.length > 0) {
    return validResults; // Return the first valid result
  }
  return []
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
function setupTunnel() {

  console.log(`Setting up tunnel for ${deviceId}`);
  
  return new Promise((resolve, reject) => {
    exec(`pitunnel --port=3000 --http --name=picam-${deviceId} --persist`, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error: ${error}`);
        console.error(`stderr: ${stderr}`);
      }else{
        console.log(`stdout: ${stdout}`);
        console.log(`Tunnel setup successful`);
      }

      resolve();
    });
  });
}

function register(connectedCpuSerialNumbers){
  console.log('Registering device with server', deviceId, connectedCpuSerialNumbers);
  return axios.post('https://railway.adboardbooking.com/api/camera/register', {
    deviceId: deviceId,
    tunnelUrl: 'https://picam-'+deviceId+'-ankurkus.in1.pitunnel.com',
    connectedCpuSerialNumbers:connectedCpuSerialNumbers
  })
  .then(function (response) {
    console.log('Registration successful', response.data)
  })
  .catch(function (error) {
    console.error('Registration failed', error.message)
  });

}

// Main function
(async function main() {
  try {
    const localIp = getLocalIp();
    const baseIp = localIp.split('.').slice(0, 3).join('.');
    const cpuSerialNumbers = await scanIpRange(baseIp);
    await register(cpuSerialNumbers)
    await setupTunnel();

    // setupTunnel(cpuSerialNumber);
    startWebServer();


  } catch (error) {
    console.error('Failed: ', error);
  }
})();
