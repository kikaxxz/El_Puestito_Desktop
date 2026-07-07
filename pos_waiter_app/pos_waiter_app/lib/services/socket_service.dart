import 'dart:async';
import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:vibration/vibration.dart';
import '../services/api_service.dart';
import '../main.dart';

class SocketService with ChangeNotifier {
  IO.Socket? _socket;
  bool _isConnected = false;
  Map<String, dynamic> _mesasState = {}; 
  final ApiService _apiService = ApiService();

  bool get isConnected => _isConnected;
  Map<String, dynamic> get mesas => _mesasState;

  final StreamController<void> _menuController = StreamController<void>.broadcast();
  final StreamController<void> _configController = StreamController<void>.broadcast();

  Stream<void> get menuActualizadoStream => _menuController.stream;
  Stream<void> get configUpdatedStream => _configController.stream;

  Future<void> initService() async {
    await _fetchInitialData(); 
    await _connectSocket();    
  }

  Future<void> refreshTables() async {
    await _fetchInitialData();
  }

  Future<void> _fetchInitialData() async {
    final data = await _apiService.getEstadoMesas();
    if (data != null) {
      _mesasState = data;
      notifyListeners(); 
    }
  }

  void _mostrarAlertaSuperior(String mensaje) {
    try {
      globalMessengerKey.currentState?.hideCurrentSnackBar();
      
      globalMessengerKey.currentState?.showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.notifications_active, color: Colors.white),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  mensaje,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                ),
              ),
            ],
          ),
          backgroundColor: Colors.green.shade800,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          margin: const EdgeInsets.all(15),
        ),
      );
    } catch (_) {}

    Future.microtask(() async {
      try {
        bool? hasVibrator = await Vibration.hasVibrator();
        if (hasVibrator == true) {
          Vibration.vibrate(duration: 500);
        }
      } catch (_) {}
    });
  }

  Future<void> _connectSocket() async {
    final serverUrl = await _apiService.getServerUrl();
    if (serverUrl == null) return;

    final apiKey = await _apiService.getApiKey();

    if (_socket != null) {
      _socket!.disconnect();
      _socket!.dispose();
    }

    try {
      _socket = IO.io(serverUrl, <String, dynamic>{
        'transports': ['websocket'],
        'autoConnect': true,
        'query': {'api_key': apiKey},
      });

      _socket!.onConnect((_) {
        _isConnected = true;
        notifyListeners();
      });

      _socket!.onDisconnect((_) {
        _isConnected = false;
        notifyListeners();
      });

      _socket!.on('mesas_actualizadas', (data) {
        if (data is Map<String, dynamic>) {
          _mesasState = data;
          notifyListeners(); 
        }
      });

      _socket!.on('menu_actualizado', (_) => _menuController.add(null));

      _socket!.on('configuracion_actualizada', (_) {
        _configController.add(null);
      });

      _socket!.on('alerta_orden_lista', (data) {
        if (data != null) {
          String? mensajeExtraido;
          try {
            if (data is Map && data.containsKey('mensaje')) {
              mensajeExtraido = data['mensaje'].toString();
            } else if (data is List && data.isNotEmpty && data[0] is Map && data[0].containsKey('mensaje')) {
              mensajeExtraido = data[0]['mensaje'].toString();
            }
          } catch (_) {}

          if (mensajeExtraido != null) {
            _mostrarAlertaSuperior(mensajeExtraido);
          }
        }
      });

    } catch (_) {}
  }

  @override
  void dispose() {
    _socket?.dispose();
    _menuController.close();
    _configController.close();
    super.dispose();
  }
}