let leaderboardData = [{ player: "Test", wins: 999, correct: 999 }];
/*
    { player: "Alice", wins: 12, correct: 54 },
    { player: "Bob", wins: 9, correct: 45 },
    { player: "Charlie", wins: 5, correct: 49 }
*/
/*
fetch('/getInfo')
  .then(response => response.json())
  .then(data => {
    console.log("Received data from Flask:", data);
    leaderboardData = data
  })
  .catch(error => console.error('Error fetching data:', error));

console.log("LEADER BOARD STUFF:")
console.log(leaderboardData)
*/
async function loadAndSortLeaderboard() {
    try {
        const response = await fetch('/getInfo');
        const data = await response.json();
        console.log("Received data from Flask:", data);

        leaderboardData = data;
        sortLeaderboard();  // Only called after data is fetched
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function sortLeaderboard() {
    const sortBy = document.getElementById("sortSelect").value;
    const statHeader = document.getElementById("statHeader");
    const tbody = document.getElementById("leaderboardBody");

    // Update column header
    statHeader.textContent = sortBy === "wins" ? "Wins" : "Correct Answers";

    // Sort and render
    const sorted = [...leaderboardData].sort((a, b) => b[sortBy] - a[sortBy]);

    tbody.innerHTML = "";
    sorted.forEach((entry, index) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${entry.player}</td>
            <td>${entry[sortBy]}</td>
        `;
        tbody.appendChild(row);
    });
}

document.addEventListener("DOMContentLoaded", loadAndSortLeaderboard);

// Initial sort on page load
document.addEventListener("DOMContentLoaded", sortLeaderboard);
