if (window.location.pathname.startsWith('/kds/')) {
    
    window.logoutKDS = async function() {
        try {
            await fetch('/api/logout', { method: 'POST' });
            window.location.href = '/';
        } catch(e) {
            console.error("Error al cerrar sesion", e);
            window.location.href = '/';
        }
    }
    
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
        
        const mesaDiv = document.createElement('div');
        mesaDiv.style.cssText = 'font-size: 24px; font-weight: 900; margin-bottom: 5px;';
        mesaDiv.textContent = 'MESA ' + mesa;
        
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = 'font-size: 18px; font-weight: 500;';
        msgDiv.textContent = mensaje;
        
        const subDiv = document.createElement('div');
        subDiv.style.cssText = 'font-size: 12px; margin-top: 5px; opacity: 0.8;';
        subDiv.textContent = 'Mensaje del Mesero';

        toast.appendChild(mesaDiv);
        toast.appendChild(msgDiv);
        toast.appendChild(subDiv);

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

    let isFetching = false;
    async function loadOrders() {
        if (isFetching) return;
        isFetching = true;
        
        try {
            const res = await fetch(`/api/kds-orders/${DESTINO}`);
            if (!res.ok) {
                 throw new Error(`Error HTTP: ${res.status} al cargar órdenes`);
            }
            
            const orders = await res.json();
            renderTickets(orders);
        } catch (e) {
            console.error("Error cargando órdenes:", e);
        } finally {
            isFetching = false;
        }
    }
    
    // Consulta periódica de respaldo (cada 2 minutos)
    setInterval(() => {
        if (socket.connected) {
            loadOrders();
        }
    }, 120000);

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
            
            const minutesElapsed = (new Date() - new Date(group.timestamp)) / 60000;
            const timeStyle = minutesElapsed > 15 ? 'color: #ff4444;' : ''; 
            
            const header = document.createElement('div');
            header.className = 'card-header';
            
            const mesaBadge = document.createElement('div');
            mesaBadge.className = 'mesa-badge';
            mesaBadge.textContent = 'Mesa ' + group.numero_mesa;
            
            const timerBadge = document.createElement('div');
            timerBadge.className = 'timer-badge';
            timerBadge.style = timeStyle;
            timerBadge.textContent = formatTime(group.timestamp);
            
            header.appendChild(mesaBadge);
            header.appendChild(timerBadge);
            card.appendChild(header);
            
            const itemsContainer = document.createElement('div');
            itemsContainer.className = 'card-items';
            
            group.items.forEach(item => {
                const row = document.createElement('div');
                row.className = 'item-row';
                
                const qty = document.createElement('div');
                qty.className = 'qty-box';
                qty.textContent = item.cantidad;
                
                const info = document.createElement('div');
                info.className = 'item-info';
                
                const name = document.createElement('div');
                name.className = 'item-name';
                name.textContent = item.nombre;
                info.appendChild(name);
                
                if (item.nombre_cerveza) {
                    const sub = document.createElement('div');
                    sub.className = 'item-sub';
                    sub.style.cssText = 'color: #00d26a; font-size: 0.9em; font-weight: bold;';
                    sub.textContent = '└ Cerveza: ' + item.nombre_cerveza;
                    info.appendChild(sub);
                }
                
                if (item.notas) {
                    const note = document.createElement('div');
                    note.className = 'item-note';
                    note.textContent = '📝 ' + item.notas;
                    info.appendChild(note);
                }
                
                row.appendChild(qty);
                row.appendChild(info);
                itemsContainer.appendChild(row);
            });
            
            card.appendChild(itemsContainer);

            const actions = document.createElement('div');
            actions.className = 'card-actions';
            const btn = document.createElement('button');
            btn.className = 'btn-complete';
            btn.textContent = '✓ LISTO';
            btn.addEventListener('click', (e) => window.markReady(group.numero_mesa, e));
            
            actions.appendChild(btn);
            card.appendChild(actions);

            container.appendChild(card);
        });
    }

    function formatTime(isoString) {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    window.markReady = async function(mesaKey, e) {
        const btn = e.target.closest('button');
        const originalText = btn.innerHTML;
        
        btn.innerHTML = 'Enviando...';
        btn.disabled = true;
        btn.style.backgroundColor = '#555';

        try {
            const response = await fetch('/api/kds-complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
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
            btn.textContent = originalText;
            btn.style.backgroundColor = ''; 
        }
    }
}