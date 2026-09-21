document.addEventListener('DOMContentLoaded', () => {
    loadView('overview');
});

let currentFilters = {
    page: 1,
    page_size: 50,
    search: '',
    format: '',
    status: '',
    validation_status: ''
};

async function loadView(viewName) {
    const container = document.getElementById('view-container');
    container.innerHTML = '<p>Loading...</p>';

    if (viewName === 'overview') {
        try {
            const response = await fetch('/api/summary');
            const data = await response.json();
            
            container.innerHTML = `
                <div class="card">
                    <h3>Pipeline Overview</h3>
                    <p>Total Ingested: <span class="metric">${data.total_ingested}</span></p>
                    <p>Parse Successes: <span class="metric">${data.parse_successes}</span></p>
                    <p>Normalization Successes: <span class="metric">${data.normalization_successes}</span></p>
                    <p>Validation Successes: <span class="metric">${data.validation_successes}</span></p>
                    <p>Active Parsers: <span class="metric">${data.active_parsers}</span></p>
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<p style="color:red">Error loading overview data: ${error.message}</p>`;
        }
    } else if (viewName === 'events') {
        renderEventsView(container);
    } else {
        container.innerHTML = `
            <div class="card">
                <h3>${viewName.charAt(0).toUpperCase() + viewName.slice(1)}</h3>
                <p>This view is under construction.</p>
            </div>
        `;
    }
}

async function renderEventsView(container) {
    container.innerHTML = `
        <div class="card">
            <h3>Event Explorer</h3>
            <div class="filters">
                <input type="text" id="filter-search" placeholder="Search ID..." value="${currentFilters.search}">
                <select id="filter-format">
                    <option value="">All Formats</option>
                    <option value="syslog" ${currentFilters.format === 'syslog' ? 'selected' : ''}>Syslog</option>
                </select>
                <select id="filter-status">
                    <option value="">All Statuses</option>
                    <option value="SUCCESS" ${currentFilters.status === 'SUCCESS' ? 'selected' : ''}>SUCCESS</option>
                    <option value="PARSE_FAILED" ${currentFilters.status === 'PARSE_FAILED' ? 'selected' : ''}>PARSE_FAILED</option>
                    <option value="NORM_FAILED" ${currentFilters.status === 'NORM_FAILED' ? 'selected' : ''}>NORM_FAILED</option>
                    <option value="VALIDATION_FAILED" ${currentFilters.status === 'VALIDATION_FAILED' ? 'selected' : ''}>VALIDATION_FAILED</option>
                </select>
                <button onclick="applyFilters()">Apply</button>
            </div>
            <div id="events-table-container"><p>Loading events...</p></div>
        </div>
    `;
    loadEvents();
}

function applyFilters() {
    currentFilters.search = document.getElementById('filter-search').value;
    currentFilters.format = document.getElementById('filter-format').value;
    currentFilters.status = document.getElementById('filter-status').value;
    currentFilters.page = 1;
    loadEvents();
}

async function loadEvents() {
    const tableContainer = document.getElementById('events-table-container');
    tableContainer.innerHTML = '<p>Loading events...</p>';
    
    try {
        const queryParams = new URLSearchParams();
        queryParams.append('page', currentFilters.page);
        queryParams.append('page_size', currentFilters.page_size);
        if (currentFilters.search) queryParams.append('search', currentFilters.search);
        if (currentFilters.format) queryParams.append('format', currentFilters.format);
        if (currentFilters.status) queryParams.append('status', currentFilters.status);
        if (currentFilters.validation_status) queryParams.append('validation_status', currentFilters.validation_status);

        const response = await fetch(`/api/events?${queryParams.toString()}`);
        if (!response.ok) throw new Error('API failure');
        const data = await response.json();
        
        if (data.items.length === 0) {
            tableContainer.innerHTML = '<p>No events found.</p>';
            return;
        }

        let tableHtml = `
            <table>
                <thead>
                    <tr>
                        <th>Event ID</th>
                        <th>Timestamp</th>
                        <th>Format</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.items.forEach(event => {
            tableHtml += `
                <tr onclick="loadEventDetail('${event.event_id}')">
                    <td>${event.event_id}</td>
                    <td>${event.timestamp}</td>
                    <td>${event.source_format}</td>
                    <td>${event.status}</td>
                </tr>
            `;
        });

        tableHtml += '</tbody></table>';
        
        tableHtml += `
            <div class="pagination">
                <button onclick="changePage(-1)" ${currentFilters.page <= 1 ? 'disabled' : ''}>Previous</button>
                <span>Page ${data.page}</span>
                <button onclick="changePage(1)" ${data.items.length < data.page_size ? 'disabled' : ''}>Next</button>
            </div>
        `;
        
        tableContainer.innerHTML = tableHtml;

    } catch (error) {
        tableContainer.innerHTML = `<p style="color:red">Failed to load events: ${error.message}</p>`;
    }
}

function changePage(delta) {
    currentFilters.page += delta;
    loadEvents();
}

async function loadEventDetail(eventId) {
    const container = document.getElementById('view-container');
    container.innerHTML = '<p>Loading event details...</p>';
    
    try {
        const [rawRes, parsedRes, normalizedRes, valRes] = await Promise.all([
            fetch(`/api/events/${eventId}/raw`),
            fetch(`/api/events/${eventId}/parsed`),
            fetch(`/api/events/${eventId}/normalized`),
            fetch(`/api/events/${eventId}/validation`)
        ]);

        const raw = await rawRes.json();
        const parsed = await parsedRes.json();
        const normalized = await normalizedRes.json();
        const validation = await valRes.json();
        
        // Escape raw log for safe rendering
        const escapeHtml = (unsafe) => {
            return (unsafe || '').toString()
                 .replace(/&/g, "&amp;")
                 .replace(/</g, "&lt;")
                 .replace(/>/g, "&gt;")
                 .replace(/"/g, "&quot;")
                 .replace(/'/g, "&#039;");
        };

        container.innerHTML = `
            <div class="card">
                <h3>Event Detail: ${eventId}</h3>
                <button onclick="loadView('events')">Back to Events</button>
                <hr style="margin:15px 0;">
                
                <div class="trace-section">
                    <h4>1. Raw Log</h4>
                    <pre id="raw-log-content"></pre>
                </div>

                <div class="trace-section">
                    <h4>2. Parsed Dictionary</h4>
                    <pre>${JSON.stringify(parsed, null, 2)}</pre>
                </div>

                <div class="trace-section">
                    <h4>3. Normalized OCSF</h4>
                    <pre>${JSON.stringify(normalized, null, 2)}</pre>
                </div>

                <div class="trace-section">
                    <h4>4. Validation</h4>
                    <pre>${JSON.stringify(validation, null, 2)}</pre>
                </div>
            </div>
        `;
        
        // Set raw log safely as text
        document.getElementById('raw-log-content').textContent = raw.raw_log || 'N/A';
        
    } catch (error) {
        container.innerHTML = `
            <div class="card">
                <h3>Event Detail</h3>
                <button onclick="loadView('events')">Back to Events</button>
                <p style="color:red">Error loading event details: ${error.message}</p>
            </div>
        `;
    }
}
