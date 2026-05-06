if (window.location.pathname.startsWith('/kds/')) {
    
    const socket = io();
    const alertOverlay = document.getElementById('disconnect-alert');

    socket.on('connect', () => {
        console.log("Conectado al WebSocket");
        if(alertOverlay) alertOverlay.style.display = 'none';
        loadOrders();
    });

    socket.on('connect_error', (error) => {
        console.error("Error de conexión al WebSocket:", error);
        if(alertOverlay) {
            alertOverlay.style.display = 'flex';
            alertOverlay.querySelector('.alert-msg').textContent = "Error de conexión al servidor.";
        }
    });

    socket.on('disconnect', () => {
        console.warn("Desconectado del WebSocket");
        if(alertOverlay) {
            alertOverlay.style.display = 'flex';
            alertOverlay.querySelector('.alert-msg').textContent = "Intentando reconectar con el servidor...";
        }
    });

    socket.on('kds_update', (data) => {
        if (data.destino === 'all' || data.destino === DESTINO) {
            console.log("Actualización recibida");
            loadOrders();
        }
    });

    socket.on('kds_message_alert', (data) => {
        if (data.destino === 'all' || data.destino === DESTINO) {
            showToastNotification(data.mesa_key, data.mensaje);
        }
    });

    // --- ACTUALIZACIÓN DINÁMICA DE TIEMPOS ---
    setInterval(updateAllTimers, 60000); // Ejecutar cada 60 segundos

    function updateAllTimers() {
        document.querySelectorAll('.order-card').forEach(card => {
            const ts = card.dataset.timestamp;
            if (!ts) return;
            
            const minutesElapsed = (new Date() - new Date(ts)) / 60000;
            const timerBadge = card.querySelector('.timer-badge');
            
            if (minutesElapsed > 15) {
                timerBadge.style.color = '#ff4444';
                timerBadge.style.fontWeight = 'bold';
                card.style.boxShadow = '0 4px 20px rgba(255, 68, 68, 0.15)'; // Resplandor rojo de urgencia
            } else if (minutesElapsed > 10) {
                timerBadge.style.color = '#ffeb3b'; // Advertencia amarilla
            }
        });
    }

    function showToastNotification(mesa, mensaje) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #ff9800;
            color: white;
            padding: 20px 40px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            z-index: 10000;
            text-align: center;
            font-family: sans-serif;
            border: 2px solid white;
            min-width: 300px;
            animation: slideDown 0.5s ease-out;
        `;
        
        toast.innerHTML = `
            <div style="font-size: 24px; font-weight: 900; margin-bottom: 5px;">MESA ${mesa}</div>
            <div style="font-size: 18px; font-weight: 500;">${mensaje}</div>
            <div style="font-size: 12px; margin-top: 5px; opacity: 0.8;">Mensaje del Mesero</div>
        `;

        try {
            const audio = new Audio('/static/notification.mp3');
            audio.play().catch(e => console.log("Audio bloqueado por el navegador"));
        } catch(e) {
            console.error("Error al reproducir audio:", e);
        }

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s';
            setTimeout(() => toast.remove(), 500);
        }, 10000);
    }
    
    const styleSheet = document.createElement("style");
    styleSheet.innerText = `
        @keyframes slideDown {
            from { top: -100px; opacity: 0; }
            to { top: 20px; opacity: 1; }
        }
    `;
    document.head.appendChild(styleSheet);

    async function loadOrders() {
        try {
            const res = await fetch(`/api/kds-orders/${DESTINO}`);
            if (!res.ok) {
                 throw new Error(`Error HTTP: ${res.status} al cargar órdenes`);
            }
            
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
                        ${item.nombre_cerveza ? `<div class="item-sub" style="color: #00d26a; font-size: 0.9em; font-weight: bold;">└ Cerveza: ${item.nombre_cerveza}</div>` : ''}
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
            const response = await fetch('/api/kds-complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': typeof API_KEY !== 'undefined' ? API_KEY : '' 
                },
                body: JSON.stringify({ mesa_key: mesaKey, destino: DESTINO })
            });

            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({}));
                 throw new Error(errorData.message || "Error al completar la orden");
            }
        } catch (e) {
            console.error("Error de conexión al completar orden:", e);
            btn.disabled = false;
            btn.innerHTML = originalText;
            btn.style.backgroundColor = ''; 
        }
    }
}