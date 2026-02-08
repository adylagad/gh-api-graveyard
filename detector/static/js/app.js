// Main dashboard JavaScript

const API_BASE = '/api';

// Format date nicely
function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    }
    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }
    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
    }
    // Format as date
    return date.toLocaleDateString();
}

// Format number with commas
function formatNumber(num) {
    return num.toLocaleString();
}

// Load dashboard summary
async function loadSummary() {
    try {
        const response = await fetch(`${API_BASE}/dashboard/summary`);
        const data = await response.json();
        
        document.getElementById('stat-services').textContent = data.services;
        document.getElementById('stat-endpoints').textContent = formatNumber(data.total_endpoints);
        document.getElementById('stat-unused').textContent = `${formatNumber(data.unused_endpoints)} (${data.unused_percentage}%)`;
        document.getElementById('stat-savings').textContent = `$${data.monthly_savings.toFixed(2)}`;
    } catch (error) {
        console.error('Error loading summary:', error);
        document.querySelectorAll('.loading').forEach(el => {
            el.textContent = 'Error';
        });
    }
}

// Load services list
async function loadServices() {
    try {
        const response = await fetch(`${API_BASE}/services`);
        const services = await response.json();
        
        const tbody = document.getElementById('services-table');
        
        if (services.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-gray-500">No services found. Run a scan first!</td></tr>';
            return;
        }
        
        tbody.innerHTML = services.map(service => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">${service.name}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">${service.total_endpoints}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${service.unused_endpoints > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
                        ${service.unused_endpoints}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">${service.unused_percentage}%</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${formatDate(service.last_scan)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <a href="/service.html?name=${encodeURIComponent(service.name)}" class="text-indigo-600 hover:text-indigo-900 mr-3">View</a>
                    <a href="/trends.html?service=${encodeURIComponent(service.name)}" class="text-green-600 hover:text-green-900">Trends</a>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading services:', error);
        document.getElementById('services-table').innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-red-500">Error loading services</td></tr>';
    }
}

// Load recent scans
async function loadScans() {
    try {
        const response = await fetch(`${API_BASE}/scans?limit=10`);
        const scans = await response.json();
        
        const tbody = document.getElementById('scans-table');
        
        if (scans.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-gray-500">No scans found</td></tr>';
            return;
        }
        
        tbody.innerHTML = scans.map(scan => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    #${scan.id}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">${scan.service_name}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${formatDate(scan.timestamp)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${scan.total_endpoints}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${scan.unused_endpoints > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
                        ${scan.unused_endpoints}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${scan.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                        ${scan.success ? '✓ Success' : '✗ Failed'}
                    </span>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading scans:', error);
        document.getElementById('scans-table').innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-red-500">Error loading scans</td></tr>';
    }
}

// Refresh all data
function refreshData() {
    loadSummary();
    loadServices();
    loadScans();
}

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    refreshData();
    
    // Auto-refresh every 30 seconds
    setInterval(refreshData, 30000);
});
