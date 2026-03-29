/* Currency toggle */
async function setCurrency(cur) {
    await fetch('/api/currency', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({currency: cur}),
    });
    location.reload();
}

/* Helpers */
function splitField(val) {
    return val ? val.split(',').map(s => s.trim()).filter(Boolean) : [];
}

/* Add route */
async function addRoute(e) {
    e.preventDefault();
    const cabins = Array.from(document.querySelectorAll('input[name="cabin"]:checked')).map(cb => cb.value);
    const ages = Array.from(document.querySelectorAll('#addForm input[name="traveler_age"]')).map(inp => parseInt(inp.value) || 30);
    const body = {
        origin: document.getElementById('origin').value.toUpperCase(),
        destination: document.getElementById('destination').value.toUpperCase(),
        departure_date: document.getElementById('departure_date').value,
        return_date: document.getElementById('return_date').value || null,
        is_round_trip: document.getElementById('is_round_trip').checked,
        cabin_types: cabins,
        airlines: splitField(document.getElementById('airlines').value),
        alliances: splitField(document.getElementById('alliances').value),
        travelers: ages,
    };
    const res = await fetch('/api/routes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });
    if (res.ok) location.reload();
    else alert('Failed to add route. Check your input.');
}

/* Route actions */
async function toggleRoute(id) {
    await fetch(`/api/routes/${id}/toggle`, {method: 'PATCH'});
    location.reload();
}

async function checkRoute(id) {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Checking\u2026';
    await fetch(`/api/routes/${id}/check`, {method: 'POST'});
    location.reload();
}

async function deleteRoute(id) {
    if (confirm('Delete this route and all its data?')) {
        await fetch(`/api/routes/${id}`, {method: 'DELETE'});
        location.reload();
    }
}

/* Travelers */
function addTraveler() {
    const list = document.getElementById('travelers-list');
    const row = document.createElement('div');
    row.className = 'traveler-row';
    row.innerHTML = '<input type="number" name="traveler_age" value="30" min="0" max="120" placeholder="Age">' +
        '<button type="button" class="btn-sm btn-danger" onclick="removeTraveler(this)">Remove</button>';
    list.appendChild(row);
}

function removeTraveler(btn) {
    const list = btn.closest('#travelers-list, #edit-travelers-list');
    if (list && list.children.length > 1) btn.parentElement.remove();
}

function toggleReturnDate() {
    const rt = document.getElementById('is_round_trip');
    const rd = document.getElementById('return_date');
    if (rd) rd.required = rt.checked;
}

/* Edit modal */
function openEditModal(id, route) {
    document.getElementById('edit_route_id').value = id;
    document.getElementById('edit_departure_date').value = route.departure_date || '';
    document.getElementById('edit_return_date').value = route.return_date || '';
    document.getElementById('edit_is_round_trip').checked = route.is_round_trip;
    document.getElementById('edit_airlines').value = (route.airlines || []).join(', ');
    document.getElementById('edit_alliances').value = (route.alliances || []).join(', ');

    document.querySelectorAll('input[name="edit_cabin"]').forEach(cb => {
        cb.checked = (route.cabin_types || []).includes(cb.value);
    });

    const tList = document.getElementById('edit-travelers-list');
    tList.innerHTML = '';
    (route.travelers || [30]).forEach(age => {
        const row = document.createElement('div');
        row.className = 'traveler-row';
        row.innerHTML = `<input type="number" name="edit_traveler_age" value="${age}" min="0" max="120" placeholder="Age">` +
            '<button type="button" class="btn-sm btn-danger" onclick="removeTraveler(this)">Remove</button>';
        tList.appendChild(row);
    });

    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

function addEditTraveler() {
    const list = document.getElementById('edit-travelers-list');
    const row = document.createElement('div');
    row.className = 'traveler-row';
    row.innerHTML = '<input type="number" name="edit_traveler_age" value="30" min="0" max="120" placeholder="Age">' +
        '<button type="button" class="btn-sm btn-danger" onclick="removeTraveler(this)">Remove</button>';
    list.appendChild(row);
}

async function saveEdit(e) {
    e.preventDefault();
    const id = document.getElementById('edit_route_id').value;
    const cabins = Array.from(document.querySelectorAll('input[name="edit_cabin"]:checked')).map(cb => cb.value);
    const ages = Array.from(document.querySelectorAll('input[name="edit_traveler_age"]')).map(inp => parseInt(inp.value) || 30);
    const body = {
        departure_date: document.getElementById('edit_departure_date').value || null,
        return_date: document.getElementById('edit_return_date').value || null,
        is_round_trip: document.getElementById('edit_is_round_trip').checked,
        cabin_types: cabins,
        airlines: splitField(document.getElementById('edit_airlines').value),
        alliances: splitField(document.getElementById('edit_alliances').value),
        travelers: ages,
    };
    const res = await fetch(`/api/routes/${id}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });
    if (res.ok) location.reload();
    else alert('Failed to update route.');
}
