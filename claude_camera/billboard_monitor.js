const cv = require('opencv4nodejs');
const Stream = require('node-rtsp-stream');
const WebSocket = require('ws');

// Input RTSP stream URL
const inputRtspUrl = "rtsp://username:password@ip_address:port/stream";

// Output stream settings
const streamPort = 9999;
const wsPort = 9998;

// Load pre-trained face detection model
const faceCascade = new cv.CascadeClassifier(cv.HAAR_FRONTALFACE_ALT2);

let trackedPersons = [];
let nextFaceId = 0;

class TrackedPerson {
    constructor(faceId, faceLocation) {
        this.faceId = faceId;
        this.faceLocation = faceLocation;
        this.framesSinceSeen = 0;
    }
}

function processFrame(frame) {
    const gray = frame.cvtColor(cv.COLOR_BGR2GRAY);
    const faces = faceCascade.detectMultiScale(gray).objects;

    // Match detected faces to tracked persons
    faces.forEach(face => {
        let matched = false;
        trackedPersons.forEach(person => {
            if (euclideanDistance(face, person.faceLocation) < 50) { // Adjust threshold as needed
                person.faceLocation = face;
                person.framesSinceSeen = 0;
                matched = true;
            }
        });

        if (!matched) {
            trackedPersons.push(new TrackedPerson(nextFaceId++, face));
        }
    });

    // Update tracked persons and remove those not seen recently
    trackedPersons = trackedPersons.filter(p => p.framesSinceSeen < 10); // Adjust threshold as needed
    trackedPersons.forEach(person => person.framesSinceSeen++);

    // Draw rectangles and IDs
    trackedPersons.forEach(person => {
        const [x, y, w, h] = person.faceLocation;
        frame.drawRectangle(new cv.Rect(x, y, w, h), new cv.Vec3(255, 0, 0), 2);
        frame.putText(`ID: ${person.faceId}`, new cv.Point2(x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.9, new cv.Vec3(255, 0, 0), 2);
    });

    const viewerCount = trackedPersons.length;
    frame.putText(`Viewers: ${viewerCount}`, new cv.Point2(10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, new cv.Vec3(0, 255, 0), 2);

    console.log(`Current viewers looking at billboard: ${viewerCount}`);

    return frame;
}

function euclideanDistance(rect1, rect2) {
    return Math.sqrt(Math.pow(rect1.x - rect2.x, 2) + Math.pow(rect1.y - rect2.y, 2));
}

// Set up RTSP stream
const stream = new Stream({
    name: 'name',
    streamUrl: inputRtspUrl,
    wsPort: wsPort,
    ffmpegOptions: {
        '-stats': '',
        '-r': 30
    }
});

// Set up WebSocket server for processed frames
const wss = new WebSocket.Server({ port: streamPort });

// Process frames
const cap = new cv.VideoCapture(inputRtspUrl);

function processAndSendFrame() {
    const frame = cap.read();
    if (frame.empty) {
        console.log("Failed to grab frame, trying to reconnect...");
        setTimeout(processAndSendFrame, 1000);
        return;
    }

    const processedFrame = processFrame(frame);
    const rawFrame = processedFrame.getData();

    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(rawFrame);
        }
    });

    setImmediate(processAndSendFrame);
}

processAndSendFrame();

console.log(`RTSP stream running on ws://localhost:${wsPort}`);
console.log(`Processed stream available on ws://localhost:${streamPort}`);