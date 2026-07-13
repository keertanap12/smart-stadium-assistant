document.addEventListener('DOMContentLoaded', () => {
    // Tab switching elements
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Sub-tab switching inside Parking
    const subTabs = document.querySelectorAll('.panel-sub-tab');
    const subContents = document.querySelectorAll('.panel-sub-content');
    
    // Forms
    const addGateForm = document.getElementById('addGateForm');
    const addBatchForm = document.getElementById('addBatchForm');
    const addLotForm = document.getElementById('addLotForm');
    const resetBtn = document.getElementById('resetBtn');
    
    // Alert Banner
    const alertBanner = document.getElementById('alertBanner');

    // ==========================================================================
    // UTILITY FUNCTIONS
    // ==========================================================================
    
    function showAlert(message, type = 'success') {
        alertBanner.textContent = message;
        alertBanner.className = `alert-banner ${type}`;
        alertBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        // Auto-hide alert after 5 seconds
        setTimeout(() => {
            alertBanner.classList.add('hidden');
        }, 5000);
    }
    
    function formatPercentage(val) {
        return (val * 100).toFixed(1) + '%';
    }

    // ==========================================================================
    // TAB MANAGEMENT
    // ==========================================================================
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.getAttribute('data-tab');
            
            tabs.forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            tabContents.forEach(content => content.classList.remove('active'));
            
            tab.classList.add('active');
            tab.setAttribute('aria-selected', 'true');
            document.getElementById(targetTab).classList.add('active');
            
            // Fetch updated data for the newly opened tab
            if (targetTab === 'gate-flow') {
                fetchGateData();
            } else if (targetTab === 'parking-allocation') {
                fetchParkingData();
            }
        });
    });

    subTabs.forEach(subTab => {
        subTab.addEventListener('click', () => {
            const targetPanel = subTab.getAttribute('data-panel-sub');
            
            subTabs.forEach(st => st.classList.remove('active'));
            subContents.forEach(sc => sc.classList.remove('active'));
            
            subTab.classList.add('active');
            document.getElementById(targetPanel).classList.add('active');
        });
    });

    // ==========================================================================
    // BACKEND API - GATE AND CROWD FLOW MODULE
    // ==========================================================================

    function fetchGateData() {
        const tableBody = document.querySelector('#gateFlowTable tbody');
        
        fetch('/api/gates')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    renderGateTable(data.gates);
                    calculateGateKPIs(data.gates);
                } else {
                    tableBody.innerHTML = `<tr><td colspan="7" class="loading-cell text-error">Error loading gate feeds: ${data.error}</td></tr>`;
                }
            })
            .catch(err => {
                tableBody.innerHTML = `<tr><td colspan="7" class="loading-cell text-error">Error connecting to server.</td></tr>`;
            });
    }

    function renderGateTable(gates) {
        const tableBody = document.querySelector('#gateFlowTable tbody');
        tableBody.innerHTML = '';
        
        if (gates.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="loading-cell">No gate sensors active.</td></tr>';
            return;
        }
        
        gates.forEach(gate => {
            const tr = document.createElement('tr');
            
            // Build Status pill
            const statusClass = gate.status.toLowerCase().replace(' ', '-');
            const pctText = formatPercentage(gate.crowd_percentage);
            
            tr.innerHTML = `
                <td><strong>${escapeHTML(gate.gate_id)}</strong></td>
                <td>${gate.current_crowd_count}</td>
                <td>${gate.gate_capacity}</td>
                <td>${gate.time_to_kickoff_minutes} mins</td>
                <td>${pctText}</td>
                <td><span class="status-pill ${statusClass}">${gate.status}</span></td>
                <td>${escapeHTML(gate.recommendation)}</td>
            `;
            tableBody.appendChild(tr);
        });
    }

    function calculateGateKPIs(gates) {
        document.getElementById('stat-total-gates').textContent = gates.length;
        
        const nearCapacity = gates.filter(g => g.status === 'Near Capacity').length;
        document.getElementById('stat-near-capacity').textContent = nearCapacity;
        
        const critical = gates.filter(g => g.status === 'Critical').length;
        document.getElementById('stat-critical-gates').textContent = critical;
        
        if (gates.length > 0) {
            const sumPct = gates.reduce((acc, g) => acc + g.crowd_percentage, 0);
            const avg = sumPct / gates.length;
            document.getElementById('stat-avg-occupancy').textContent = formatPercentage(avg);
        } else {
            document.getElementById('stat-avg-occupancy').textContent = '0%';
        }
    }

    addGateForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = {
            gate_id: document.getElementById('gate_id').value,
            gate_capacity: parseInt(document.getElementById('gate_capacity').value),
            current_crowd_count: parseInt(document.getElementById('current_crowd_count').value),
            time_to_kickoff_minutes: parseInt(document.getElementById('time_to_kickoff_minutes').value)
        };
        
        // Simple client-side check
        if (!formData.gate_id.trim() || isNaN(formData.gate_capacity) || isNaN(formData.current_crowd_count) || isNaN(formData.time_to_kickoff_minutes)) {
            showAlert('Please fill out all fields with valid numbers.', 'error');
            return;
        }

        fetch('/api/gates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showAlert('Gate sensor stream added successfully!');
                addGateForm.reset();
                renderGateTable(data.gates);
                calculateGateKPIs(data.gates);
            } else {
                showAlert(data.error, 'error');
            }
        })
        .catch(err => {
            showAlert('Server request failed. Please try again.', 'error');
        });
    });

    // ==========================================================================
    // BACKEND API - PARKING & TRANSPORT ALLOCATOR MODULE
    // ==========================================================================

    function fetchParkingData() {
        const batchTableBody = document.querySelector('#batchAllocationsTable tbody');
        const lotTableBody = document.querySelector('#lotStatusTable tbody');
        
        fetch('/api/parking')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    renderParkingTables(data.allocations, data.lots);
                    calculateParkingKPIs(data.allocations, data.lots, data.recommendation);
                } else {
                    const errMsg = `<tr><td colspan="7" class="loading-cell text-error">Error: ${data.error}</td></tr>`;
                    batchTableBody.innerHTML = errMsg;
                    lotTableBody.innerHTML = errMsg;
                }
            })
            .catch(err => {
                const errMsg = '<tr><td colspan="7" class="loading-cell text-error">Server communication error.</td></tr>';
                batchTableBody.innerHTML = errMsg;
                lotTableBody.innerHTML = errMsg;
            });
    }

    function renderParkingTables(allocations, lots) {
        const batchTableBody = document.querySelector('#batchAllocationsTable tbody');
        const lotTableBody = document.querySelector('#lotStatusTable tbody');
        
        // 1. Render Batches Allocations Table
        batchTableBody.innerHTML = '';
        if (allocations.length === 0) {
            batchTableBody.innerHTML = '<tr><td colspan="7" class="loading-cell">No vehicle batches registered.</td></tr>';
        } else {
            allocations.forEach(alloc => {
                const tr = document.createElement('tr');
                const alertClass = alloc.alert === 'None' ? 'alert-none' : 'alert-warning';
                
                // Capitalize vehicle type for visual quality
                const vehType = alloc.vehicle_type.charAt(0).toUpperCase() + alloc.vehicle_type.slice(1);
                
                // Add tag flag for Bus
                const vehicleBadge = alloc.vehicle_type === 'bus' ? `<span class="badge vertical-badge" style="font-size:0.65rem;">BUS REQ</span>` : '';
                
                tr.innerHTML = `
                    <td><strong>${escapeHTML(alloc.batch_id)}</strong></td>
                    <td>${vehType} ${vehicleBadge}</td>
                    <td>${alloc.count}</td>
                    <td>${escapeHTML(alloc.expected_arrival_time)}</td>
                    <td><span style="font-weight: 500;">${escapeHTML(alloc.assigned_lot)}</span></td>
                    <td>${alloc.assigned_lot !== 'Unassigned' ? formatPercentage(alloc.fill_percentage_after) : '-'}</td>
                    <td class="${alertClass}">${escapeHTML(alloc.alert)}</td>
                `;
                batchTableBody.appendChild(tr);
            });
        }
        
        // 2. Render Lots Capacities Table
        lotTableBody.innerHTML = '';
        if (lots.length === 0) {
            lotTableBody.innerHTML = '<tr><td colspan="6" class="loading-cell">No lots registered.</td></tr>';
        } else {
            lots.forEach(lot => {
                const tr = document.createElement('tr');
                const fillPct = lot.current_occupancy / lot.lot_capacity;
                const freeSpaces = lot.lot_capacity - lot.current_occupancy;
                
                tr.innerHTML = `
                    <td><strong>${escapeHTML(lot.lot_id)}</strong></td>
                    <td>${lot.lot_capacity}</td>
                    <td>${lot.current_occupancy}</td>
                    <td>${freeSpaces}</td>
                    <td>${formatPercentage(fillPct)}</td>
                    <td>${lot.is_overflow ? '<span class="status-pill near-capacity">Overflow Reserve</span>' : '<span class="status-pill normal">Main Lot</span>'}</td>
                `;
                lotTableBody.appendChild(tr);
            });
        }
    }

    function calculateParkingKPIs(allocations, lots, recommendation) {
        document.getElementById('stat-total-lots').textContent = lots.length;
        document.getElementById('stat-total-batches').textContent = allocations.length;
        
        // Global parking spaces utilized
        const totalCap = lots.reduce((acc, l) => acc + l.lot_capacity, 0);
        const totalOcc = lots.reduce((acc, l) => acc + l.current_occupancy, 0);
        
        document.getElementById('stat-global-spaces').textContent = `${totalOcc} / ${totalCap}`;
        
        const occupancySummaryCard = document.getElementById('card-occupancy-summary');
        if (totalCap > 0 && (totalOcc / totalCap) > 0.85) {
            occupancySummaryCard.className = "metric-card critical";
        } else if (totalCap > 0 && (totalOcc / totalCap) > 0.70) {
            occupancySummaryCard.className = "metric-card warning";
        } else {
            occupancySummaryCard.className = "metric-card info";
        }
        
        // Overflow recommendation
        const alertCard = document.getElementById('card-overflow-status');
        const alertText = document.getElementById('stat-overflow-alert');
        
        alertText.textContent = recommendation || 'No action needed';
        
        if (recommendation && recommendation.toLowerCase().includes('open overflow')) {
            alertCard.className = 'metric-card alert-state active';
        } else {
            alertCard.className = 'metric-card alert-state';
        }
    }

    addBatchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = {
            batch_id: document.getElementById('batch_id').value,
            vehicle_type: document.getElementById('vehicle_type').value,
            count: parseInt(document.getElementById('vehicle_count').value),
            expected_arrival_time: document.getElementById('expected_arrival_time').value
        };
        
        if (!formData.batch_id.trim() || isNaN(formData.count) || !formData.expected_arrival_time) {
            showAlert('Please fill out all batch fields correctly.', 'error');
            return;
        }

        fetch('/api/parking/batches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showAlert('Vehicle batch allocated successfully!');
                addBatchForm.reset();
                renderParkingTables(data.allocations, data.lots);
                calculateParkingKPIs(data.allocations, data.lots, data.recommendation);
            } else {
                showAlert(data.error, 'error');
            }
        })
        .catch(err => {
            showAlert('Server request failed.', 'error');
        });
    });

    addLotForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = {
            lot_id: document.getElementById('lot_id').value,
            lot_capacity: parseInt(document.getElementById('lot_capacity').value),
            current_occupancy: parseInt(document.getElementById('current_occupancy').value),
            is_overflow: document.getElementById('is_overflow').checked
        };
        
        if (!formData.lot_id.trim() || isNaN(formData.lot_capacity) || isNaN(formData.current_occupancy)) {
            showAlert('Please fill out all lot fields correctly.', 'error');
            return;
        }

        fetch('/api/parking/lots', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showAlert('Parking lot added successfully!');
                addLotForm.reset();
                renderParkingTables(data.allocations, data.lots);
                calculateParkingKPIs(data.allocations, data.lots, data.recommendation);
            } else {
                showAlert(data.error, 'error');
            }
        })
        .catch(err => {
            showAlert('Server request failed.', 'error');
        });
    });

    // ==========================================================================
    // DATA RESET BUTTON
    // ==========================================================================

    resetBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all mock sensor data back to default values?')) {
            fetch('/api/reset', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        showAlert('Data successfully reset to defaults.');
                        // Refresh whichever tab is active
                        const activeTab = document.querySelector('.tab-link.active').getAttribute('data-tab');
                        if (activeTab === 'gate-flow') {
                            fetchGateData();
                        } else {
                            fetchParkingData();
                        }
                    } else {
                        showAlert(data.error, 'error');
                    }
                })
                .catch(err => {
                    showAlert('Reset failed due to communication error.', 'error');
                });
        }
    });

    // Helper to escape HTML and prevent XSS
    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }

    // Initial load on launch
    fetchGateData();
});
