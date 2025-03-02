
#!/bin/bash

tailscale funnel --bg 80
sleep 5

FUNNEL_URL=$(tailscale funnel status | grep -o 'https://[^ ]*' | head -n 1)
echo "Funnel URL: $FUNNEL_URL"

DEVICE_ID=$(cat /proc/cpuinfo | grep "Serial" | awk '{print $3}')


RESPONSE=$(curl -X POST "https://railway.adboardbooking.com/api/camera/register" \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "'"$DEVICE_ID"'",
    "service": "billboardMonitoring", 
    "publicWebUrl": "'"$FUNNEL_URL"'"
  }')

echo "API Response: $RESPONSE"

