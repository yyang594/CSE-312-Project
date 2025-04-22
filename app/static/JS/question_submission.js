let questionCount = 0;

function addQuestion() {
    questionCount++;
    const container = document.getElementById("questionsContainer");

    const block = document.createElement("div");
    block.className = "question-block";

    block.innerHTML = `
        <h4>Question ${questionCount+1}</h3>
        <label>Question:</label><br>
        <input type="text" name="question[]" required><br><br>

        <label>Possible Answers:</label><br>
        <input type="text" name="answer[]" required>
        <input type="text" name="answer[]" required>
        <input type="text" name="answer[]" required>
        <input type="text" name="answer[]" required>

        <label>Correct Answer:</label><br>
        <input type="text" name="correct_answer[]" required><br>
    `;

    container.appendChild(block);
}