import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;

class SocketService with ChangeNotifier {
  IO.Socket? _socket;
  bool _isConnected = false;

  final StreamController<Map<String, dynamic>> _mesasController = StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<void> _menuController =
      StreamController<void>.broadcast();

  Stream<Map<String, dynamic>> get mesasActualizadasStream => _mesasController.stream;
  Stream<void> get menuActualizadoStream => _menuController.stream;
  bool get isConnected => _isConnected;

  Future<void> initSocket() async {
    final prefs = await SharedPreferences.getInstance();
    final serverUrl = prefs.getString('server_url');
    
    if (serverUrl == null || serverUrl.isEmpty) {
      print("SocketService: No hay URL de servidor, no se puede conectar.");
      return;
    }

    if (_socket != null) {
      _socket!.disconnect();
      _socket!.dispose();
    }

    try {
      _socket = IO.io(serverUrl, <String, dynamic>{
        'transports': ['websocket'],
        'autoConnect': true,
      });

      _socket!.onConnect((_) {
        print('SocketService: Conectado al servidor $serverUrl');
        _isConnected = true;
        notifyListeners();
        _setupSocketListeners();
      });

      _socket!.onDisconnect((_) {
        print('SocketService: Desconectado');
        _isConnected = false;
        notifyListeners();
      });

      _socket!.onError((data) => print('SocketService: Error - $data'));
    } catch (e) {
      print("SocketService: Error al inicializar - ${e.toString()}");
    }
  }

  void _setupSocketListeners() {
    _socket?.on('mesas_actualizadas', (data) {
      print("SocketService: Recibido evento 'mesas_actualizadas' con datos: $data");
      try {
        if (data is Map<String, dynamic> && data.containsKey('mesas_ocupadas')) {
          final Map<String, dynamic> mesasData = Map<String, dynamic>.from(data);
          _mesasController.add(mesasData);
        }
      } catch (e) {
        print("SocketService: Error procesando payload de 'mesas_actualizadas': $e.");
      }
    });

    _socket?.on('menu_actualizado', (data) {
      print("SocketService: Recibido evento 'menu_actualizado'.");
      _menuController.add(null);
    });
  }

  void disconnect() {
    _socket?.disconnect();
    _socket?.dispose();
    _socket = null;
    _isConnected = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _mesasController.close();
    _menuController.close();
    disconnect();
    super.dispose();
  }
}