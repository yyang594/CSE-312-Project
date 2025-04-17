const canvas = document.getElementById("Canvas");
const ctx = canvas.getContext("2d");

let playerX = 100;
let playerY = 100;
const radius = 10;
const speed = 3;

const keysPressed = new Set();

canvas.height = window.innerHeight * 0.80;
canvas.width = window.innerWidth * 0.80;

//Timer
//Change maxTime to change countdown
const timer = document.getElementById("timer")
var maxTime = 5
var totalTime = maxTime
setInterval(function () {
    totalTime -= 1
    timer.innerHTML = "00:" + totalTime
    if (totalTime == 0){
        totalTime = maxTime
        //Debugging purposes
        console.log(`You are at position: (${playerX},${playerY})`)
        console.log(`You have chosen: (${ctx.getImageData(playerX, playerY, 1, 1).data})`)
    }
}, 1000);

function drawCircle() {
    ctx.beginPath();
    ctx.arc(playerX, playerY, radius, 0, 2 * Math.PI);
    ctx.fillStyle = "teal";
    ctx.fill();
    ctx.stroke();
}

//Set will store all currently pressed key and prevent the lag between key switches
function updatePosition() {
    if (keysPressed.has("w")) playerY -= speed;
    if (keysPressed.has("s")) playerY += speed;
    if (keysPressed.has("a")) playerX -= speed;
    if (keysPressed.has("d")) playerX += speed;
}

document.addEventListener("keydown", (e) => {
    keysPressed.add(e.key.toLowerCase());
});

document.addEventListener("keyup", (e) => {
    keysPressed.delete(e.key.toLowerCase());
});

function setUp(){
    let rectWidth = canvas.width*0.4
    let rectHeight = canvas.height*0.4

    ctx.fillStyle = "red";
    ctx.fillRect(0, 0, rectWidth, rectHeight);

    ctx.fillStyle = "blue";
    ctx.fillRect(canvas.width-rectWidth, 0, rectWidth, rectHeight);

    ctx.fillStyle = "orange";
    ctx.fillRect(0, canvas.height-rectHeight, rectWidth, rectHeight);
    
    ctx.fillStyle = "green";
    ctx.fillRect(canvas.width-rectWidth, canvas.height-rectHeight, rectWidth, rectHeight);
}

//Main loop
function gameLoop() {
    //Set up game board
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setUp();

    updatePosition();
    drawCircle();
    requestAnimationFrame(gameLoop);
}

requestAnimationFrame(gameLoop);