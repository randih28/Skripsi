(async () => {
    const constraints = {
        video: true
    };

    try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        const videoElement = document.getElementById('video');
        videoElement.srcObject = stream;
    } catch (error) {
        console.error('Error accessing media devices.', error);
    }
})();

document.getElementById('capture').addEventListener('click', () => {
    const video = document.getElementById('video');
    const snapshot = document.getElementById('snapshot');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to image data URL
    const dataURL = canvas.toDataURL('image/jpeg');
    snapshot.src = dataURL;
});
