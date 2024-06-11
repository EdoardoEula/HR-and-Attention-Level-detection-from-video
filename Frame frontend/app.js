let numberElement = document.getElementById('number');
let bpm = document.getElementById('widget-bpm')
let avg_bpm = document.getElementById('widget-avg-bpm');
let warning = document.querySelector('.warning')
let counter = 0;
let currentNumber = 0;
const video = document.getElementById('video');
let lowlight = 1;

warning.style.display = 'none'

navigator.mediaDevices.getUserMedia({ video: {
    frameRate: {
    min: 30,
    ideal: 30,
    max: 30
    }
}, audio: false })
    .then(function(stream) {
        video.srcObject = stream;
    })
    .catch(function(err) {
        console.error('Error accessing webcam:', err);
    });

function getRandomNumber(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}
document.documentElement.style.setProperty('--percentage', counter);
numberElement.innerHTML = "0%"

setInterval(() => {
    currentNumber = getRandomNumber(0, 100);
    bpm.innerHTML = getRandomNumber(60, 110);
    lowlight = getRandomNumber(0,1);

    if (lowlight == 0) {
        warning.style.display = 'none'
    } else {
        warning.style.display = 'block'
    }

    avg_bpm.innerHTML = `Media: ${getRandomNumber(60, 110)}`;

    let interval = setInterval(() => {
        let circle = document.querySelector('circle');
        if (counter === currentNumber) {
            clearInterval(interval);
        } else {
            if (currentNumber < counter) {
                counter -= 1;
                let dashOffset = 450 - (450 * counter / 100);
                circle.style.strokeDashoffset = dashOffset;
                circle.style.transition = 'stroke-dashoffset 2s linear';
            } else {
                counter += 1;
                let dashOffset = 450 - (450 * counter / 100);
                circle.style.strokeDashoffset = dashOffset;
                circle.style.transition = 'stroke-dashoffset 2s linear';
            }
            numberElement.innerHTML = `${counter}%`;
            document.documentElement.style.setProperty('--percentage', counter);
        }
    }, 40);
}, 8000);
