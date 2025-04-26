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

const canvas = document.getElementById("Canvas");
const ctx = canvas.getContext("2d");

const questionDisplay = document.getElementById("questionBox");
const timerElement = document.getElementById("timer");

// --- Socket Events ---

socket.on("connect", () => {
    myId = socket.id;
    socket.emit("join_room", { room: ROOM_ID }); // Tell server what room we joined
});

socket.on("start_game", function(data) {
    console.log("Received start_game from server");
    loadQuestions(data.questions);
    startGame();
});

// --- Game Logic ---

function loadQuestions(questionsFromServer) {
    questionSet = {};
    questionsFromServer.forEach(q => {
        questionSet[q.question] = [...q.answers, q.solution];
    });
}

function startGame() {
    askNewQuestion();
    startTimer();
    requestAnimationFrame(gameLoop);
}

function askNewQuestion() {
    currentQuestion = getRandomKey(questionSet);
    questionDisplay.innerHTML = currentQuestion;

    let allAnswers = [...questionSet[currentQuestion]];
    solution = allAnswers.pop();
    answers = allAnswers;
}

function startTimer() {
    clearInterval(intervalId); // Always clear old timers
    totalTime = maxTime;
    updateTimerDisplay();

    const timerElement = document.getElementById("timer");
    let totalTime = 5;
    intervalId = setInterval(countdown, 1000);
}

// var currentQuestion = getRandomKey(questionSet)
// questionDisplay.innerHTML = currentQuestion
// var solution = questionSet[currentQuestion].pop()
// var answers = questionSet[currentQuestion]
var isGameRunning = true;

canvas.height = window.innerHeight;
canvas.width = window.innerWidth;
var rectXBound, rectYBound;
var playerScore = 0;

//Timer

//For adding score to total
/*
var toAdd = 0

function countdown() {
    totalTime -= 1
    timer.innerHTML = "00:" + totalTime
    if (totalTime == 0){
        totalTime = maxTime

        rectXBound = solutionParameter[0]+solutionParameter[2]
        rectYBound = solutionParameter[1]+solutionParameter[3]

        //console.log(`You are at position: (${playerX},${playerY})`)
        ctx.willReadFrequently = true;  //Efficiency (Optional (Solely for getImageData))
        //console.log(`You have chosen: (${ctx.getImageData(playerX, playerY, 1, 1).data})`)
        if(playerX > solutionParameter[0] && playerX < rectXBound && playerY > solutionParameter[1] && playerY < rectYBound){
            score += toAdd
            console.log(`Your score is ${score}`)
        }

        toAdd = 0


        delete questionSet[currentQuestion];
        
        currentQuestion = getRandomKey(questionSet)
        questionDisplay.innerHTML = currentQuestion

        if(currentQuestion == undefined){
            //End the game
            isGameRunning = false
        }

        //Release Player State
        playerState = "Default"
    }
}


//This should take in a dict(key) which would be the list of answers and the solution
    if (totalTime <= 0) {
        clearInterval(intervalId);
        playerState = "Default";
        askNewQuestion();
        startTimer();
    }
}
*/

function updateTimerDisplay() {
    timerElement.innerHTML = "00:" + (totalTime < 10 ? "0" + totalTime : totalTime);
}

function getRandomKey(dict) {
    const keys = Object.keys(dict);
    const randomIndex = Math.floor(Math.random() * keys.length);
    return keys[randomIndex];
}

// --- Drawing and Movement ---

canvas.height = window.innerHeight;
canvas.width = window.innerWidth - 275; // Adjust for sidebar
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

    let rectWidth = canvas.width * 0.4;
    let rectHeight = canvas.height * 0.4;

    answers = questionSet[currentQuestion];
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
        e.preventDefault(); // Prevents scroll
        console.log('Spacebar pressed!');
        //Disable everything
        playerState = "Locked"
        //Make the avatar slightly green
        
        //UNDO LATER
        e.preventDefault();
        if (playerState === "Locked") return;

        playerState = "Locked";
        document.getElementById('avatar').style.filter = 'hue-rotate(90deg)';

        let elapsed = (Date.now() - startTime) / 1000;
        const MAX_TIME = 10;
        const MAX_SCORE = 1000;

        elapsed = Math.min(elapsed, maxTime);

        // CALCULATE SCORE HERE
        let currentScore = Math.round(MAX_SCORE * ((maxTime - elapsed) / maxTime));
        currentScore = Math.max(currentScore, 0); // no negative scores
        elapsed = Math.min(elapsed, MAX_TIME);

        toAdd += currentScore;
        //console.log(`Scored ${currentScore} points! Total Score: ${score}`);

        score += currentScore;
        console.log(`Scored ${currentScore} points! Total Score: ${score}`);
        document.getElementById("scoreDisplay").innerText = score;

        socket.emit("update_score", { 
            score: score, 
            user_id: USER_ID, 
            room: ROOM_ID 
        });

        // Reset timer
        startTime = Date.now();
    }
    if (e.code === 'ShiftLeft'){
        //Dash
        console.log("ShiftLeft Pressed")
        speed = 15
    }
});

document.addEventListener("keyup", (e) => {
    keysPressed.delete(e.key.toLowerCase());
});

function setUp(){
    canvas.width = window.innerWidth-270;
    canvas.height = window.innerHeight-170;
    let rectWidth = canvas.width*0.4
    let rectHeight = canvas.height*0.4

    answers = questionSet[currentQuestion]
    let rectParemeters = [
        //Format: NW, NE, SW, SE
        //Format: [x, y, width, height, textX, textY, color, answer, T/F Solution]
        [0, 0, rectWidth, rectHeight, rectWidth/2, rectHeight/2, "red", answers[0], solution === answers[0]],
        [canvas.width-rectWidth, 0, rectWidth, rectHeight, canvas.width-rectWidth + rectWidth/2, rectHeight/2, "blue", answers[1], solution === answers[1]],
        [0, canvas.height-rectHeight, rectWidth, rectHeight, rectWidth/2, canvas.height-rectHeight + rectHeight/2, "orange", answers[2], solution === answers[2]],
        [canvas.width-rectWidth, canvas.height-rectHeight, rectWidth, rectHeight, canvas.width-rectWidth + rectWidth/2, canvas.height-rectHeight + rectHeight/2, "green", answers[3], solution === answers[3]]
    ]

    //Format: [x, y, width, height, textX, textY, color, answer]
    for (let rect = 0; rect < rectParemeters.length; rect++){
        let currentRect = rectParemeters[rect]
        ctx.fillStyle = currentRect[6];
        ctx.fillRect(currentRect[0], currentRect[1], currentRect[2], currentRect[3]);

        ctx.fillStyle = "white";
        ctx.font = '20px sans-serif';
        ctx.fillText(currentRect[7], currentRect[4], currentRect[5]);
        
        //GET PAREMETERS OF CORRECT RECTANGLE
        if(currentRect[currentRect.length-1] == true){
            solutionParameter = [currentRect[0], currentRect[1], currentRect[2], currentRect[3]]
        }
    }
}

function endScreen(){
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    gradient.addColorStop("0", "magenta");
    gradient.addColorStop("0.5", "blue");
    gradient.addColorStop("1.0", "red");

    // Fill with gradient
    ctx.fillStyle = gradient;
    ctx.font = "48px Arial";
    ctx.fillText("You Win!", 40, 90);
}

//Main loop
function gameLoop() {
    //Has game ended
    if(!isGameRunning){
        endScreen();
        console.log("End game")
        return
    }

    if(questionSet != {}){
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        setUp();
    }

    //Dash functionality
    if(speed !== 3){
        speed -= 1
    }
    
    if(playerState === "Default"){
        updatePosition();
    }
    drawPlayers(); // draw others first
    drawCircle();  // draw self
    requestAnimationFrame(gameLoop);
}

requestAnimationFrame(gameLoop);