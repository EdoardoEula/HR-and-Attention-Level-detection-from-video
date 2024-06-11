var video = document.querySelector('video');
var subjectInput = document.getElementById('subject');
var recorder;
var isRecording = false;
var counter = 0;
let recordingDuration = 8000;

function startWebcam() {
    navigator.mediaDevices.getUserMedia({
        video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            frameRate: 30
        }
    })
    .then(function(stream) {
        video.srcObject = stream;
        startRecordingCycle();
    }).catch(function(error) {
        alert('Unable to capture your camera. Please check console logs.');
        console.error(error);
    });
}

function startRecordingCycle() {
    isRecording = true;
    startRecording();
}

function startRecording() {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 320; // Width for 240p
    canvas.height = 240; // Height for 240p

    // Use a requestAnimationFrame loop to draw the video frames onto the canvas
    const stream = video.srcObject;
    const videoTrack = stream.getVideoTracks()[0];
    const captureStream = canvas.captureStream(25);

    recorder = new RecordRTC(captureStream, {
        type: 'video'
    });

    function drawVideoFrame() {
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        if (isRecording) {
            requestAnimationFrame(drawVideoFrame);
        }
    }

    drawVideoFrame();

    recorder.setRecordingDuration(recordingDuration).onRecordingStopped(stopRecording);
    recorder.startRecording();
}


function stopRecording() {
    if (!isRecording) return;

    isRecording = false;
    
    //recorder.stopRecording(function() {
        downloadRecordedVideo(recorder.getBlob());
        startRecordingCycle();
    //});
}

function downloadRecordedVideo(blob) {
    const jsonData = {
        idEvento: 'idev1235',
        username: subjectInput.value,
    };

    blobToBase64(blob).then(base64Data => {
        jsonData.video = base64Data;

        const jsonContent = JSON.stringify(jsonData, null, 2);
        const blobJson = new Blob([jsonContent], { type: 'application/json' });
        const urlJson = URL.createObjectURL(blobJson);
        const a = document.createElement('a');
        a.href = urlJson;
        a.download = `recorded_video_${subjectInput.value}_${counter}.json`;
        document.body.appendChild(a);
        a.click();

        URL.revokeObjectURL(urlJson);
        document.body.removeChild(a);

        counter++;
    });
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsArrayBuffer(blob);
        reader.onloadend = () => {
            const base64String = btoa(
                new Uint8Array(reader.result)
                    .reduce((data, byte) => data + String.fromCharCode(byte), '')
            );
            resolve(base64String);
        };
        reader.onerror = reject;
    });
}

window.onload = startWebcam;

window.addEventListener('beforeunload', function() {
    stopRecording();
});
