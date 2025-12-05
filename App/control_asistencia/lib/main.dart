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
    const primaryColor = Color(0xFFF76606);
    const darkBackgroundColor = Color(0xFF0F0F10);
    const cardBackgroundColor = Color(0xFF1B1C1F);
    const textColor = Color(0xFFE5E7EB);
    const subtleTextColor = Color(0xFF8F949C);

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Control de Asistencia',
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        primaryColor: primaryColor,
        colorScheme: const ColorScheme.dark(
          primary: primaryColor,
          secondary: primaryColor,
          background: darkBackgroundColor,
          surface: cardBackgroundColor,
          onBackground: textColor,
          onSurface: textColor,
          error: Colors.redAccent,
          onError: Colors.white,
        ),
        scaffoldBackgroundColor: darkBackgroundColor,
        appBarTheme: const AppBarTheme(
          backgroundColor: cardBackgroundColor,
          foregroundColor: textColor,
          elevation: 1,
          centerTitle: true,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
           fillColor: cardBackgroundColor,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12.0),
             borderSide: BorderSide.none,
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12.0),
             borderSide: const BorderSide(color: primaryColor),
          ),
          labelStyle: const TextStyle(color: subtleTextColor),
          hintStyle: const TextStyle(color: subtleTextColor),
          prefixIconColor: subtleTextColor,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryColor,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16.0),
            textStyle: const TextStyle(fontSize: 18.0, fontWeight: FontWeight.bold),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12.0),
            ),
          ),
        ),
         dropdownMenuTheme: DropdownMenuThemeData(
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: cardBackgroundColor,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12.0),
              borderSide: BorderSide.none,
            ),
             contentPadding: const EdgeInsets.symmetric(vertical: 15.0, horizontal: 10.0),
          ),
           textStyle: const TextStyle(color: textColor),
          menuStyle: MenuStyle(
             backgroundColor: MaterialStateProperty.all(cardBackgroundColor),
            surfaceTintColor: MaterialStateProperty.all(cardBackgroundColor),
          ),
        ),
         textTheme: const TextTheme(
            bodyMedium: TextStyle(color: textColor),
            bodyLarge: TextStyle(color: textColor),
            titleMedium: TextStyle(color: textColor),
            titleLarge: TextStyle(color: textColor),
        ),
        iconTheme: const IconThemeData(color: textColor),
        progressIndicatorTheme: const ProgressIndicatorThemeData(
          color: primaryColor,
        ),
      ),
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
  static const String apiKey = "puestito_seguro_2025";
  
  List<Employee> _employees = [];
  bool _isLoadingEmployees = false;
  String? _selectedEmployeeId;
  String? _lockedEmployeeName; 
  bool _isDeviceLocked = false; 

  String _statusMessage = 'Cargando configuración...';
  String? _savedServerUrl;
  final LocalAuthentication _auth = LocalAuthentication();
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _loadConfiguration();
  }

  Map<String, String> _getHeaders() {
    return {
      'Content-Type': 'application/json; charset=UTF-8',
      'X-API-KEY': apiKey,
    };
  }

  Future<void> _loadConfiguration() async {
    setState(() {
      _isLoadingEmployees = true;
      _statusMessage = 'Verificando seguridad...';
    });

    final prefs = await SharedPreferences.getInstance();
    final serverUrl = prefs.getString('server_url');
    final lockedEmpId = prefs.getString('locked_employee_id'); 
    final lockedEmpName = prefs.getString('locked_employee_name');

    setState(() {
      _savedServerUrl = serverUrl;
      if (lockedEmpId != null) {
        _isDeviceLocked = true;
        _selectedEmployeeId = lockedEmpId;
        _lockedEmployeeName = lockedEmpName ?? 'Usuario Registrado';
        _statusMessage = 'Dispositivo vinculado a $_lockedEmployeeName.';
      } else {
        _isDeviceLocked = false;
      }
    });

    await _getDeviceId();

    if (serverUrl == null || serverUrl.isEmpty) {
      setState(() {
        _statusMessage = 'Servidor no configurado. Escanea el QR.';
        _isLoadingEmployees = false;
      });
      return;
    }

    if (!_isDeviceLocked) {
      await _fetchEmployees(serverUrl);
    } else {
       setState(() {
        _isLoadingEmployees = false;
      });
    }
  }

  Future<void> _fetchEmployees(String serverUrl) async {
    setState(() {
      _statusMessage = 'Obteniendo lista de empleados...';
    });
    try {
      var url = serverUrl;
      if (url.endsWith('/')) url = url.substring(0, url.length - 1);

      final response = await http
          .get(Uri.parse('$url/employees'), headers: _getHeaders())
          .timeout(const Duration(seconds: 8));

      if (!mounted) return;

      if (response.statusCode == 200) {
        final List<dynamic> employeeListJson = jsonDecode(response.body);
        setState(() {
          _employees = employeeListJson.map((json) => Employee.fromJson(json)).toList();
          _statusMessage = 'Lista cargada. Selecciona tu usuario.';
          _isLoadingEmployees = false;
        });
      } else {
        setState(() {
          _statusMessage = 'Error de API Key o Servidor (${response.statusCode})';
          _isLoadingEmployees = false;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _statusMessage = 'Error de conexión con el servidor.';
        _employees = [];
        _isLoadingEmployees = false;
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
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        deviceId = iosInfo.identifierForVendor;
      }
    } catch (e) { }

    deviceId ??= const Uuid().v4();
    await prefs.setString('unique_device_id', deviceId);
    return deviceId;
  }

  Future<void> _authenticateAndRegister() async {
    if (_isProcessing) return;

    if (_selectedEmployeeId == null) {
      setState(() {
        _statusMessage = 'Error: No se ha identificado el empleado.';
      });
      return;
    }

    setState(() { _isProcessing = true; });

    bool authenticated = false;
    try {
      setState(() { _statusMessage = 'Escanea tu huella/rostro...'; });
      authenticated = await _auth.authenticate(
        localizedReason: 'Confirma tu identidad',
        options: const AuthenticationOptions(stickyAuth: true, biometricOnly: false),
      );
    } on PlatformException catch (e) {
      setState(() {
        _statusMessage = 'Error biométrico: ${e.message}';
        _isProcessing = false;
      });
      return;
    }

    if (authenticated) {
      setState(() { _statusMessage = 'Identidad confirmada. Registrando...'; });
      await _sendAttendanceData();
    } else {
      setState(() {
        _statusMessage = 'No se pudo verificar tu identidad.';
        _isProcessing = false;
      });
    }
  }

  Future<void> _sendAttendanceData() async {
    final serverUrl = _savedServerUrl;
    final deviceId = await _getDeviceId();

    if (serverUrl == null || deviceId == null) {
        setState(() { _isProcessing = false; _statusMessage = "Error de configuración"; });
        return;
    }

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
            headers: _getHeaders(),
            body: body,
          )
          .timeout(const Duration(seconds: 10));

      final responseBody = jsonDecode(response.body);

      if (response.statusCode == 200 || response.statusCode == 201) {
        if (!_isDeviceLocked) {
          await _lockDeviceToUser(_selectedEmployeeId!);
        }
        
        setState(() {
          _statusMessage = '✅ Asistencia Registrada Correctamente';
        });
      } else {
        setState(() {
          _statusMessage = '❌ Error: ${responseBody['message'] ?? 'Servidor rechazó'}';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = '⚠ Error de red o API Key inválida.';
      });
    } finally {
      if (mounted) setState(() { _isProcessing = false; });
    }
  }

  Future<void> _lockDeviceToUser(String empId) async {
    final prefs = await SharedPreferences.getInstance();
    
    String empName = "Empleado";
    try {
      final emp = _employees.firstWhere((e) => e.id == empId);
      empName = emp.nombre;
    } catch (_) {}

    await prefs.setString('locked_employee_id', empId);
    await prefs.setString('locked_employee_name', empName);

    setState(() {
      _isDeviceLocked = true;
      _lockedEmployeeName = empName;
      _employees.clear(); 
    });
  }

  void _openScanner() async {
    await Navigator.of(context).pushNamed('/scanner');
    _loadConfiguration();
  }

  void _resetDeviceLock() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('locked_employee_id');
    await prefs.remove('locked_employee_name');
    setState(() {
      _isDeviceLocked = false;
      _selectedEmployeeId = null;
      _statusMessage = "Dispositivo desbloqueado. Recargando...";
    });
    _loadConfiguration();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Control de Asistencia'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: _openScanner,
          ),
          if (_isDeviceLocked)
            IconButton(
              icon: const Icon(Icons.lock_reset, color: Colors.grey),
              onPressed: _resetDeviceLock, 
              tooltip: "Resetear usuario",
            )
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
            else if (_isDeviceLocked)
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Theme.of(context).cardColor,
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(color: Theme.of(context).primaryColor, width: 2),
                ),
                child: Column(
                  children: [
                    const Icon(Icons.account_circle, size: 60, color: Colors.white70),
                    const SizedBox(height: 10),
                    const Text("Bienvenido de nuevo,", style: TextStyle(color: Colors.grey)),
                    const SizedBox(height: 5),
                    Text(
                      _lockedEmployeeName ?? "Empleado",
                      style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      "Este dispositivo está vinculado a tu nombre.",
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
              )
            else if (_employees.isEmpty && _savedServerUrl != null)
              Center(
                child: Text(
                  _statusMessage,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                  textAlign: TextAlign.center,
                ),
              )
            else
              DropdownButtonFormField<String>(
                value: _selectedEmployeeId,
                decoration: const InputDecoration(
                  labelText: 'Selecciona tu nombre',
                  prefixIcon: Icon(Icons.person_add),
                  helperText: "⚠️ Se vinculará este dispositivo a tu nombre permanentemente.",
                  helperMaxLines: 2,
                ),
                hint: const Text('Empleado'),
                isExpanded: true,
                items: _employees.map((Employee employee) {
                  return DropdownMenuItem<String>(
                    value: employee.id,
                    child: Text(employee.nombre),
                  );
                }).toList(),
                onChanged: (String? newValue) {
                  setState(() {
                    _selectedEmployeeId = newValue;
                  });
                },
              ),
            
            const SizedBox(height: 32.0),
            
            ElevatedButton.icon(
              icon: const Icon(Icons.fingerprint, size: 28),
              label: const Text('Registrar Entrada/Salida'),
              onPressed: _isProcessing ? null : _authenticateAndRegister,
            ),

            const SizedBox(height: 40.0),
            
            Text(
              _statusMessage,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16.0,
                color: _statusMessage.contains('Error') || _statusMessage.contains('❌')
                    ? Theme.of(context).colorScheme.error
                    : (_statusMessage.contains('Éxito') || _statusMessage.contains('✅')
                        ? Colors.green.shade400
                        : Theme.of(context).colorScheme.onBackground),
                fontWeight: FontWeight.w500,
              ),
            ),
            
            const Spacer(),
            if (_savedServerUrl != null)
              Text(
                'Servidor Conectado',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.green.shade700, fontSize: 10),
              ),
          ],
        ),
      ),
    );
  }
}