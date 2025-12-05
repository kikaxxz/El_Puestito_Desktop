import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String apiKey = "puestito_seguro_2025"; 

  Future<String?> getServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('server_url');
  }

  Future<bool> splitOrder(String mesaKey, List<Map<String, dynamic>> items) async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return false;
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/split-order'),
        headers: _getHeaders(),
        body: json.encode({
          'mesa_key': mesaKey,
          'items': items,
        }),
      );
      return response.statusCode == 200;
    } catch (e) {
      print("Error Split Order: $e");
      return false;
    }
  }

  Map<String, String> _getHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-API-KEY': apiKey, 
    };
  }

  Future<Map<String, dynamic>?> getMenu() async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return null;
    try {
      final response = await http.get(Uri.parse('$baseUrl/menu'), headers: _getHeaders());
      return (response.statusCode == 200) ? json.decode(response.body) : null;
    } catch (e) {
      print("Error Menu: $e");
      return null;
    }
  }

  Future<Map<String, dynamic>> enviarOrden(Map<String, dynamic> ordenData) async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return {'exito': false, 'msg': 'URL no configurada'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/nueva-orden'),
        headers: _getHeaders(),
        body: json.encode(ordenData),
      );

      if (response.statusCode == 200) {
        return {'exito': true, 'msg': 'Orden enviada'};
      } else {
        final body = json.decode(response.body);
        return {'exito': false, 'msg': body['mensaje'] ?? 'Error del servidor'};
      }
    } catch (e) {
      return {'exito': false, 'msg': e.toString()};
    }
  }

  Future<Map<String, dynamic>?> getConfiguracion() async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return null;
    try {
      final response = await http.get(Uri.parse('$baseUrl/configuracion'), headers: _getHeaders());
      return (response.statusCode == 200) ? json.decode(response.body) : null;
    } catch (_) { return null; }
  }

  Future<Map<String, dynamic>?> getEstadoMesas() async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return null;
    try {
      final response = await http.get(Uri.parse('$baseUrl/estado-mesas'), headers: _getHeaders());
      return (response.statusCode == 200) ? json.decode(response.body) : null;
    } catch (_) { return null; }
  }
}