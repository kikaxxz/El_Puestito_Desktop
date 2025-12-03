import 'dart:async';
import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import '../services/api_service.dart';

class SocketService with ChangeNotifier {
  IO.Socket? _socket;
  bool _isConnected = false;
  Map<String, dynamic> _mesasState = {}; 
  final ApiService _apiService = ApiService();


  bool get isConnected => _isConnected;
  Map<String, dynamic> get mesas => _mesasState;

  final StreamController<void> _menuController = StreamController<void>.broadcast();
  Stream<void> get menuActualizadoStream => _menuController.stream;

  Future<void> initService() async {
    await _fetchInitialData(); 
    await _connectSocket();    
  }


  Future<void> refreshTables() async {
    print("SocketService: Refrescando mesas vía HTTP...");
    await _fetchInitialData();
  }

  Future<void> _fetchInitialData() async {
    final data = await _apiService.getEstadoMesas();
    if (data != null) {
      _mesasState = data;
      notifyListeners(); 
    }
  }

  Future<void> _connectSocket() async {
    final serverUrl = await _apiService.getServerUrl();
    if (serverUrl == null) return;

    if (_socket != null) {
      _socket!.disconnect();
      _socket!.dispose();
    }

    try {
      _socket = IO.io(serverUrl, <String, dynamic>{
        'transports': ['websocket'],
        'autoConnect': true,
        'extraHeaders': {
          'X-API-KEY': ApiService.apiKey 
        }
      });

      _socket!.onConnect((_) {
        print('Socket: Conectado');
        _isConnected = true;
        notifyListeners();
      });

      _socket!.onDisconnect((_) {
        print('Socket: Desconectado');
        _isConnected = false;
        notifyListeners();
      });

      _socket!.on('mesas_actualizadas', (data) {
        print("Socket: Evento 'mesas_actualizadas' recibido.");
        if (data is Map<String, dynamic>) {
          _mesasState = data;
          notifyListeners(); 
        }
      });

      _socket!.on('menu_actualizado', (_) => _menuController.add(null));

    } catch (e) {
      print("Socket Error: $e");
    }
  }

  @override
  void dispose() {
    _socket?.dispose();
    _menuController.close();
    super.dispose();
  }
}