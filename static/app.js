function getCsrfToken() {
    var match = document.cookie.match('(^|;)\\s*csrf_token=([^;]+)');
    return match ? match[2] : '';
}

/* Close user dropdown when clicking outside */
document.addEventListener('click', function(e) {
    document.querySelectorAll('.user-menu.open').forEach(function(m) {
        if (!m.contains(e.target)) m.classList.remove('open');
    });
});

/* Language toggle */
async function setLanguage(lang) {
    await fetch('/api/language', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json', 'x-csrf-token': getCsrfToken()},
        body: JSON.stringify({language: lang}),
    });
    location.reload();
}

/* Currency toggle - changes preference, reloads to show converted prices */
async function setCurrency(cur) {
    await fetch('/api/currency', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json', 'x-csrf-token': getCsrfToken()},
        body: JSON.stringify({currency: cur}),
    });
    location.reload();
}

/* Helpers */
function splitField(val) {
    return val ? val.split(',').map(function(s) { return s.trim(); }).filter(Boolean) : [];
}

/* Add route */
async function addRoute(e) {
    e.preventDefault();
    var cabins = [];
    document.querySelectorAll('#addForm input[name="cabin"]:checked').forEach(function(cb) { cabins.push(cb.value); });
    var ages = [];
    document.querySelectorAll('#addForm input[name="traveler_age"]').forEach(function(inp) { ages.push(parseInt(inp.value) || 30); });
    var body = {
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
    var res = await fetch('/api/routes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'x-csrf-token': getCsrfToken()},
        body: JSON.stringify(body),
    });
    if (res.ok) location.reload();
    else alert('Failed to add route. Check your input.');
}

/* Route actions */
async function toggleRoute(id) {
    await fetch('/api/routes/' + id + '/toggle', {method: 'PATCH', headers: {'x-csrf-token': getCsrfToken()}});
    location.reload();
}

async function checkRoute(id) {
    var btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Checking\u2026';
    await fetch('/api/routes/' + id + '/check', {method: 'POST', headers: {'x-csrf-token': getCsrfToken()}});
    location.reload();
}

async function deleteRoute(id) {
    if (confirm('Delete this route and all its data?')) {
        await fetch('/api/routes/' + id, {method: 'DELETE', headers: {'x-csrf-token': getCsrfToken()}});
        location.reload();
    }
}

/* Travelers */
function addTraveler() {
    var list = document.getElementById('travelers-list');
    var row = document.createElement('div');
    row.className = 'traveler-row';
    row.innerHTML = '<input type="number" name="traveler_age" value="30" min="0" max="120" placeholder="Age">' +
        '<button type="button" class="btn-sm btn-danger" onclick="removeTraveler(this)">Remove</button>';
    list.appendChild(row);
}

function removeTraveler(btn) {
    var list = btn.closest('#travelers-list') || btn.closest('#edit-travelers-list');
    if (list && list.children.length > 1) btn.parentElement.remove();
}

function toggleReturnDate() {
    var rt = document.getElementById('is_round_trip');
    var rd = document.getElementById('return_date');
    if (rd) rd.required = rt.checked;
}

/* Nearby dates toggle */
function toggleNearby(selectEl, routeId) {
    var maxOffset = parseInt(selectEl.value) || 0;
    var container = document.getElementById('nearby-' + routeId);
    if (!container) return;
    if (maxOffset === 0) {
        container.style.display = 'none';
        return;
    }
    container.style.display = '';
    var items = container.querySelectorAll('[data-offset]');
    items.forEach(function(el) {
        var offset = parseInt(el.getAttribute('data-offset')) || 0;
        el.style.display = offset <= maxOffset ? '' : 'none';
    });
}

/* Edit modal */
function openEditModal(btn) {
    var id = btn.getAttribute('data-route-id');
    var route = JSON.parse(btn.getAttribute('data-route'));
    document.getElementById('edit_route_id').value = id;
    document.getElementById('edit_departure_date').value = route.departure_date || '';
    document.getElementById('edit_return_date').value = route.return_date || '';
    document.getElementById('edit_is_round_trip').checked = route.is_round_trip;
    document.getElementById('edit_airlines').value = (route.airlines || []).join(', ');
    document.getElementById('edit_alliances').value = (route.alliances || []).join(', ');

    /* Set cabin checkboxes */
    var cabinTypes = route.cabin_types || [];
    document.querySelectorAll('#editForm input[name="edit_cabin"]').forEach(function(cb) {
        cb.checked = cabinTypes.indexOf(cb.value) !== -1;
    });

    /* Build traveler rows */
    var tList = document.getElementById('edit-travelers-list');
    tList.innerHTML = '';
    var travelers = route.travelers || [30];
    travelers.forEach(function(age) {
        var row = document.createElement('div');
        row.className = 'traveler-row';
        row.innerHTML = '<input type="number" name="edit_traveler_age" value="' + age + '" min="0" max="120" placeholder="Age">' +
            '<button type="button" class="btn-sm btn-danger" onclick="removeTraveler(this)">Remove</button>';
        tList.appendChild(row);
    });

    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

function addEditTraveler() {
    var list = document.getElementById('edit-travelers-list');
    var row = document.createElement('div');
    row.className = 'traveler-row';
    row.innerHTML = '<input type="number" name="edit_traveler_age" value="30" min="0" max="120" placeholder="Age">' +
        '<button type="button" class="btn-sm btn-danger" onclick="removeTraveler(this)">Remove</button>';
    list.appendChild(row);
}

async function saveEdit(e) {
    e.preventDefault();
    var id = document.getElementById('edit_route_id').value;
    var cabins = [];
    document.querySelectorAll('#editForm input[name="edit_cabin"]:checked').forEach(function(cb) { cabins.push(cb.value); });
    var ages = [];
    document.querySelectorAll('#editForm input[name="edit_traveler_age"]').forEach(function(inp) { ages.push(parseInt(inp.value) || 30); });
    var body = {
        cabin_types: cabins,
        travelers: ages,
        airlines: splitField(document.getElementById('edit_airlines').value),
        alliances: splitField(document.getElementById('edit_alliances').value),
    };
    var depDate = document.getElementById('edit_departure_date').value;
    var retDate = document.getElementById('edit_return_date').value;
    if (depDate) body.departure_date = depDate;
    if (retDate) body.return_date = retDate;
    body.is_round_trip = document.getElementById('edit_is_round_trip').checked;

    var res = await fetch('/api/routes/' + id, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json', 'x-csrf-token': getCsrfToken()},
        body: JSON.stringify(body),
    });
    if (res.ok) location.reload();
    else alert('Failed to update route.');
}
