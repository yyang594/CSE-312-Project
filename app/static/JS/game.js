const socket = io(); // Connect to WebSocket

let players = {};
let myId = null;
let score = 0;
let startTime = Date.now();

socket.on("connect", () => {
    myId = socket.id;
    socket.emit("join_room", { room: ROOM_ID })
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
var speed = 3;

const keysPressed = new Set();

//Format: [Question]: [Answer1, Answer2, Answer3, Answer4, Solution]
questionSet = {
    // "What is 1 + 1?": ["1", "2", "3", "4", "2"],
    // "What color is the sky?": ["magenta", "blue", "hot pink", "green", "blue"],
    // "What produces light?": ["Moon", "Concrete", "Leaf", "Sun", "Sun"]
}
async function fetchTriviaQuestions(amount = 10) {
    try {
        const response = await fetch(`https://opentdb.com/api.php?amount=${amount}&type=multiple`);
        const data = await response.json();
        const results = data.results;

        if (results && results.length > 0) {
            results.forEach(result => {
                const question = decodeHTML(result.question);
                const correctAnswer = decodeHTML(result.correct_answer);
                const incorrectAnswers = result.incorrect_answers.map(ans => decodeHTML(ans));

                const allAnswers = [...incorrectAnswers, correctAnswer];
                shuffleArray(allAnswers);

                questionSet[question] = [
                    allAnswers[0],
                    allAnswers[1],
                    allAnswers[2],
                    allAnswers[3],
                    correctAnswer
                ];
            });

            console.log('Trivia questions loaded into questionSet:', questionSet);

            // Now start the game AFTER loading questions
            startGame();
        } else {
            console.error('No trivia questions found.');
        }
    } catch (error) {
        console.error('Error fetching trivia questions:', error);
    }
}

function decodeHTML(html) {
    const txt = document.createElement('textarea');
    txt.innerHTML = html;
    return txt.value;
}

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

// Fetch the trivia questions immediately when page loads
fetchTriviaQuestions();

let intervalId;  // Move intervalId here globally

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
    clearInterval(intervalId); // Clear old timer if it exists

    const timerElement = document.getElementById("timer");
    let totalTime = 30;

    timerElement.innerHTML = `00:${totalTime}`;

    intervalId = setInterval(function () {
        totalTime -= 1;
        timerElement.innerHTML = `00:${totalTime < 10 ? "0" + totalTime : totalTime}`;

        if (totalTime <= 0) {
            clearInterval(intervalId);
            askNewQuestion();  // Ask new question
            playerState = "Default"
            startTimer();      // Restart timer for new question
        }
    }, 1000);
}


// var currentQuestion = getRandomKey(questionSet)
// questionDisplay.innerHTML = currentQuestion
// var solution = questionSet[currentQuestion].pop()
// var answers = questionSet[currentQuestion]
var solutionParameter;
var isGameRunning = true;

canvas.height = window.innerHeight;
canvas.width = window.innerWidth;
let playerX = canvas.width / 2;
let playerY = canvas.height / 2;
var playerState = "Default";
var rectXBound, rectYBound;
var playerScore = 0;

//Timer
//Change maxTime to change countdown
const timer = document.getElementById("timer")
var maxTime = 5
var totalTime = maxTime

//For adding score to total
var toAdd = 0

function countdown() {
    totalTime -= 1;
    updateTimerDisplay();

    if (totalTime <= 0) {
        clearInterval(intervalId);
        playerState = "Default"; // Reset player lock state
        askNewQuestion();
        startTimer();
    }
}

//This should take in a dict(key) which would be the list of answers and the solution
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
        socket.emit("move", { id: myId, x: playerX, y: playerY, room: ROOM_ID });
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
        ctx.fillStyle = "white";
        ctx.textAlign = "center";
        ctx.fillText(p.name || "Guest", p.x, p.y + radius + 10);
    }
}

document.addEventListener("keydown", (e) => {
    keysPressed.add(e.key.toLowerCase());

    if (e.code === 'Space') {
        e.preventDefault(); // Prevents scroll
        console.log('Spacebar pressed!');
        //Disable everything
        playerState = "Locked"
        //Make the avatar slightly green
        
        //UNDO LATER
        document.getElementById('avatar').style.filter = 'hue-rotate(90deg)';

        let elapsed = (Date.now() - startTime) / 1000; // seconds
        const MAX_SCORE = 1000;

        elapsed = Math.min(elapsed, maxTime);

        // CALCULATE SCORE HERE
        let currentScore = Math.round(MAX_SCORE * ((maxTime - elapsed) / maxTime));
        currentScore = Math.max(currentScore, 0); // no negative scores

        toAdd += currentScore;
        //console.log(`Scored ${currentScore} points! Total Score: ${score}`);

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
    for (let rect = 0; rect < rectParemeters.length; rect++) {
        let currentRect = rectParemeters[rect];
        ctx.fillStyle = currentRect[6];
        ctx.fillRect(currentRect[0], currentRect[1], currentRect[2], currentRect[3]);
    
        ctx.fillStyle = "white";
        ctx.font = '20px sans-serif';
        ctx.textAlign = "center";      // ADDED THIS
        ctx.textBaseline = "middle";   // ANDED THIS
        ctx.fillText(currentRect[7], currentRect[4], currentRect[5]);
        
        if (currentRect[currentRect.length-1] == true) {
            solutionParameter = [currentRect[0], currentRect[1], currentRect[2], currentRect[3]];
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