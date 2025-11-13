// lib/main.dart

import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:local_auth/local_auth.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:uuid/uuid.dart'; 
import 'scanner_screen.dart'; 

// Modelo de empleado
class Employee {
  final String id;
  final String nombre;

  Employee({required this.id, required this.nombre});

  factory Employee.fromJson(Map<String, dynamic> json) {
    return Employee(
      id: json['id'] ?? '',
      nombre: json['nombre'] ?? 'Sin Nombre',
    );
  }
}

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Definimos los colores principales (similares a tu app de escritorio)
    const primaryColor = Color(0xFFF76606); // Naranja Puestito
    const darkBackgroundColor = Color(0xFF0F0F10);
    const cardBackgroundColor = Color(0xFF1B1C1F);
    const textColor = Color(0xFFE5E7EB);
    const subtleTextColor = Color(0xFF8F949C);

    return MaterialApp(
      // --- QUITAR BANNER DEBUG ---
      debugShowCheckedModeBanner: false,
      // --------------------------
      title: 'Control de Asistencia',

      // --- TEMA OSCURO ---
      themeMode: ThemeMode.dark, // Forzar tema oscuro
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        primaryColor: primaryColor,
        colorScheme: const ColorScheme.dark(
          primary: primaryColor,
          secondary: primaryColor, // Usar naranja como acento también
          background: darkBackgroundColor,
          surface: cardBackgroundColor, // Color para Cards, Dropdowns, etc.
          onBackground: textColor,
          onSurface: textColor,
          error: Colors.redAccent,
          onError: Colors.white,
        ),
        scaffoldBackgroundColor: darkBackgroundColor,
        appBarTheme: const AppBarTheme(
          backgroundColor: cardBackgroundColor, // Barra superior más oscura
          foregroundColor: textColor, // Texto e íconos blancos en AppBar
          elevation: 1, // Sombra sutil
          centerTitle: true,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
           fillColor: cardBackgroundColor, // Fondo del dropdown
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12.0),
             borderSide: BorderSide.none, // Sin borde visible por defecto
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12.0),
             borderSide: const BorderSide(color: primaryColor), // Borde naranja al enfocar
          ),
          labelStyle: const TextStyle(color: subtleTextColor),
          hintStyle: const TextStyle(color: subtleTextColor),
          prefixIconColor: subtleTextColor,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryColor, // Botón naranja
            foregroundColor: Colors.white, // Texto blanco
            padding: const EdgeInsets.symmetric(vertical: 16.0),
            textStyle: const TextStyle(fontSize: 18.0, fontWeight: FontWeight.bold),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12.0),
            ),
          ),
        ),
         dropdownMenuTheme: DropdownMenuThemeData( // Estilo del menú desplegable
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: cardBackgroundColor,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12.0),
              borderSide: BorderSide.none,
            ),
             contentPadding: const EdgeInsets.symmetric(vertical: 15.0, horizontal: 10.0), // Ajustar padding
          ),
           textStyle: const TextStyle(color: textColor), // Texto del item seleccionado
          menuStyle: MenuStyle(
             backgroundColor: MaterialStateProperty.all(cardBackgroundColor), // Fondo del menú
            surfaceTintColor: MaterialStateProperty.all(cardBackgroundColor),
          ),
        ),
         textTheme: const TextTheme( // Asegurar colores de texto base
            bodyMedium: TextStyle(color: textColor),
            bodyLarge: TextStyle(color: textColor),
            titleMedium: TextStyle(color: textColor),
            titleLarge: TextStyle(color: textColor),
        ),
         iconTheme: const IconThemeData(color: textColor), // Color de íconos general
        progressIndicatorTheme: const ProgressIndicatorThemeData(
           color: primaryColor, // Indicador de carga naranja
        ),
      ),
      // -----------------

      initialRoute: '/',
      routes: {
        '/': (context) => const AttendanceScreen(),
        '/scanner': (context) => const ScannerScreen(),
      },
    );
  }
}

class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  List<Employee> _employees = [];
  bool _isLoadingEmployees = false;
  String? _selectedEmployeeId;
  String _statusMessage = 'Cargando configuración...';
  String? _savedServerUrl;
  final LocalAuthentication _auth = LocalAuthentication();
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    // _resetDeviceId(); // Comenta o elimina esta línea para producción
    _loadServerUrlAndEmployees();
  }

  /// Elimina el ID único guardado (para pruebas)
  Future<void> _resetDeviceId() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('unique_device_id');
    print("🧹 ID único eliminado. Se generará uno nuevo al reiniciar.");
  }

  Future<void> _loadServerUrlAndEmployees() async {
    setState(() {
      _isLoadingEmployees = true;
      _statusMessage = 'Cargando URL del servidor...';
    });

    final prefs = await SharedPreferences.getInstance();
    final serverUrl = prefs.getString('server_url');

    setState(() {
      _savedServerUrl = serverUrl;
    });

    final deviceId = await _getDeviceId();
    print("📱 ID único de este dispositivo: $deviceId");

    if (serverUrl == null || serverUrl.isEmpty) {
      setState(() {
        _statusMessage = 'Servidor no configurado. Escanea el QR.';
        _isLoadingEmployees = false;
      });
      return;
    }

    await _fetchEmployees(serverUrl);

    setState(() {
      _isLoadingEmployees = false;
      if (_statusMessage.startsWith('Cargando')) {
        _statusMessage = 'Por favor, selecciona tu nombre y registra tu asistencia.';
      }
    });
  }

  Future<void> _fetchEmployees(String serverUrl) async {
    setState(() {
      _statusMessage = 'Obteniendo lista de empleados...';
    });
    try {
      var url = serverUrl;
      if (url.endsWith('/')) url = url.substring(0, url.length - 1);

      final response = await http
          .get(Uri.parse('$url/employees'))
          .timeout(const Duration(seconds: 8));

      if (!mounted) return;

      if (response.statusCode == 200) {
        final List<dynamic> employeeListJson = jsonDecode(response.body);
        setState(() {
          _employees = employeeListJson.map((json) => Employee.fromJson(json)).toList();
          _statusMessage = 'Lista de empleados cargada.';
          _selectedEmployeeId = null;
        });
      } else {
        final errorBody = jsonDecode(response.body);
        setState(() {
          _statusMessage =
              'Error al cargar empleados: ${errorBody['error'] ?? response.statusCode}';
          _employees = [];
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _statusMessage = 'Error de red al cargar empleados: ${e.toString()}';
        _employees = [];
      });
    }
  }


  Future<String?> _getDeviceId() async {
    final prefs = await SharedPreferences.getInstance();

    final storedId = prefs.getString('unique_device_id');
    if (storedId != null) return storedId;

    final DeviceInfoPlugin deviceInfo = DeviceInfoPlugin();
    String? deviceId;

    try {
      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        deviceId = androidInfo.id; 
        if (deviceId == null || deviceId.startsWith('AP') || deviceId.length < 10) {
          deviceId = null;
        }
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        deviceId = iosInfo.identifierForVendor;
      }
    } catch (e) {
      print('Error al obtener Device ID nativo: $e');
    }

    // Genera UUID si no hay uno válido
    deviceId ??= const Uuid().v4();

    await prefs.setString('unique_device_id', deviceId);

    print("✅ ID único asignado a este dispositivo: $deviceId");
    return deviceId;
  }

  Future<void> _authenticateAndRegister() async {
    if (_isProcessing) return;

    if (_selectedEmployeeId == null) {
      setState(() {
        _statusMessage = 'Error: Debes seleccionar un empleado primero.';
      });
      return;
    }

    setState(() {
      _isProcessing = true;
    });

    bool authenticated = false;
    try {
      setState(() {
        _statusMessage = 'Por favor, autentícate...';
      });

      authenticated = await _auth.authenticate(
        localizedReason: 'Autentícate para registrar tu asistencia',
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: false,
        ),
      );
    } on PlatformException catch (e) {
      setState(() {
        _statusMessage = 'Error de autenticación: ${e.message}';
        _isProcessing = false;
      });
      return;
    }

    if (!mounted) return;

    if (authenticated) {
      setState(() {
        _statusMessage = 'Autenticación exitosa. Enviando datos...';
      });
      await _sendAttendanceData();
    } else {
      setState(() {
        _statusMessage = 'Autenticación fallida. Inténtalo de nuevo.';
      });
    }

    if (mounted) {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Future<void> _sendAttendanceData() async {
    final serverUrl = _savedServerUrl;

    if (serverUrl == null || serverUrl.isEmpty) {
      setState(() {
        _statusMessage = 'Error: No hay URL del servidor. Escanea el QR.';
      });
      return;
    }

    final deviceId = await _getDeviceId();
    if (deviceId == null || deviceId.isEmpty) {
      setState(() {
        _statusMessage = 'Error: No se pudo obtener el ID del dispositivo.';
      });
      return;
    }

    print("📡 Enviando registro con deviceId: $deviceId");

    try {
      final body = jsonEncode({
        'employee_id': _selectedEmployeeId,
        'deviceId': deviceId,
      });

      var url = serverUrl;
      if (url.endsWith('/')) url = url.substring(0, url.length - 1);

      final response = await http
          .post(
            Uri.parse('$url/registrar'),
            headers: {'Content-Type': 'application/json; charset=UTF-8'},
            body: body,
          )
          .timeout(const Duration(seconds: 10));

      final responseBody = jsonDecode(response.body);

      if (response.statusCode == 200 || response.statusCode == 201) {
        setState(() {
          _statusMessage = 'Éxito: ${responseBody['message']}';
        });
      } else {
        setState(() {
          _statusMessage =
              'Error: ${responseBody['message'] ?? 'Error desconocido del servidor.'}';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = 'Error de red: No se pudo conectar al servidor.';
      });
    }
  }

  void _openScanner() async {
    await Navigator.of(context).pushNamed('/scanner');
    _loadServerUrlAndEmployees();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Control de Asistencia'),
        // centerTitle: true, // Ya está centrado por el tema
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            tooltip: 'Escanear QR del Servidor',
            onPressed: _openScanner,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            if (_isLoadingEmployees)
              const Center(child: CircularProgressIndicator())
            else if (_employees.isEmpty && _savedServerUrl != null)
              Center(
                child: Text(
                  _statusMessage.contains('Error')
                      ? _statusMessage
                      : 'No se encontraron empleados en el servidor.',
                  style: TextStyle(color: Theme.of(context).colorScheme.error), // Usar color de error del tema
                  textAlign: TextAlign.center,
                ),
              )
            else
              DropdownButtonFormField<String>(
                value: _selectedEmployeeId,
                decoration: const InputDecoration( // Usará inputDecorationTheme del tema
                  labelText: 'Selecciona tu nombre',
                  prefixIcon: Icon(Icons.person),
                ),
                hint: const Text('Empleado'),
                isExpanded: true,
                // Estilos del menú y items ahora controlados por dropdownMenuTheme
                items: _employees.map((Employee employee) {
                  return DropdownMenuItem<String>(
                    value: employee.id,
                    child: Text(employee.nombre),
                  );
                }).toList(),
                onChanged: (String? newValue) {
                  setState(() {
                    _selectedEmployeeId = newValue;
                    _statusMessage =
                        'Empleado seleccionado. Listo para registrar.';
                  });
                },
              ),
            const SizedBox(height: 32.0),
            ElevatedButton.icon(
              icon: const Icon(Icons.fingerprint), // O Icons.touch_app
              label: const Text('Registrar Asistencia'),
              // Estilo tomado de elevatedButtonTheme
              onPressed:
                  _isProcessing || _employees.isEmpty ? null : _authenticateAndRegister,
            ),
            const SizedBox(height: 40.0),
            Text(
              _statusMessage,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16.0,
                color: _statusMessage.contains('Error') ||
                        _statusMessage.contains('ADVERTENCIA')
                    ? Theme.of(context).colorScheme.error
                    : (_statusMessage.contains('Éxito')
                        ? Colors.green.shade400
                        : Theme.of(context).colorScheme.onBackground),
                fontWeight: FontWeight.w500,
              ),
            ),
            const Spacer(),
            Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Text(
                'Servidor: ${_savedServerUrl ?? "No configurado"}',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Theme.of(context).textTheme.bodySmall?.color?.withOpacity(0.7), // Usar color del tema
                  fontSize: 12
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}