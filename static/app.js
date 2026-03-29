function splitField(val) {
    return val ? val.split(",").map(s => s.trim()).filter(Boolean) : [];
}

async function addRoute(e) {
    e.preventDefault();
    const cabins = Array.from(document.querySelectorAll('input[name="cabin"]:checked')).map(cb => cb.value);
    const travelerAges = Array.from(document.querySelectorAll('input[name="traveler_age"]')).map(inp => parseInt(inp.value) || 30);

    const body = {
        origin: document.getElementById("origin").value.toUpperCase(),
        destination: document.getElementById("destination").value.toUpperCase(),
        departure_date: document.getElementById("departure_date").value,
        return_date: document.getElementById("return_date").value || null,
        is_round_trip: document.getElementById("is_round_trip").checked,
        cabin_types: cabins,
        airlines: splitField(document.getElementById("airlines").value),
        alliances: splitField(document.getElementById("alliances").value),
        travelers: travelerAges,
    };

    const res = await fetch("/api/routes", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
    });

    if (res.ok) {
        location.reload();
    } else {
        alert("Failed to add route. Check your input.");
    }
}

async function toggleRoute(id) {
    await fetch(`/api/routes/${id}/toggle`, {method: "PATCH"});
    location.reload();
}

async function checkRoute(id) {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = "Checking...";
    await fetch(`/api/routes/${id}/check`, {method: "POST"});
    location.reload();
}

async function deleteRoute(id) {
    if (confirm("Delete this route and all its data?")) {
        await fetch(`/api/routes/${id}`, {method: "DELETE"});
        location.reload();
    }
}

function addTraveler() {
    const list = document.getElementById("travelers-list");
    const row = document.createElement("div");
    row.className = "traveler-row";
    row.innerHTML = '<label>Age: <input type="number" name="traveler_age" value="30" min="0" max="120"></label>' +
        '<button type="button" class="btn-small" onclick="removeTraveler(this)">Remove</button>';
    list.appendChild(row);
}

function removeTraveler(btn) {
    const list = document.getElementById("travelers-list");
    if (list.children.length > 1) {
        btn.parentElement.remove();
    }
}

function toggleReturnDate() {
    const rt = document.getElementById("is_round_trip");
    const rd = document.getElementById("return_date");
    if (rd) rd.required = rt.checked;
}
