# POS Waiter App

Aplicación móvil construida en Flutter para el sistema POS (Punto de Venta) El Puestito.

## Características Principales
- **Gestión de Órdenes**: Envío de órdenes nuevas o adición de artículos a mesas existentes.
- **División de Cuentas**: Soporta envío de órdenes parciales y asignación a sub-cuentas.
- **Notas Personalizadas**: Los meseros pueden agregar notas (ej. "Sin hielo") a cada artículo.
- **Sincronización en Tiempo Real**: Socket.IO se encarga de recibir actualizaciones de mesas de forma instantánea.

## Requisitos y Compatibilidad
- **SDK de Flutter**: Compatible con la última versión de Flutter y Dart.
- **Android**: 
  - Soporte para dispositivos modernos (Android 14+).
  - Configurado con Gradle 8+ y Kotlin Script (kts).
  - Requiere el permiso `INTERNET` (ya incluido en el Manifest de Release).
- **Backend API**: Diseñado para comunicarse con el servidor `El_Puestito` en Flask mediante un esquema seguro (`X-API-KEY`).

## Compilación para Producción (Release)
Para generar el APK o App Bundle final, ejecute los siguientes comandos:

```bash
# Limpiar compilaciones anteriores
flutter clean
flutter pub get

# Construir App Bundle (Recomendado para Play Store)
flutter build appbundle --release

# Construir APK (Instalación directa)
flutter build apk --release
```

## Arquitectura
La aplicación utiliza **Provider** para la inyección de dependencias y el manejo de estado:
- `CartProvider`: Responsable de la lógica de carrito y de interactuar con `ApiService` para enviar órdenes.
- `SocketService`: Mantiene el estado en tiempo real de las mesas (ChangeNotifier).
- `ApiService`: Wrapper HTTP que adjunta credenciales y se comunica con el servidor central.

## Pruebas
Puede ejecutar las pruebas unitarias usando:
```bash
flutter test
```
Las pruebas validan la lógica central del `CartProvider` y la interacción con la API.
