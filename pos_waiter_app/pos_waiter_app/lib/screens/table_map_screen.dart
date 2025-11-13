import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/socket_service.dart';

class TableMapScreen extends StatefulWidget {
  const TableMapScreen({super.key});

  @override
  State<TableMapScreen> createState() => _TableMapScreenState();
}

class _TableMapScreenState extends State<TableMapScreen> {
  bool _isLoading = true;
  String _errorMessage = '';
  int _totalMesas = 0;
  Map<String, dynamic> _cajaData = {};
  bool _isJoiningMode = false;
  final Set<int> _selectedTables = {};
  Stream<Map<String, dynamic>>? _mesasStream;

Widget _buildJoiningControls() {
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
    color: Theme.of(context).colorScheme.surfaceVariant,
    child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text('Mesas: ${_selectedTables.join(', ')}', style: const TextStyle(fontSize: 16)),
        Row(
          children: [
            TextButton(
              onPressed: () {
                setState(() {
                  _isJoiningMode = false;
                  _selectedTables.clear();
                });
              },
              child: const Text('Cancelar', style: TextStyle(color: Colors.red)),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: _selectedTables.length < 2
                  ? null 
                  : () {
                      int mesaPadre = _selectedTables.first;
                      List<int> mesasHijas = _selectedTables.skip(1).toList();

                      final arguments = {
                        'mesa_padre': mesaPadre,
                        'mesas_hijas': mesasHijas,
                      };

                      setState(() {
                        _isJoiningMode = false;
                        _selectedTables.clear();
                      });

                      Navigator.of(context).pushNamed('/menu', arguments: arguments);
                    },
              child: const Text('Juntar'),
            ),
          ],
        ),
      ],
    ),
  );
}

  @override
  void initState() {
    super.initState();
    final socketService = Provider.of<SocketService>(context, listen: false);
    setState(() {
      _mesasStream = socketService.mesasActualizadasStream;
    });
    
    _loadTableData();

    if (!socketService.isConnected) {
      socketService.initSocket();
    }
  }

  Future<void> _loadTableData() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final serverUrl = prefs.getString('server_url');

      if (serverUrl == null || serverUrl.isEmpty) {
        throw Exception(
            'Servidor no configurado. Vaya al menú para escanear el QR.');
      }

      final responses = await Future.wait([
        http.get(Uri.parse('$serverUrl/configuracion')).timeout(const Duration(seconds: 5)),
        http.get(Uri.parse('$serverUrl/estado-mesas')).timeout(const Duration(seconds: 5)),
      ]);

      if (!mounted) return;

      final configResponse = responses[0];
      int totalMesas = 0;
      if (configResponse.statusCode == 200) {
        totalMesas = json.decode(configResponse.body)['total_mesas'] ?? 0;
      } else {
        throw Exception('Error al cargar la configuración de mesas.');
      }

      final estadoResponse = responses[1];
      Map<String, dynamic> cajaData = {};
      if (estadoResponse.statusCode == 200) {
        cajaData = Map<String, dynamic>.from(json.decode(estadoResponse.body));
      } else {
        throw Exception('Error al cargar el estado de las mesas.');
      }

      setState(() {
        _totalMesas = totalMesas;
        _cajaData = cajaData; 
        _isLoading = false;
      });

    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Error al cargar datos: ${e.toString()}';
        _isLoading = false;
      });
    }
  }

  @override
Widget build(BuildContext context) {
  return Scaffold(
    appBar: AppBar(
      title: Text(_isJoiningMode ? 'Seleccione mesas para unir' : 'Mapa de Mesas'),
      // Oculta botones mientras se unen mesas
      actions: _isJoiningMode ? null : [
        IconButton(
          icon: const Icon(Icons.refresh),
          onPressed: _loadTableData,
        ),
        IconButton(
          icon: const Icon(Icons.qr_code_scanner),
          onPressed: () {
            Navigator.of(context).pushNamed('/scanner').then((_) {
              Provider.of<SocketService>(context, listen: false).initSocket();
              _loadTableData();
            });
          },
        ),
      ],
    ),
    body: StreamBuilder<Map<String, dynamic>>(
      stream: _mesasStream,
      initialData: _cajaData,
      builder: (context, snapshot) {

        if (snapshot.hasData) {
          _cajaData = snapshot.data!;
        }
        
        if (_isLoading) {
          return const Center(child: CircularProgressIndicator());
        }

        if (_errorMessage.isNotEmpty) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _errorMessage,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.red, fontSize: 16),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: _loadTableData,
                    child: const Text('Reintentar Conexión'),
                  )
                ],
              ),
            ),
          );
        }

        // El GridView
        return GridView.builder(
          padding: const EdgeInsets.all(16.0),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            crossAxisSpacing: 16.0,
            mainAxisSpacing: 16.0,
            childAspectRatio: 1.0,
          ),
          itemCount: _totalMesas,
          itemBuilder: (ctx, index) { 
            final int numeroMesa = index + 1;
            return _buildTableCard(numeroMesa);
          },
        );
      },
    ),
    bottomNavigationBar: _isJoiningMode ? _buildJoiningControls() : null,
  );
}

Widget _buildTableCard(int numeroMesa) {
  final String numeroMesaStr = numeroMesa.toString();

  String textoMesa = 'Mesa $numeroMesaStr';
  Color colorMesa = Colors.green.shade700;
  IconData iconoMesa = Icons.check_circle_outline;
  int? mesaPadreDestino;

  if (_cajaData.containsKey(numeroMesaStr)) {
    // --- ESTADO 1: Es una Mesa "Padre"
    final orden = _cajaData[numeroMesaStr];
    final List? enlazadas = orden['mesas_enlazadas'];

    if (enlazadas != null && enlazadas.isNotEmpty) {
      // Es un grupo
      final allTables = [numeroMesa, ...enlazadas].join('/');
      textoMesa = 'Grupo $allTables';
      colorMesa = Colors.red.shade700;
      iconoMesa = Icons.people_alt;
      mesaPadreDestino = numeroMesa;
    } else {
      // --- ESTADO 2: Es una mesa simple ocupada ---
      textoMesa = 'Mesa $numeroMesaStr';
      colorMesa = Colors.red.shade700;
      iconoMesa = Icons.people_alt;
      mesaPadreDestino = numeroMesa;
    }
  } else {
    // Revisa si esta mesa está en la lista 'mesas_enlazadas' de OTRA mesa
    String? padreKey;
    for (var key in _cajaData.keys) {
      final List? enlazadas = _cajaData[key]['mesas_enlazadas'];
      if (enlazadas != null && enlazadas.contains(numeroMesa)) {
        padreKey = key;
        break;
      }
    }

    if (padreKey != null) {
      textoMesa = 'Ver Mesa $padreKey';
      colorMesa = Colors.grey.shade600; // Mesas hijas en gris
      iconoMesa = Icons.link;
      mesaPadreDestino = int.parse(padreKey);
    }
  }

  final bool isSelected = _selectedTables.contains(numeroMesa);
  final bool isPadre = mesaPadreDestino == numeroMesa;

  final bool puedeSeleccionarse = (mesaPadreDestino == null) || isPadre;

  return InkWell(
    onTap: () {
      if (_isJoiningMode) {
        if (puedeSeleccionarse) {
          setState(() {
            if (isSelected) {
              _selectedTables.remove(numeroMesa);
            } else {
              _selectedTables.add(numeroMesa);
            }
          });
        }
      } else {
        final arguments = {
          'mesa_padre': mesaPadreDestino ?? numeroMesa,
          'mesas_hijas': _cajaData[mesaPadreDestino?.toString()]?['mesas_enlazadas'] ?? [],
        };
        Navigator.of(context).pushNamed('/menu', arguments: arguments);
      }
    },
    onLongPress: () {
      if (!_isJoiningMode && puedeSeleccionarse) {
        setState(() {
          _isJoiningMode = true;
          _selectedTables.add(numeroMesa);
        });
      }
    },
    borderRadius: BorderRadius.circular(12),
    child: Card(
      elevation: 4.0,
      color: colorMesa,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: isSelected
            ? BorderSide(color: Theme.of(context).primaryColorLight, width: 4)
            : BorderSide.none,
      ),
      child: Opacity(
        opacity: (_isJoiningMode && !puedeSeleccionarse) ? 0.3 : 1.0,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(iconoMesa, color: Colors.white, size: 40),
            const SizedBox(height: 10),
            Text(
              textoMesa,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
}