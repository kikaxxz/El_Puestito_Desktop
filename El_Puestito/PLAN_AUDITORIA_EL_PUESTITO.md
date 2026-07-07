# Plan maestro de corrección — El Puestito

## Contexto

Proyecto de escritorio ubicado en:

`C:\Users\KikaXxz\Documents\MiProyectoPOS\El_Puestito`

Tecnologías principales:

- PyQt6 para la aplicación de escritorio.
- Flask y Flask-SocketIO como servidor embebido.
- SQLite como persistencia local.
- Socket.IO para comunicación en tiempo real.
- Firebase Admin para notificaciones.
- PyInstaller para distribución.

## Instrucción para Codex

Implementa este plan una fase por vez. Antes de empezar, el usuario debe indicar expresamente qué fase autoriza. No avances a otra fase hasta entregar los resultados de la fase actual y recibir una nueva aprobación.

Ejemplo de autorización:

> Implementa únicamente la Fase 1 del archivo `PLAN_AUDITORIA_EL_PUESTITO.md` y espera mi aprobación antes de continuar.

## Reglas obligatorias

1. Inspecciona el estado actual del repositorio antes de editar. No dependas ciegamente de números de línea ni de hallazgos anteriores.
2. Implementa solamente la fase solicitada.
3. No avances a la siguiente fase sin aprobación explícita.
4. Conserva los contratos actuales de la aplicación móvil y del ESP32, salvo que la fase autorice una migración compatible.
5. No modifiques datos operativos reales de `%APPDATA%\ElPuestito`.
6. Usa bases de datos temporales para pruebas.
7. No incluyas, muestres ni registres secretos.
8. Antes de cambiar el esquema de SQLite, crea una migración segura y explica el respaldo necesario.
9. No uses `QThread.terminate()` como mecanismo de cierre.
10. Conserva los cambios ajenos que ya existan en el repositorio.
11. Evita refactorizaciones no relacionadas con la fase activa.
12. Al terminar cada fase entrega:

    - Archivos modificados.
    - Cambios realizados.
    - Pruebas ejecutadas y sus resultados.
    - Riesgos o tareas pendientes.
    - Confirmación de que no se trabajó en fases posteriores.

---

# Fase 1 — Contención de seguridad

## Objetivo

Cerrar las vulnerabilidades explotables sin cambiar todavía la lógica de órdenes, inventario o facturación.

## Archivos principales

- `server/server_routes.py`
- `server/server_worker.py`
- `server/templates/kds_view.html`
- `server/templates/reportes_dashboard.html`
- `server/static/kds_logic.js`
- `views/attendance_page.py`
- `app.py`
- `Assets/config.json`
- `src/firebase_service.py`
- `El Puestito.spec`

## Tareas

### 1. Restringir la entrega de archivos

- Modifica `/images/<filename>` para que sirva únicamente imágenes.
- Permite solo extensiones explícitas: `.png`, `.jpg`, `.jpeg`, `.webp` e `.ico`.
- Impide el acceso a:

  - `config.json`
  - Archivos de asistencia.
  - Archivos de órdenes.
  - Cualquier archivo JSON.
  - Cualquier archivo fuera de la carpeta de imágenes autorizada.

- Preferiblemente sirve imágenes desde una carpeta exclusiva, no desde la raíz completa de `Assets`.

### 2. Eliminar la API key del navegador KDS

- Elimina la API key del contexto de `kds_view.html`.
- Elimina su uso en `kds_logic.js`.
- No reemplaces la API key por otro secreto visible en HTML o JavaScript.

### 3. Proteger el KDS mediante sesión

Protege mediante sesión:

- `/kds/<destino>`
- `/api/kds-orders/<destino>`
- `/api/kds-complete`

La autorización debe verificar el destino:

- Una sesión de cocina solo puede consultar y completar cocina.
- Una sesión de barra solo puede consultar y completar barra.
- Un destino no válido debe responder `400` o `403`, no éxito.

### 4. Autenticar Socket.IO

- Añade autenticación durante el evento de conexión.
- Rechaza conexiones sin una sesión válida.
- No confíes únicamente en el origen del navegador.
- Crea salas separadas:

  - `cocina`
  - `barra`
  - `reportes`

- Emite cada evento únicamente a la sala correspondiente.
- No transmitas el estado completo de caja a clientes que no lo necesitan.

### 5. Restringir CORS

- Elimina `cors_allowed_origins="*"`.
- Permite same-origin por defecto.
- Si se requieren orígenes adicionales, deben venir de una configuración explícita y validada.

### 6. Corregir XSS

En `server/static/kds_logic.js`:

- No insertes nombres, notas, mesas o mensajes recibidos mediante `innerHTML`.
- Usa `textContent` y creación segura de elementos DOM.
- No construyas atributos `onclick` con datos recibidos.
- Registra listeners con `addEventListener`.
- Trata como no confiables:

  - `numero_mesa`
  - `nombre`
  - `nombre_cerveza`
  - `notas`
  - `mensaje`

### 7. Proteger el inicio de sesión por PIN

- Añade rate limiting o bloqueo temporal por IP/sesión.
- Usa comparación segura.
- No registres PINes ni mapas de PINes en logs.
- Implementa una ruta de logout que elimine la sesión.
- Cambia el botón “Cerrar sesión” para usar esa ruta.
- Configura expiración razonable de sesión.
- Usa una `secret_key` persistente y segura fuera del repositorio.

### 8. Proteger operaciones locales destructivas

- Exige autenticación administrativa antes de borrar el historial de asistencia.
- Mantén la confirmación visual existente.
- No borres automáticamente datos como parte de una prueba.

### 9. Reducir exposición de red

- Cambia la regla de firewall para el perfil privado.
- No uses `profile=any`.
- Documenta la subred o interfaz esperada.
- No intentes implementar certificados inseguros o autofirmados silenciosamente.
- Si TLS no se implementa en esta fase, deja documentado que la API key y las sesiones no deben circular por redes no confiables.

### 10. Retirar credenciales Firebase distribuidas

- Asegura que las credenciales Firebase no se incorporen a PyInstaller.
- Inspecciona y limpia artefactos generados que contengan la cuenta de servicio.
- No inventes, generes ni rotes credenciales automáticamente.
- Informa al usuario que debe realizar manualmente:

  - Revocación de la cuenta de servicio distribuida.
  - Creación de una credencial nueva.
  - Rotación de la API key actual.

## Criterios de aceptación

- `/images/config.json` responde `403` o `404`.
- Un usuario sin sesión no puede consultar órdenes KDS.
- Cocina no puede consultar ni completar órdenes de barra.
- Barra no puede consultar ni completar órdenes de cocina.
- La API key no aparece en el HTML ni en JavaScript del KDS.
- Una conexión Socket.IO anónima es rechazada.
- Cada cliente recibe solamente eventos de su sala.
- Una nota que contenga `<script>` se muestra como texto y no se ejecuta.
- Cerrar sesión invalida inmediatamente el acceso.
- El historial de asistencia no puede borrarse sin autorización administrativa.
- Ninguna credencial Firebase aparece en el artefacto reconstruido.

---

# Fase 2 — Integridad de órdenes, inventario y SQLite

## Objetivo

Garantizar que una orden solo se confirme después de guardarse correctamente y evitar corrupción de inventario, cuentas o históricos.

## Archivos principales

- `src/data_model.py`
- `src/app_controller.py`
- `server/server_routes.py`
- `server/server_worker.py`
- `views/admin_tabs/menu_tab.py`
- `views/admin_tabs/employees_tab.py`

## Tareas

### 1. Corregir el contrato de persistencia

Rediseña `DataManager.execute()`:

- No ocultes errores de SQLite.
- Devuelve `lastrowid` para inserciones.
- Devuelve `rowcount` para actualizaciones y eliminaciones.
- Propaga excepciones tipadas o devuelve un resultado estructurado inequívoco.
- No permitas que la interfaz informe éxito cuando no se modificó ninguna fila.

### 2. Hacer sincrónica la confirmación de órdenes

Modifica `/nueva-orden` para ejecutar este orden:

1. Validar la solicitud.
2. Iniciar transacción.
3. Validar menú y stock desde la base de datos.
4. Insertar orden y detalles.
5. Descontar inventario.
6. Confirmar la transacción.
7. Emitir señales/eventos.
8. Responder al cliente.

No respondas `200` antes del commit.

### 3. Implementar idempotencia real

- Exige un `order_id` válido, no vacío y con longitud limitada.
- Mantén una restricción única en la base de datos.
- Si el UUID ya existe, responde como duplicado aceptado.
- Evita que dos solicitudes simultáneas inserten el mismo UUID.

### 4. No confiar en datos comerciales del cliente

Obtén desde la base de datos:

- Nombre del producto.
- Precio aplicable.
- Destino.
- Disponibilidad.

Antes de decidir el precio, inspecciona las reglas actuales de precio normal, precio de michelada y cerveza seleccionada. Conserva la regla comercial existente, pero aplica el valor autoritativo del servidor.

### 5. Validar cantidades y estructura

- La cantidad debe ser un entero.
- Debe ser mayor que cero.
- Debe respetar un límite razonable.
- La orden debe contener al menos un artículo.
- Cada artículo debe tener un identificador válido.
- Limita longitudes de notas, mesa y nombres de subcuenta.
- Rechaza valores `NaN`, infinitos o tipos inesperados.

### 6. Hacer atómico el inventario

- Usa una sola transacción para validación y descuento.
- Actualiza inventario con una condición equivalente a `cantidad >= solicitada`.
- Verifica el número de filas afectadas.
- Haz rollback completo si cualquier artículo carece de stock.
- Evita que dos órdenes simultáneas produzcan stock negativo.

### 7. Corregir división de cuentas

En `split_order`:

- Verifica que cada `id_detalle` pertenece a la orden origen.
- Verifica que la orden origen está activa.
- Valida cantidades positivas.
- Impide mover más unidades que las existentes.
- Valida la cuenta destino.
- Evita claves de cuenta ambiguas o duplicadas.
- Si un elemento es inválido, falla toda la operación.

### 8. Corregir eliminación de artículos

En `remove_items_from_order`:

- Aplica las mismas validaciones de pertenencia y cantidad.
- No aceptes cantidades negativas.
- Restaura inventario únicamente por la cantidad efectivamente eliminada.
- Falla completamente ante datos inconsistentes.

### 9. Activar integridad referencial

- Ejecuta `PRAGMA foreign_keys=ON` en cada conexión.
- Crea una migración segura para las relaciones existentes.
- Define políticas explícitas `ON UPDATE` y `ON DELETE`.
- Evita que editar el ID de un empleado deje asistencia huérfana.
- Evita que eliminar menú o inventario destruya información histórica.

### 10. Preservar reportes históricos

- Usa `nombre_congelado` y `precio_unitario_congelado` para reportes históricos.
- No dependas de que el producto siga existiendo en `menu_items`.
- Verifica que eliminar un producto no cambie ventas pasadas.

### 11. Hacer atómicas operaciones relacionadas

Incluye en una sola transacción:

- Vinculación o reasignación de huellas.
- Eliminación de categorías y productos.
- Limpieza de huellas.
- División de cuentas.
- Operaciones compuestas de inventario.

## Criterios de aceptación

- Una orden fallida nunca devuelve éxito.
- Una orden aceptada existe en SQLite antes de responder.
- Cantidades negativas, cero o no enteras son rechazadas.
- El cliente no puede modificar el precio cobrado.
- Dos órdenes simultáneas no producen stock negativo.
- No se pueden mover artículos de otra mesa.
- No se pueden eliminar más unidades que las existentes.
- Cambiar o eliminar productos no altera reportes históricos.
- Todos los fallos transaccionales hacen rollback.
- Las interfaces distinguen correctamente entre éxito, cero filas modificadas y error.

---

# Fase 3 — Hilos, ciclo de vida y tiempo real

## Objetivo

Eliminar bloqueos de PyQt, cerrar el servidor limpiamente y garantizar sincronización consistente.

## Archivos principales

- `main_window.py`
- `server/server_thread.py`
- `server/server_worker.py`
- `src/app_controller.py`
- `src/printer_service.py`
- `src/firebase_service.py`
- `views/cocina_page.py`
- `views/barra_page.py`
- `views/caja_page.py`
- `server/static/kds_logic.js`

## Tareas

### 1. Reemplazar el cierre actual del servidor

- Mantén una referencia explícita al servidor WSGI o aísla Flask en un proceso controlado.
- Implementa apagado cooperativo.
- Añade un timeout razonable.
- Elimina completamente `QThread.terminate()`.
- Asegura que las conexiones SQLite terminen limpiamente.

### 2. Definir propiedad de hilos

- Documenta qué objetos viven en el hilo principal.
- Documenta qué objetos viven en workers.
- No llames directamente métodos de un `QObject` desde un hilo distinto de su afinidad.
- Usa señales, slots o colas para cruzar hilos.

### 3. Sacar I/O lento del hilo principal

Mueve a workers:

- Impresión de tickets.
- Apertura del cajón.
- Conexión con impresora de red.
- Envío Firebase.
- Escaneo USB.
- Cualquier operación potencialmente bloqueante.

Cada operación debe tener:

- Timeout.
- Resultado por señal.
- Manejo de error visible.
- Reintento controlado cuando sea seguro.

### 4. Eliminar auto-HTTP innecesario

- Evita que PyQt haga solicitudes HTTP al Flask que vive en el mismo proceso solo para emitir eventos.
- Sustituye este flujo por un puente interno de eventos seguro entre el controlador y el gateway Socket.IO.
- Mantén HTTP únicamente para clientes externos.

### 5. Centralizar eventos

Define nombres únicos, por ejemplo:

- `order_created`
- `order_updated`
- `order_completed`
- `menu_updated`
- `config_updated`
- `attendance_updated`

No mantengas simultáneamente nombres ambiguos como `mesas_update` y `mesas_actualizadas`.

### 6. Emitir después del commit

- No emitas eventos antes de que la operación de base de datos termine.
- Incluye suficiente información para que el cliente sepa qué debe refrescar.
- Si se usa un evento como invalidación, el cliente debe volver a consultar el estado autoritativo.

### 7. Mejorar reconexión KDS

- Resincroniza al conectar.
- Resincroniza después de reconectar.
- Mantén el overlay mientras no haya conexión.
- Añade una consulta periódica de respaldo con intervalo razonable.
- Evita solicitudes simultáneas duplicadas.
- Tras completar una orden, deshabilita el botón solamente mientras se recibe confirmación.

### 8. Eliminar duplicación PyQt

- Elimina conexiones duplicadas de señales.
- Elimina definiciones duplicadas de `_marcar_listo`.
- Extrae una clase o componente común para cocina y barra.
- Asegura que cada evento provoque una sola consulta y un solo render.

## Criterios de aceptación

- La aplicación cierra sin `terminate()`.
- No quedan procesos ni el puerto 5000 abiertos.
- Una impresora desconectada no congela la interfaz.
- Una demora de Firebase no congela la interfaz.
- El KDS refleja altas, cambios y cierres sin depender de otro evento posterior.
- Una reconexión recupera el estado completo.
- Cada señal provoca una única actualización de pantalla.
- Los errores de workers llegan a la interfaz de forma controlada.

---

# Fase 4 — Correcciones funcionales

## Objetivo

Corregir comportamientos visibles sin hacer todavía una reorganización arquitectónica extensa.

## Archivos principales

- `server/templates/reportes_dashboard.html`
- `server/server_routes.py`
- `views/admin_tabs/reports_tab.py`
- `views/admin_tabs/printer_tab.py`
- `src/printer_service.py`
- `views/role_selection_page.py`
- `views/admin_tabs/settings_tab.py`
- `views/admin_tabs/payroll_tab.py`
- `src/firebase_service.py`
- `src/app_controller.py`

## Tareas

### 1. Corregir reportes web

- “Ventas de Hoy” debe usar `resumen_hoy.total`.
- Lee `start` y `end` desde la URL.
- Inicializa los campos de fecha con esos valores.
- Aplica el rango enviado desde PyQt.
- Valida que inicio no sea posterior a fin.
- Responde `400` ante fechas inválidas.
- No devuelvas detalles internos de excepciones al cliente.

### 2. Unificar configuración de impresora

- Elige una ubicación única para:

  - Interfaz.
  - Dirección IP.
  - VID.
  - PID.
  - Encabezado.
  - Pie.
  - Propinas.

- Migra valores antiguos de forma compatible.
- Asegura que los cambios tengan efecto inmediato.
- Invalida la conexión actual cuando cambie la configuración.
- Reconecta en la siguiente operación o mediante una prueba explícita.

### 3. Corregir datos de impresión

- Incluye `mesa_key` en proformas y tickets.
- Verifica que se imprima correctamente en cuentas agrupadas y subcuentas.
- No cierres la cuenta silenciosamente si la política exige impresión obligatoria; documenta la decisión.

### 4. Corregir PINes

- Recarga los PINes después de guardar.
- Exige exactamente cuatro dígitos.
- Impide PINes duplicados.
- Impide valores vacíos.
- No registres PINes en logs.
- Muestra un error de validación antes de guardar.

### 5. Corregir nómina

- Mantén una entrada pendiente por empleado.
- No compartas `last_entry_time` entre empleados.
- Maneja múltiples turnos en un mismo día.
- Define y prueba turnos nocturnos.
- Aplica márgenes configurados.
- Detecta entradas o salidas sin pareja.
- No inventes horas ante registros incompletos.
- Mantén trazabilidad del cálculo diario.

### 6. Corregir Firebase

- Define una ruta válida por entorno.
- No incluyas secretos dentro del ejecutable.
- Respeta `recibe_alertas`.
- Usa tokens o temas coherentes con las preferencias.
- Maneja credenciales ausentes sin reintentos repetitivos y ruidosos.

### 7. Eliminar dependencias web innecesarias

- Incluye Chart.js localmente.
- Incluye `notification.mp3`.
- Verifica que el dashboard funcione sin Internet.

### 8. Corregir handler del botón KDS

- No dependas del objeto global `event`.
- Pasa el botón o evento explícitamente al handler.
- Restaura el estado del botón en caso de error.

## Criterios de aceptación

- El total diario coincide con la consulta SQLite.
- Abrir reportes desde una fecha seleccionada muestra ese rango.
- Cambiar USB/Wi-Fi modifica realmente el servicio usado.
- Los tickets muestran la mesa correcta.
- Los PINes cambian sin reiniciar.
- La nómina no mezcla empleados.
- El dashboard funciona sin Internet.
- Las preferencias de notificaciones se respetan.

---

# Fase 5 — Arquitectura y mantenibilidad

## Objetivo

Separar responsabilidades manteniendo compatibilidad funcional.

## Estructura sugerida

```text
src/
  config/
    config_service.py
    schema.py
  database/
    connection.py
    migrations/
    repositories/
      orders.py
      menu.py
      employees.py
      attendance.py
      inventory.py
  services/
    order_service.py
    attendance_service.py
    payroll_service.py
    notification_service.py
    printer_service.py
  realtime/
    events.py
    socket_gateway.py
server/
  app_factory.py
  auth.py
  routes/
    kds.py
    orders.py
    attendance.py
    reports.py
    biometric.py
```

La estructura es orientativa. Adáptala al proyecto actual sin hacer una reescritura total.

## Tareas

1. Divide `data_model.py` en repositorios por dominio.
2. Divide `server_routes.py` por dominio.
3. Crea una capa de servicios para transacciones y reglas de negocio.
4. Haz que PyQt y Flask usen los mismos servicios.
5. Centraliza carga, validación y guardado de configuración.
6. Elimina claves alternativas como `pines` y `pines_acceso`.
7. Usa constantes o enums para eventos y estados.
8. Sustituye manipulación de `sys.path` por paquetes Python normales.
9. Añade `__init__.py` donde corresponda.
10. Versiona las migraciones.
11. Añade índices para:

    - Estado de órdenes.
    - `mesa_key`.
    - `client_uuid`.
    - Destino y estado del detalle.
    - Empleado y fecha de asistencia.
    - Fecha de cierre.

12. Planifica migración monetaria de `REAL` a centavos enteros.
13. Guarda imágenes modificables en AppData, no dentro del paquete.
14. Centraliza logging y evita múltiples inicializaciones implícitas.
15. Elimina imports, parámetros y módulos sin uso.

## Criterios de aceptación

- Las rutas no contienen reglas de negocio complejas.
- PyQt y Flask utilizan los mismos servicios.
- Existe una única fuente de configuración.
- Los módulos pueden probarse sin iniciar la interfaz.
- No cambia el comportamiento externo de las APIs.
- Las migraciones se pueden aplicar y verificar de forma independiente.

---

# Fase 6 — Pruebas, empaquetado y entrega

## Objetivo

Evitar regresiones y generar un paquete reproducible sin datos sensibles.

## Tareas

### 1. Completar dependencias

- Declara todas las dependencias utilizadas.
- Fija versiones verificadas.
- Incluye, según el paquete realmente elegido:

  - `firebase-admin`
  - `pyusb`
  - La distribución correcta de `escpos`
  - `fpdf` o `fpdf2`, pero no ambas simultáneamente

- Verifica instalación en un entorno virtual limpio.

### 2. Crear pruebas de seguridad

Incluye pruebas para:

- Autenticación y autorización de rutas.
- Acceso a archivos.
- Separación cocina/barra.
- Socket.IO anónimo.
- XSS.
- Rate limiting.
- Logout.

### 3. Crear pruebas de órdenes e inventario

Incluye pruebas para:

- Orden válida.
- Orden sin UUID.
- Orden duplicada.
- Precio manipulado.
- Cantidad negativa.
- Cantidad no entera.
- Stock insuficiente.
- Concurrencia de inventario.
- Rollback completo.
- División de cuentas.
- Eliminación de artículos.

### 4. Crear pruebas de negocio

Incluye pruebas para:

- Reportes históricos tras eliminar productos.
- Ventas de hoy.
- Filtros por fecha.
- Nómina por empleado.
- Múltiples turnos.
- Turnos nocturnos.
- Feriados y horas extra.
- Configuración de impresora.
- Recarga de PINes.

### 5. Crear pruebas de integración

- Usa SQLite temporal.
- Usa el cliente de pruebas de Flask.
- Usa el cliente de pruebas de Flask-SocketIO.
- No uses la base real de AppData.
- Prueba reconexión y resincronización.
- Prueba apagado limpio del servidor.

### 6. Validar PyInstaller

- Reconstruye desde cero, sin reutilizar `build` o `dist` antiguos.
- Inspecciona el artefacto final.
- Confirma que no contiene:

  - Credenciales Firebase.
  - API keys reales.
  - Bases de datos operativas.
  - Logs.
  - Historial de asistencia.
  - Órdenes reales.

### 7. Documentar operación

Documenta:

- Instalación limpia.
- Configuración inicial.
- Variables de entorno.
- Respaldo.
- Restauración.
- Actualización de esquema.
- Rotación de credenciales.
- Diagnóstico de impresora.
- Diagnóstico del servidor y WebSocket.

## Criterios de aceptación

- Todas las pruebas pasan.
- La aplicación arranca desde un entorno limpio.
- El paquete funciona sin Internet salvo servicios explícitamente externos.
- El artefacto no contiene secretos ni datos reales.
- El cierre no deja el puerto 5000 ocupado.
- Las migraciones funcionan sobre una copia representativa de la base.
- `git status` muestra únicamente los cambios esperados.

---

# Orden obligatorio de ejecución

1. Fase 1: seguridad.
2. Fase 2: integridad de datos.
3. Fase 3: hilos y tiempo real.
4. Fase 4: errores funcionales.
5. Fase 5: arquitectura.
6. Fase 6: pruebas y entrega.

No debe iniciarse una fase si la anterior no fue implementada, verificada y aprobada.
