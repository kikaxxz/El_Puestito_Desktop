import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/socket_service.dart';
import '../services/api_service.dart';

class OrderDetailScreen extends StatefulWidget {
  final String mesaKey;
  const OrderDetailScreen({super.key, required this.mesaKey});

  @override
  State<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends State<OrderDetailScreen> {
  final Map<int, int> _selectedQuantities = {};
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    final socketService = Provider.of<SocketService>(context);
    final mesaData = socketService.mesas[widget.mesaKey];

    if (mesaData == null) {
      return Scaffold(
        appBar: AppBar(title: Text("Mesa ${widget.mesaKey}")),
        body: const Center(child: Text("La mesa ya no tiene órdenes activas.")),
      );
    }

    final List items = mesaData['items'] ?? [];

    return Scaffold(
      appBar: AppBar(
        title: Text("Detalle Mesa ${widget.mesaKey}"),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: items.length,
              itemBuilder: (ctx, i) {
                final item = items[i];
                final int idDetalle = item['id_detalle']; 
                final int maxQty = item['cantidad'];
                final int currentSel = _selectedQuantities[idDetalle] ?? 0;

                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(item['nombre'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                              Text("Cant: $maxQty  |  Unit: C\$${item['precio_unitario']}"),
                            ],
                          ),
                        ),
                        Row(
                          children: [
                            IconButton(
                              icon: const Icon(Icons.remove_circle_outline),
                              color: currentSel > 0 ? Colors.red : Colors.grey,
                              onPressed: currentSel > 0 
                                ? () => setState(() => _selectedQuantities[idDetalle] = currentSel - 1)
                                : null,
                            ),
                            Text(
                              "$currentSel",
                              style: TextStyle(
                                fontSize: 18, 
                                fontWeight: FontWeight.bold,
                                color: currentSel > 0 ? Colors.blue : Colors.black
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.add_circle_outline),
                              color: currentSel < maxQty ? Colors.green : Colors.grey,
                              onPressed: currentSel < maxQty 
                                ? () => setState(() => _selectedQuantities[idDetalle] = currentSel + 1)
                                : null,
                            ),
                          ],
                        )
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 5, offset: const Offset(0, -2))]
            ),
            child: SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                icon: _isLoading 
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) 
                  : const Icon(Icons.call_split),
                label: const Text("SEPARAR CUENTA"),
                style: ElevatedButton.styleFrom(backgroundColor: Colors.orange, foregroundColor: Colors.white),
                onPressed: (_isLoading || !_hasSelection()) ? null : _submitSplit,
              ),
            ),
          )
        ],
      ),
    );
  }

  bool _hasSelection() {
    return _selectedQuantities.values.any((q) => q > 0);
  }

  Future<void> _submitSplit() async {
    setState(() => _isLoading = true);
    
    List<Map<String, dynamic>> itemsToSend = [];
    _selectedQuantities.forEach((idDetalle, qty) {
      if (qty > 0) {
        itemsToSend.add({'id_detalle': idDetalle, 'cantidad': qty});
      }
    });

    final api = ApiService();
    final success = await api.splitOrder(widget.mesaKey, itemsToSend);

    if (mounted) {
      setState(() => _isLoading = false);
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Cuenta separada con éxito")));
        Navigator.of(context).pop(); 
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al separar la cuenta")));
      }
    }
  }
}