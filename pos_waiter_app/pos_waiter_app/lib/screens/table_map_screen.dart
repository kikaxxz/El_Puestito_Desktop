import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/socket_service.dart';
import '../services/api_service.dart';

class TableMapScreen extends StatefulWidget {
  const TableMapScreen({super.key});

  @override
  State<TableMapScreen> createState() => _TableMapScreenState();
}

class _TableMapScreenState extends State<TableMapScreen> {
  int _totalMesas = 0;
  bool _isJoiningMode = false;
  final Set<int> _selectedTables = {};
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadConfigAndInit();
    });
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
        // Mesa individual ocupada
        final m = int.tryParse(key);
        if (m != null) ocupadas.add(m);
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
            onPressed: () => socketService.refreshTables(),
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
        // Ocupada Individual (Rojo)
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
          Navigator.of(context).pushNamed('/menu', arguments: {'mesa_padre': numMesa, 'mesas_hijas': []});
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