const socket = io(); // Connect to WebSocket

let players = {};
let myId = null;

socket.on("connect", () => {
    myId = socket.id;
});

socket.on("player_moved", (data) => {
    players[data.id] = data;

    if (data.id === myId) {
        players[myId] = data;
    }
});
const canvas = document.getElementById("Canvas");
const ctx = canvas.getContext("2d");

const questionDisplay = document.getElementById("questionBox");


const radius = 10;
const speed = 3;

const keysPressed = new Set();

//Format: [Question]: [Answer1, Answer2, Answer3, Answer4, Solution]
questionSet = {
    "What is 1 + 1?": ["1", "2", "3", "4", "2"],
    "What color is the sky?": ["magenta", "blue", "hot pink", "green", "blue"],
    "What produces light?": ["Moon", "Concrete", "Leaf", "Sun", "Sun"]
}
questionDisplay.innerHTML = getRandomKey(questionSet)

canvas.height = window.innerHeight * 0.80;
canvas.width = window.innerWidth * 0.80;
let playerX = canvas.width / 2;
let playerY = canvas.height / 2;
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
        questionDisplay.innerHTML = getRandomKey(questionSet)

        //Debugging purposes
        console.log(`You are at position: (${playerX},${playerY})`)
        console.log(`You have chosen: (${ctx.getImageData(playerX, playerY, 1, 1).data})`)
    }
}, 1000);

function getRandomKey(dict) {
    const keys = Object.keys(dict);
    const randomIndex = Math.floor(Math.random() * keys.length);
    return keys[randomIndex];
}

function drawCircle() {
    ctx.beginPath();
    ctx.arc(playerX, playerY, radius, 0, 2 * Math.PI);
    ctx.fillStyle = "teal";
    ctx.fill();
    ctx.stroke();

    ctx.font = "12px Arial";
    ctx.fillStyle = "black";
    ctx.textAlign = "center";
    //ctx.fillText(players[myId]?.name || "Guest", playerX, playerY - radius - 5);
}

//Set will store all currently pressed key and prevent the lag between key switches
function updatePosition() {
    let moved = false;
    if (keysPressed.has("w")) { playerY -= speed; moved = true; }
    if (keysPressed.has("s")) { playerY += speed; moved = true; }
    if (keysPressed.has("a")) { playerX -= speed; moved = true; }
    if (keysPressed.has("d")) { playerX += speed; moved = true; }

    playerX = Math.max(radius, Math.min(canvas.width - radius, playerX));
    playerY = Math.max(radius, Math.min(canvas.height - radius, playerY));

    if (moved) {
        socket.emit("move", { id: myId, x: playerX, y: playerY });
    }
}

function drawPlayers() {
    for (const id in players) {
        const p = players[id];

        //const img = new Image();
        //img.src = p.image || '/static/uploads/default.jpg';  // Default image fallback


        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = "purple";
        ctx.fill();
        ctx.stroke();

        ctx.font = "12px Arial";
        ctx.fillStyle = "black";
        ctx.textAlign = "center";
        ctx.fillText(p.name || "Guest", p.x, p.y + radius + 10);
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