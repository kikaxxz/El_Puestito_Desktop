# Manual de Operación - El Puestito POS

Bienvenido al manual de operación del sistema de Punto de Venta (POS) "El Puestito". Este documento explica cómo utilizar las distintas partes del sistema en tu día a día.

---

## 1. Inicio del Sistema

Para iniciar el sistema, simplemente ejecuta el archivo principal (o el ejecutable si ha sido compilado). Al abrir la aplicación, te encontrarás con la **Pantalla de Inicio de Sesión**.

### Inicio de Sesión con PIN
El sistema utiliza un sistema de PIN de 4 dígitos para identificar los roles del personal. Por defecto (puedes cambiarlo en la configuración o solicitarlo a tu administrador):
- **Caja / Administrador**: (Requiere la clave del administrador configurada)
- **Cocina**: PIN `1111`
- **Barra**: PIN `2222`

Dependiendo del PIN ingresado, el sistema te redirigirá automáticamente a tu área de trabajo correspondiente.

---

## 2. Rol: Caja (Administración de Órdenes)

La pantalla de Caja es el centro neurálgico del local.

### Crear una Nueva Orden
1. Haz clic en el botón de **Nueva Orden**.
2. Selecciona la mesa o ingresa un nombre para identificar la cuenta.
3. Agrega los productos solicitados al carrito. (Puedes buscar en las distintas categorías o usar el buscador).
4. El sistema restará automáticamente los productos del inventario y enviará las comandas (KDS) a Cocina o Barra según corresponda.

### Cuentas Divididas (Split)
Si un grupo de clientes desea dividir la cuenta:
1. Selecciona la mesa activa.
2. Usa la opción **Dividir Cuenta**.
3. Selecciona los ítems que pagará la primera persona.
4. El sistema generará sub-cuentas que podrán ser cobradas independientemente.

### Pago y Cierre
- Al cobrar una mesa, el sistema imprimirá (si hay una impresora configurada) el ticket o pre-cuenta.
- Al confirmar el pago, la mesa quedará libre y la orden se guardará en el registro histórico.

---

## 3. Rol: Cocina y Barra (KDS)

Las pantallas de Cocina y Barra funcionan como un sistema de visualización de comandas (KDS).

### Recepción de Comandas
- **Automatización**: Las comandas aparecen en la pantalla tan pronto como Caja registra el pedido. No necesitas refrescar la pantalla; el sistema se sincroniza en tiempo real.
- **Categorización**: Cocina solo verá platillos y comida. Barra solo verá bebidas.

### Preparación
- Al comenzar a preparar un pedido, toca el botón de **"En Preparación"**.
- Esto informará a la Caja que el pedido está siendo atendido.
- Cuando el pedido esté listo para ser entregado a la mesa, toca **"Listo / Entregado"**. La comanda desaparecerá de tu pantalla.

---

## 4. Control de Inventario

El sistema lleva un control estricto de las existencias.
- **Validación en tiempo real**: Caja no podrá registrar una orden si no hay stock suficiente del producto.
- **Cancelaciones**: Si un producto es cancelado de una orden antes de prepararse, el stock regresará automáticamente al inventario.
- **Modificación**: Las imágenes y precios de los productos pueden modificarse desde el panel de administrador. Las imágenes del menú pueden ser alteradas libremente por el administrador sin tocar el código fuente, solo actualizando el archivo en el sistema de gestión.

---

## 5. Reportes y Nómina

- **Asistencias**: El personal puede marcar sus horas de entrada y salida mediante el lector o en pantalla. El sistema soporta múltiples turnos (ej: descanso para comer).
- **Corte de Caja**: El administrador puede realizar un corte de caja al final del día para comparar los ingresos registrados contra el efectivo y pagos con tarjeta reales.

---

## 6. Soporte Técnico

Si el sistema no imprime los tickets, verifica:
1. Que la impresora térmica esté encendida y conectada por USB.
2. Que el papel esté colocado correctamente.
3. El administrador puede revisar el archivo `config.json` para ajustar el VID/PID de la impresora o cambiar de modo USB a Red.

Si experimentas problemas de conexión en los KDS, asegúrate de que todos los dispositivos estén conectados a la misma red WiFi que la computadora de Caja.
