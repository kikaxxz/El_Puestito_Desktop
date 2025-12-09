let currentPin = "";

function addPin(num) {
    if (currentPin.length < 4) {
        currentPin += num;
        updatePinDisplay();
    }
}

function clearPin() {
    currentPin = "";
    updatePinDisplay();
}

function updatePinDisplay() {
    const display = document.getElementById('pinDisplay');
    if(display) display.innerText = "*".repeat(currentPin.length).padEnd(4, '-');
}

async function submitPin() {
    if (currentPin.length !== 4) return;
    
    try {
        const res = await fetch('/api/validar-pin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({pin: currentPin})
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            window.location.href = data.redirect;
        } else {
            alert("PIN Incorrecto");
            clearPin();
        }
    } catch (e) {
        alert("Error de conexión");
    }
}

if (window.location.pathname.startsWith('/kds/')) {
    
    const socket = io();
    const alertOverlay = document.getElementById('disconnect-alert');

    socket.on('connect', () => {
        console.log("🟢 Conectado al WebSocket");
        if(alertOverlay) alertOverlay.style.display = 'none';
        loadOrders();
    });

    socket.on('disconnect', () => {
        console.warn("🔴 Desconectado del WebSocket");
        if(alertOverlay) alertOverlay.style.display = 'flex';
    });

    socket.on('kds_update', (data) => {
        if (data.destino === 'all' || data.destino === DESTINO) {
            console.log("🔔 Actualización recibida");
            loadOrders();
        }
    });

    async function loadOrders() {
        try {
            const res = await fetch(`/api/kds-orders/${DESTINO}`);
            if (!res.ok) throw new Error("Error HTTP al cargar órdenes");
            
            const orders = await res.json();
            renderTickets(orders);
        } catch (e) {
            console.error("Error cargando órdenes:", e);
        }
    }

    function renderTickets(orders) {
        const container = document.getElementById('orders-container');
        container.innerHTML = '';

        if (orders.length === 0) {
            container.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; margin-top: 100px; opacity: 0.5;">
                    <div style="font-size: 60px; margin-bottom: 20px;">☕</div>
                    <h2>Todo tranquilo por aquí</h2>
                    <p>Esperando nuevas comandas...</p>
                </div>`;
            return;
        }

        orders.forEach(group => {
            const card = document.createElement('div');
            card.className = 'order-card';
            
            const itemsHtml = group.items.map(item => `
                <div class="item-row">
                    <div class="qty-box">${item.cantidad}</div>
                    <div class="item-info">
                        <div class="item-name">${item.nombre}</div>
                        ${item.notas ? `<div class="item-note">📝 ${item.notas}</div>` : ''}
                    </div>
                </div>
            `).join('');

            const minutesElapsed = (new Date() - new Date(group.timestamp)) / 60000;
            const timeClass = minutesElapsed > 15 ? 'color: #ff4444;' : ''; 

            card.innerHTML = `
                <div class="card-header">
                    <div class="mesa-badge">Mesa ${group.numero_mesa}</div>
                    <div class="timer-badge" style="${timeClass}">${formatTime(group.timestamp)}</div>
                </div>
                <div class="card-items">
                    ${itemsHtml}
                </div>
                <div class="card-actions">
                    <button class="btn-complete" onclick="markReady('${group.numero_mesa}')">
                        ✓ LISTO
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    }

    function formatTime(isoString) {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    window.markReady = async function(mesaKey) {
        const btn = event.target.closest('button');
        const originalText = btn.innerHTML;
        
        btn.innerHTML = 'Enviando...';
        btn.disabled = true;
        btn.style.backgroundColor = '#555';

        try {
            await fetch('/api/kds-complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': API_KEY
                },
                body: JSON.stringify({ mesa_key: mesaKey, destino: DESTINO })
            });
        } catch (e) {
            alert("Error de conexión al completar orden");
            btn.disabled = false;
            btn.innerHTML = originalText;
            btn.style.backgroundColor = ''; 
        }
    }
}