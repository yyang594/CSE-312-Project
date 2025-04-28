const socket = io(); // Connect to WebSocket

let players = {};
let gameRunning = false;
let myId = null;

let questionSet = {};
let intervalId;
let maxTime = 20;
let totalTime = maxTime;
let playerState = "Default";
let currentQuestion;
let answers;
let solution;
let solutionParameter = [];

const canvas = document.getElementById("Canvas");
const ctx = canvas.getContext("2d");

const questionDisplay = document.getElementById("questionBox");
const timerElement = document.getElementById("timer");

let playerX = 0;
let playerY = 0;

// --- Socket Events ---

socket.on("connect", () => {
    myId = socket.id;
    socket.emit("join_room", { room: ROOM_ID });
});

socket.on('player_moved', function(data) {
    players[data.id] = {
        x: data.x,
        y: data.y,
        name: data.name
    };
});

socket.on('start_game', function() {
    document.getElementById("waitingRoom").style.display = "none";
    document.getElementById("gameContainer").style.display = "block";

    startGame();
});

socket.on('next_question', function(data) {
    currentQuestion = data.question;
    answers = [...data.answers];
    solution = data.solution;
    questionDisplay.innerHTML = currentQuestion;
    startTimer()
});

socket.on('update_positions', function(updatedPlayers) {
    players = {};
    for (const id in updatedPlayers) {
        players[id] = {
            x: updatedPlayers[id].x,
            y: updatedPlayers[id].y,
            name: updatedPlayers[id].name
        };
    }
});

socket.on('update_player_scores', function(playerScores) {
    const playerListElement = document.getElementById('player-list');
    playerListElement.innerHTML = '';

    playerScores.forEach(function(player) {
        const li = document.createElement('li');
        li.textContent = `${player.username}: ${player.score} pts`;
        playerListElement.appendChild(li);
    });
});

socket.on('game_over', function(data) {
    document.getElementById("gameContainer").style.display = "none";
    document.getElementById("gameOverScreen").style.display = "block";
    document.getElementById("winnerAnnouncement").textContent = `Winner: ${data.winnerName} with ${data.winnerScore} points!`;
});

// --- Game Logic ---

function loadQuestions(questionsFromServer) {
    questionSet = {};
    questionsFromServer.forEach(q => {
        questionSet[q.question] = [...q.answers, q.solution];
    });
}

function startGame() {
    if (gameRunning) return;
    gameRunning = true;

    startTimer();
    requestAnimationFrame(gameLoop);
}

function startTimer() {
    clearInterval(intervalId);
    totalTime = maxTime;
    updateTimerDisplay();

    intervalId = setInterval(countdown, 1000);
}

function countdown() {
    totalTime -= 1;
    updateTimerDisplay();

    if (totalTime <= 0) {
        clearInterval(intervalId);
        playerState = "Default";

        // 🚀 Send my player position to server
        socket.emit('submit_answer', {
            x: playerX,
            y: playerY,
            room: ROOM_ID
        });
    }
}

function updateTimerDisplay() {
    timerElement.innerHTML = "00:" + (totalTime < 10 ? "0" + totalTime : totalTime);
}

// --- Drawing and Movement ---

canvas.width = 1024;
canvas.height = 576;
const radius = 10;
let speed = 3;
const keysPressed = new Set();
playerX = canvas.width / 2;
playerY = canvas.height / 2;

function drawCircle() {
    ctx.beginPath();
    ctx.arc(playerX, playerY, radius, 0, 2 * Math.PI);
    ctx.fillStyle = "teal";
    ctx.fill();
    ctx.stroke();
}

function updatePosition() {
    let moved = false;
    if (keysPressed.has("w")) { playerY -= speed; moved = true; }
    if (keysPressed.has("s")) { playerY += speed; moved = true; }
    if (keysPressed.has("a")) { playerX -= speed; moved = true; }
    if (keysPressed.has("d")) { playerX += speed; moved = true; }

    playerX = Math.max(radius, Math.min(canvas.width - radius, playerX));
    playerY = Math.max(radius, Math.min(canvas.height - radius, playerY));

    if (moved) {
        socket.emit("move", { id: myId, x: playerX, y: playerY, room: ROOM_ID });
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
        ctx.font = "12px Arial";
        ctx.fillStyle = "white";
        ctx.textAlign = "center";
        ctx.fillText(p.name || "Guest", p.x, p.y + radius + 10);
    }
}

function setUp() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!answers || answers.length < 4) return;

    let rectWidth = canvas.width * 0.4;
    let rectHeight = canvas.height * 0.4;

    let rectParameters = [
        [0, 0, rectWidth, rectHeight, rectWidth / 2, rectHeight / 2, "red", answers[0], solution === answers[0]],
        [canvas.width - rectWidth, 0, rectWidth, rectHeight, canvas.width - rectWidth + rectWidth / 2, rectHeight / 2, "blue", answers[1], solution === answers[1]],
        [0, canvas.height - rectHeight, rectWidth, rectHeight, rectWidth / 2, canvas.height - rectHeight + rectHeight / 2, "orange", answers[2], solution === answers[2]],
        [canvas.width - rectWidth, canvas.height - rectHeight, rectWidth, rectHeight, canvas.width - rectWidth + rectWidth / 2, canvas.height - rectHeight + rectHeight / 2, "green", answers[3], solution === answers[3]]
    ];

    rectParameters.forEach(rect => {
        ctx.fillStyle = rect[6];
        ctx.fillRect(rect[0], rect[1], rect[2], rect[3]);

        ctx.fillStyle = "white";
        ctx.font = '20px sans-serif';
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(rect[7], rect[4], rect[5]);

        if (rect[8]) {
            solutionParameter = [rect[0], rect[1], rect[2], rect[3]];
        }
    });
}

function gameLoop() {
    if (speed !== 3) {
        speed -= 1;
    }

    setUp();
    if (playerState === "Default") {
        updatePosition();
    }
    drawPlayers();
    requestAnimationFrame(gameLoop);
}

// --- Input Handling ---

document.addEventListener("keydown", (e) => {
    keysPressed.add(e.key.toLowerCase());

    if (e.code === 'KeyR') {
        // When player presses R, send push event
        socket.emit('player_push', {
            x: playerX,
            y: playerY,
            room: ROOM_ID
        });
    }
});

document.addEventListener("keyup", (e) => {
    keysPressed.delete(e.key.toLowerCase());
});

// --- Ready Up Button ---

function readyUp() {
    socket.emit('player_ready', { room: ROOM_ID });
    const button = document.getElementById("readyButton");
    if (button) {
        button.remove();
    }
}