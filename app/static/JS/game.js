const socket = io(); // Connect to WebSocket

let players = {};
let myId = null;
let score = 0;
let startTime = Date.now();

let questionSet = {}; // Questions sent by server
let intervalId;
let maxTime = 30;
let totalTime = maxTime;
let playerState = "Default";
let currentQuestion;
let answers;
let solution;
let solutionParameter = [];

let playerScore = 0;
let rewardScore = 200;

const canvas = document.getElementById("Canvas");
const ctx = canvas.getContext("2d");

const questionDisplay = document.getElementById("questionBox");
const timerElement = document.getElementById("timer");

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

socket.on("start_game", function(data) {
    console.log("Received start_game from server");

    const waitingRoom = document.getElementById("waitingRoom");
    if (waitingRoom) waitingRoom.style.display = "none";

    const gameContainer = document.getElementById("gameContainer");
    if (gameContainer) gameContainer.style.display = "block";

    loadQuestions(data.questions);
    startGame();
});

socket.on('update_lobby', function(players) {
    const playerList = document.getElementById('player-list');
    playerList.innerHTML = '';

    for (const id in players) {
        const player = players[id];
        const li = document.createElement('li');
        li.textContent = player.username + (player.ready ? ' ✅' : ' ❌');
        playerList.appendChild(li);
    }
});

socket.on('next_question', function(data) {
    currentQuestion = data.question;
    answers = [...data.answers];
    solution = data.solution;
    questionDisplay.innerHTML = currentQuestion;
});

socket.on('player_pushed', function(data) {
    const pushX = data.x;
    const pushY = data.y;
    const pushRadius = 100;
    const pushStrength = 50;

    for (const id in players) {
        if (id === data.pusherId) continue;

        const other = players[id];
        const dx = other.x - pushX;
        const dy = other.y - pushY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < pushRadius) {
            const factor = (pushRadius - distance) / pushRadius;
            players[id].x += (dx / distance) * pushStrength * factor;
            players[id].y += (dy / distance) * pushStrength * factor;
        }
    }

    // --- THEN sync ---
    socket.emit('sync_positions', { players: players, room: ROOM_ID });
});

socket.on('update_positions', function(updatedPlayers) {
    players = updatedPlayers;

    if (players[myId]) {
        playerX = players[myId].x;
        playerY = players[myId].y;
    }
});

// --- Game Logic ---

function loadQuestions(questionsFromServer) {
    questionSet = {};
    questionsFromServer.forEach(q => {
        questionSet[q.question] = [...q.answers, q.solution];
    });
}

function startGame() {
    requestNewQuestion();
    startTimer();
    requestAnimationFrame(gameLoop);
}

function requestNewQuestion() {
    socket.emit('request_next_question', { room: ROOM_ID });
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

    let rectXBound = solutionParameter[0] + solutionParameter[2];
    let rectYBound = solutionParameter[1] + solutionParameter[3];

    if (totalTime <= 0) {
        if (playerX > solutionParameter[0] && playerX < rectXBound &&
            playerY > solutionParameter[1] && playerY < rectYBound) {
            playerScore += rewardScore;
            console.log("You got the question right!");
            console.log(`Your score is: ${playerScore}`);
        }

        clearInterval(intervalId);
        playerState = "Default";
        requestNewQuestion();
        startTimer();
    }
}

function updateTimerDisplay() {
    timerElement.innerHTML = "00:" + (totalTime < 10 ? "0" + totalTime : totalTime);
}

// --- Drawing and Movement ---

canvas.height = window.innerHeight;
canvas.width = window.innerWidth - 275;
const radius = 10;
var speed = 3;
const keysPressed = new Set();
let playerX = canvas.width / 2;
let playerY = canvas.height / 2;

function drawCircle() {
    ctx.beginPath();
    ctx.arc(playerX, playerY, radius, 0, 2 * Math.PI);
    ctx.fillStyle = "teal";
    ctx.fill();
    ctx.stroke();

    ctx.font = "12px Arial";
    ctx.fillStyle = "black";
    ctx.textAlign = "center";
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

// --- Game Loop ---

function gameLoop() {
    if (speed !== 3) {
        speed -= 1;
    }

    setUp();
    if (playerState === "Default") {
        updatePosition();
    }
    drawPlayers();
    drawCircle();
    requestAnimationFrame(gameLoop);
}

// --- Input Handling ---

document.addEventListener("keydown", (e) => {
    keysPressed.add(e.key.toLowerCase());

    if (e.code === 'Space') {
        e.preventDefault();
        if (playerState === "Locked") return;

        playerState = "Locked";
        document.getElementById('avatar').style.filter = 'hue-rotate(90deg)';

        let elapsed = (Date.now() - startTime) / 1000;
        const MAX_TIME = 10;
        const MAX_SCORE = 1000;

        elapsed = Math.min(elapsed, MAX_TIME);
        let currentScore = Math.round(MAX_SCORE * ((MAX_TIME - elapsed) / MAX_TIME));
        currentScore = Math.max(currentScore, 0);

        score += currentScore;
        console.log(`Scored ${currentScore} points! Total Score: ${score}`);
        document.getElementById("scoreDisplay").innerText = score;

        socket.emit("update_score", {
            score: score,
            user_id: USER_ID,
            room: ROOM_ID
        });

        startTime = Date.now();
    }

    // 🔥 R key for pushing players
    if (e.code === 'KeyR') {
        socket.emit('player_push', { x: playerX, y: playerY, room: ROOM_ID, pusherId: myId });
    }

    if (e.code === 'ShiftLeft') {
        speed = 15; // Dash
    }
});

document.addEventListener("keyup", (e) => {
    keysPressed.delete(e.key.toLowerCase());
});

// --- Ready Up Button ---

function readyUp() {
    socket.emit('player_ready', { room: ROOM_ID });
    console.log("Ready pressed!");

    const button = document.getElementById("readyButton");
    if (button) {
        button.remove();
    }
}