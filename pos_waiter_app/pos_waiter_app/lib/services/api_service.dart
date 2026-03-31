import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {

  Future<String?> getServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('server_url');
  }

  Future<String> getApiKey() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('api_key') ?? 'puestito_seguro_2025';
  }

  Future<void> saveServerConfig(String url, String key) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', url);
    await prefs.setString('api_key', key);
  }

  Future<Map<String, String>> _getHeaders() async {
    final apiKey = await getApiKey();
    return {
      'Content-Type': 'application/json',
      'X-API-KEY': apiKey,
    };
  }

  Future<bool> updateItemNote(int idDetalle, String nota) async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return false;

    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/update-item-note'),
        headers: headers,
        body: json.encode({
          'id_detalle': idDetalle,
          'nota': nota,
        }),
      );
      return response.statusCode == 200;
    } catch (e) {
      print("Error Update Note: $e");
      return false;
    }
  }

  Future<bool> splitOrder(String mesaKey, List<Map<String, dynamic>> items) async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return false;
    
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/split-order'),
        headers: headers,
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

  Future<bool> cancelOrder(String mesaKey) async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return false;
    
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/cancel-order'),
        headers: headers,
        body: json.encode({'mesa_key': mesaKey}),
      );
      return response.statusCode == 200;
    } catch (e) {
      print("Error Cancel Order: $e");
      return false;
    }
  }

  Future<bool> removeItems(String mesaKey, List<Map<String, dynamic>> items) async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return false;
    
    try {
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/api/remove-items'),
        headers: headers,
        body: json.encode({
          'mesa_key': mesaKey,
          'items': items,
        }),
      );
      return response.statusCode == 200;
    } catch (e) {
      print("Error Remove Items: $e");
      return false;
    }
  }

  Future<Map<String, dynamic>?> getMenu() async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return null;
    try {
      final headers = await _getHeaders();
      final response = await http.get(Uri.parse('$baseUrl/menu'), headers: headers);
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
      final headers = await _getHeaders();
      final response = await http.post(
        Uri.parse('$baseUrl/nueva-orden'),
        headers: headers,
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
      final headers = await _getHeaders();
      final response = await http.get(Uri.parse('$baseUrl/configuracion'), headers: headers);
      return (response.statusCode == 200) ? json.decode(response.body) : null;
    } catch (_) { return null; }
  }

  Future<Map<String, dynamic>?> getEstadoMesas() async {
    final baseUrl = await getServerUrl();
    if (baseUrl == null) return null;
    try {
      final headers = await _getHeaders();
      final response = await http.get(Uri.parse('$baseUrl/estado-mesas'), headers: headers);
      return (response.statusCode == 200) ? json.decode(response.body) : null;
    } catch (_) { return null; }
  }
}