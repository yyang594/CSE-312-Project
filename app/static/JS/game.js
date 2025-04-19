const socket = io(); // Connect to WebSocket

let players = {};
let myId = null;

socket.on("connect", () => {
    myId = socket.id;
});

socket.on("player_moved", (data) => {
    players[data.id] = data;
});
const canvas = document.getElementById("Canvas");
const ctx = canvas.getContext("2d");


const radius = 10;
const speed = 3;

const keysPressed = new Set();

canvas.height = window.innerHeight * 0.80;
canvas.width = window.innerWidth * 0.80;
let playerX = canvas.width / 2;
let playerY = canvas.height / 2;
//Timer
//Change maxTime to change countdown
const timer = document.getElementById("timer")
var maxTime = 30
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
    let moved = false;
    if (keysPressed.has("w")) { playerY -= speed; moved = true; }
    if (keysPressed.has("s")) { playerY += speed; moved = true; }
    if (keysPressed.has("a")) { playerX -= speed; moved = true; }
    if (keysPressed.has("d")) { playerX += speed; moved = true; }

    if (moved) {
        socket.emit("move", { id: myId, x: playerX, y: playerY });
    }
}

function drawPlayers() {
    for (const id in players) {
        const p = players[id];
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = "purple";
        ctx.fill();
        ctx.stroke();
    }
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
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setUp();
    updatePosition();
    drawPlayers(); // draw others first
    drawCircle();  // draw self
    requestAnimationFrame(gameLoop);
}

requestAnimationFrame(gameLoop);