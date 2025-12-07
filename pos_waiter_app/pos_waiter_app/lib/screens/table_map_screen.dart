import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/socket_service.dart';
import '../services/api_service.dart';
import 'order_detail_screen.dart'; 

class TableMapScreen extends StatefulWidget {
  const TableMapScreen({super.key});

  @override
  State<TableMapScreen> createState() => _TableMapScreenState();
}

class _TableMapScreenState extends State<TableMapScreen> {
  int _totalMesas = 0;
  bool _isJoiningMode = false;
  final Set<int> _selectedTables = {};
  
  // Suscripción para detectar cambios en la configuración
  StreamSubscription? _configSubscription;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadConfigAndInit();
      
      // --- AUTOMATIZACIÓN DE CONFIGURACIÓN ---
      final socketService = Provider.of<SocketService>(context, listen: false);
      _configSubscription = socketService.configUpdatedStream.listen((_) {
        print("TableMapScreen: Configuración actualizada detectada. Recargando...");
        _loadConfigAndInit(); 
      });
      // ---------------------------------------
    });
  }

  @override
  void dispose() {
    _configSubscription?.cancel();
    super.dispose();
  }

  Future<void> _loadConfigAndInit() async {
    final api = ApiService();
    final config = await api.getConfiguracion();
    if (config != null) {
      if (mounted) {
        setState(() {
          _totalMesas = int.tryParse(config['total_mesas'].toString()) ?? 10;
        });
        Provider.of<SocketService>(context, listen: false).initService();
      }
    }
  }

  // --- FUNCIÓN CORREGIDA: Menú de Opciones sin altura fija ---
  void _showTableOptions(BuildContext context, String mesaKey, int mesaPadreId) {
    
    // Reconstruimos la lista de mesas hijas
    List<int> mesasHijas = [];
    if (mesaKey.contains('+')) {
      final parts = mesaKey.split('+');
      for (var p in parts) {
        final m = int.tryParse(p);
        if (m != null && m != mesaPadreId) {
          mesasHijas.add(m);
        }
      }
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true, // Permite que el contenido defina la altura
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        // Usamos Padding y Column con MainAxisSize.min para evitar el overflow
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 30), // Padding inferior extra para estética
          child: Column(
            mainAxisSize: MainAxisSize.min, // <--- ESTO SOLUCIONA EL OVERFLOW
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    "Mesa $mesaKey", 
                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                  )
                ],
              ),
              const SizedBox(height: 10),
              
              // Opción 1: AGREGAR PRODUCTOS
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.add_shopping_cart, color: Colors.blue, size: 28),
                ),
                title: const Text("Agregar Productos", style: TextStyle(fontWeight: FontWeight.w600)),
                subtitle: const Text("Ir al catálogo para añadir items"),
                onTap: () {
                  Navigator.pop(ctx); 
                  Navigator.of(context).pushNamed('/menu', arguments: {
                    'mesa_padre': mesaPadreId, 
                    'mesas_hijas': mesasHijas
                  });
                },
              ),
              
              const Divider(),

              // Opción 2: DETALLE / DIVIDIR
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.receipt_long, color: Colors.orange, size: 28),
                ),
                title: const Text("Ver Detalle / Dividir", style: TextStyle(fontWeight: FontWeight.w600)),
                subtitle: const Text("Ver consumo actual o separar cuentas"),
                onTap: () {
                  Navigator.pop(ctx); 
                  Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => OrderDetailScreen(mesaKey: mesaKey)
                  ));
                },
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final socketService = Provider.of<SocketService>(context);
    final cajaData = socketService.mesas;

    final Set<int> ocupadas = {};
    
    final Map<int, Color> groupColors = {}; 
    final Map<int, String> groupIds = {};

    final List<Color> groupPalette = [
      Colors.purple, Colors.orange, Colors.teal, Colors.indigo, 
      Colors.pink, Colors.brown, Colors.cyan, Colors.deepOrange
    ];
    int groupIndex = 0;

    for (final key in cajaData.keys) {
      if (key.contains('+')) {

        final color = groupPalette[groupIndex % groupPalette.length];
        final id = String.fromCharCode(65 + (groupIndex % 26)); 

        for (final s in key.split('+')) {
          final m = int.tryParse(s);
          if (m != null) {
            ocupadas.add(m);
            groupColors[m] = color;
            groupIds[m] = id;
          }
        }
        groupIndex++;
      } else {
        String mesaRealStr = key;
        if (key.contains('-')) {
          mesaRealStr = key.split('-')[0];
        }

        final m = int.tryParse(mesaRealStr);
        if (m != null) {
          ocupadas.add(m);
        }
      }
    }

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_isJoiningMode ? 'Modo Unión' : 'Mapa de Mesas', style: const TextStyle(fontSize: 18)),
            Row(
              children: [
                Icon(Icons.circle, size: 10, color: socketService.isConnected ? Colors.green : Colors.red),
                const SizedBox(width: 5),
                Text(socketService.isConnected ? "Conectado" : "Desconectado", style: const TextStyle(fontSize: 12)),
              ],
            )
          ],
        ),
        actions: _isJoiningMode ? [] : [
          IconButton(
            icon: const Icon(Icons.refresh), 
            onPressed: () => _loadConfigAndInit(),
            tooltip: "Actualizar manual",
          ),
          IconButton(
            icon: const Icon(Icons.qr_code), 
            onPressed: () => Navigator.of(context).pushNamed('/scanner').then((_) => _loadConfigAndInit())
          ),
        ],
      ),
      body: _totalMesas == 0 
        ? const Center(child: CircularProgressIndicator())
        : GridView.builder(
            padding: const EdgeInsets.all(15),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3, 
              crossAxisSpacing: 15, 
              mainAxisSpacing: 15,
              childAspectRatio: 0.80 
            ),
            itemCount: _totalMesas,
            itemBuilder: (ctx, i) => _buildTableCard(i + 1, ocupadas, groupColors, groupIds),
          ),
      bottomNavigationBar: _isJoiningMode ? _buildJoiningControls() : null,
    );
  }

  Widget _buildTableCard(int numMesa, Set<int> ocupadas, Map<int, Color> groupColors, Map<int, String> groupIds) {
    bool ocupada = ocupadas.contains(numMesa);
    bool selected = _selectedTables.contains(numMesa);
    bool enlazada = groupColors.containsKey(numMesa);

    Color bgColor = Colors.green.shade50;
    Color borderColor = Colors.green;
    IconData icon = Icons.table_restaurant;
    Color iconColor = Colors.green;
    String statusText = "Libre";
    Widget? badge; 

    if (ocupada) {
      if (enlazada) {
        final groupColor = groupColors[numMesa]!;
        final groupId = groupIds[numMesa]!;
        
        bgColor = groupColor.withOpacity(0.1);
        borderColor = groupColor;
        icon = Icons.link;
        iconColor = groupColor;
        statusText = "Grupo $groupId";
        
        badge = Positioned(
          right: 5,
          top: 5,
          child: Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(color: groupColor, shape: BoxShape.circle),
            child: Text(groupId, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
          ),
        );

      } else {
        bgColor = Colors.red.shade50;
        borderColor = Colors.red;
        icon = Icons.restaurant_menu;
        iconColor = Colors.red;
        statusText = "Ocupada";
      }
    }

    if (selected) {
      bgColor = Colors.blue.shade50;
      borderColor = Colors.blue;
      iconColor = Colors.blue;
      icon = Icons.check_circle;
      statusText = "Seleccionada";
    }

    return GestureDetector(
      onTap: () {
        if (_isJoiningMode) {
          if (!ocupada) setState(() => selected ? _selectedTables.remove(numMesa) : _selectedTables.add(numMesa));
        } else {
          if (ocupada) {
            String keyToSend = "$numMesa";
            
            if (enlazada) {
                final socketService = Provider.of<SocketService>(context, listen: false);
                for (var k in socketService.mesas.keys) {
                  if (k.contains('+') && k.split('+').contains("$numMesa")) {
                    keyToSend = k;
                    break;
                  }
                }
            }
            
            // Invocamos el menú corregido
            _showTableOptions(context, keyToSend, numMesa);

          } else {
            Navigator.of(context).pushNamed('/menu', arguments: {'mesa_padre': numMesa, 'mesas_hijas': []});
          }
        }
      },
      onLongPress: () {
        if (!ocupada && !_isJoiningMode) setState(() { _isJoiningMode = true; _selectedTables.add(numMesa); });
      },
      child: Stack(
        children: [
          Container(
            width: double.infinity,
            height: double.infinity,
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: borderColor, width: 2),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 4,
                  offset: const Offset(2, 2)
                )
              ]
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  "$numMesa", 
                  style: TextStyle(
                    fontSize: 26, 
                    fontWeight: FontWeight.bold, 
                    color: borderColor
                  )
                ),
                const SizedBox(height: 5),
                Icon(icon, size: 28, color: iconColor),
                const SizedBox(height: 5),
                Text(
                  statusText, 
                  style: TextStyle(
                    fontSize: 12, 
                    fontWeight: FontWeight.bold,
                    color: iconColor.withOpacity(0.9)
                  )
                )
              ],
            ),
          ),
          if (badge != null) badge,
        ],
      ),
    );
  }

  Widget _buildJoiningControls() {
    return Container(
      height: 70,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      color: Colors.blueGrey.shade900,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            '${_selectedTables.length} Mesas', 
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)
          ),
          Row(
            children: [
              TextButton(
                onPressed: () => setState(() { _isJoiningMode = false; _selectedTables.clear(); }),
                child: const Text('Cancelar', style: TextStyle(color: Colors.white70)),
              ),
              const SizedBox(width: 10),
              ElevatedButton.icon(
                icon: const Icon(Icons.link),
                label: const Text("Unir"),
                style: ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent, foregroundColor: Colors.white),
                onPressed: _selectedTables.length < 2 ? null : _goToMenuJoined,
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _goToMenuJoined() {
    final sorted = _selectedTables.toList()..sort();
    Navigator.of(context).pushNamed('/menu', arguments: {
      'mesa_padre': sorted.first,
      'mesas_hijas': sorted.skip(1).toList(),
    });
    setState(() { _isJoiningMode = false; _selectedTables.clear(); });
  }
}