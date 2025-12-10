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
    
    final allMesas = socketService.mesas;
    final relatedOrders = _getRelatedOrders(allMesas, widget.mesaKey);

    if (relatedOrders.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text("Mesa ${widget.mesaKey}")),
        body: const Center(child: Text("La mesa ya no tiene órdenes activas.")),
      );
    }

    double grandTotal = 0.0;
    for (var group in relatedOrders) {
      for (var item in group['items']) {
        final double p = double.tryParse(item['precio_unitario'].toString()) ?? 0.0;
        final int q = int.tryParse(item['cantidad'].toString()) ?? 0;
        grandTotal += (p * q);
      }
    }

    return Scaffold(
      appBar: AppBar(
        title: Text("Gestión Mesa ${widget.mesaKey}"),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.only(bottom: 20), 
              itemCount: relatedOrders.length,
              itemBuilder: (ctx, index) {
                final orderGroup = relatedOrders[index];
                return _buildOrderSection(orderGroup);
              },
            ),
          ),
          
          _buildGrandTotal(grandTotal),

          _buildBottomActions(),
        ],
      ),
    );
  }

  Widget _buildGrandTotal(double total) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey.shade300)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05), 
            offset: const Offset(0, -3), 
            blurRadius: 5
          )
        ]
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            "GRAN TOTAL:", 
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87)
          ),
          Text(
            "C\$ ${total.toStringAsFixed(2)}",
            style: TextStyle(
              fontSize: 22, 
              fontWeight: FontWeight.w900, 
              color: Colors.green.shade800
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrderSection(Map<String, dynamic> orderGroup) {
    final String key = orderGroup['key'];
    final List items = orderGroup['items'];
    final bool isSubAccount = key.contains('-');
    
    double sectionTotal = 0.0;
    for (var item in items) {
      final double precio = double.tryParse(item['precio_unitario'].toString()) ?? 0.0;
      final int cantidad = int.tryParse(item['cantidad'].toString()) ?? 0;
      sectionTotal += (precio * cantidad);
    }
    
    String title = "Cuenta Principal";
    if (isSubAccount) {
      final parts = key.split('-');
      title = "Sub-cuenta ${parts.last}";
    } else if (key.contains('+')) {
      title = "Grupo Principal ($key)";
    }

    final headerColor = isSubAccount ? Colors.blue.shade50 : Colors.orange.shade50;
    final headerTextColor = isSubAccount ? Colors.blue.shade900 : Colors.brown.shade900;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          color: headerColor,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title, 
                    style: TextStyle(
                      fontSize: 16, 
                      fontWeight: FontWeight.bold, 
                      color: headerTextColor
                    )
                  ),
                  Text(
                    "${items.length} items",
                    style: TextStyle(color: headerTextColor.withOpacity(0.7), fontSize: 12),
                  )
                ],
              ),
              Text(
                "C\$ ${sectionTotal.toStringAsFixed(2)}",
                style: TextStyle(
                  fontSize: 16, 
                  fontWeight: FontWeight.bold, 
                  color: headerTextColor
                ),
              ),
            ],
          ),
        ),

        if (items.isEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            alignment: Alignment.center,
            child: Column(
              children: [
                const Text("Esta cuenta está vacía.", style: TextStyle(fontStyle: FontStyle.italic, color: Colors.grey)),
                const SizedBox(height: 10),
                ElevatedButton.icon(
                  icon: const Icon(Icons.cleaning_services),
                  label: const Text("LIBERAR MESA VACÍA"),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.grey.shade300, 
                    foregroundColor: Colors.black87
                  ),
                  onPressed: () => _submitCancel(key),
                )
              ],
            ),
          )
        else
          ...items.map((item) => _buildItemCard(item)),
          
        const SizedBox(height: 10), 
      ],
    );
  }

  // --- AQUÍ ESTÁ EL CAMBIO CLAVE PARA NOTAS POR ÍTEM ---
  Widget _buildItemCard(dynamic item) {
    final int idDetalle = item['id_detalle']; 
    final int maxQty = item['cantidad'];
    final String estado = item['estado_item'] ?? 'pendiente'; 
    final bool isLocked = estado == 'listo'; 
    final int currentSel = _selectedQuantities[idDetalle] ?? 0;
    
    // Leemos la nota que viene del servidor
    final String notaActual = item['notas'] ?? ''; 
    
    final double precioUnitario = double.tryParse(item['precio_unitario'].toString()) ?? 0.0;
    final double subtotalItem = precioUnitario * maxQty;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      color: isLocked ? Colors.grey.shade100 : Colors.white,
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          children: [
            Row(
              children: [
                Icon(
                  isLocked ? Icons.check_circle : Icons.timer,
                  color: isLocked ? Colors.green : Colors.orange,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item['nombre'], 
                        style: TextStyle(
                          fontWeight: FontWeight.bold, 
                          fontSize: 16,
                          color: isLocked ? Colors.grey : Colors.black
                        )
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "C\$ ${precioUnitario.toStringAsFixed(2)} x $maxQty",
                        style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                      ),
                    ],
                  ),
                ),
                // BOTÓN DE NOTA (LÁPIZ)
                IconButton(
                  icon: Icon(
                    notaActual.isNotEmpty ? Icons.comment : Icons.add_comment_outlined,
                    color: notaActual.isNotEmpty ? Colors.blue : Colors.grey,
                  ),
                  tooltip: "Agregar nota (ej: sin cebolla)",
                  onPressed: () => _showNoteDialog(idDetalle, notaActual, item['nombre']),
                ),
              ],
            ),
            
            // MOSTRAR LA NOTA VISUALMENTE
            if (notaActual.isNotEmpty)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.only(top: 5, left: 34, bottom: 5),
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.yellow.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.yellow.shade300)
                ),
                child: Text(
                  "📝 $notaActual",
                  style: TextStyle(fontStyle: FontStyle.italic, color: Colors.brown.shade800),
                ),
              ),

            if (!isLocked) 
              Padding(
                padding: const EdgeInsets.only(top: 5),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      "Total: C\$ ${subtotalItem.toStringAsFixed(2)}   |   ${isLocked ? 'LISTO' : 'PENDIENTE'}",
                      style: TextStyle(
                        color: isLocked ? Colors.green.shade700 : Colors.orange.shade800,
                        fontWeight: FontWeight.bold,
                        fontSize: 12
                      ),
                    ),
                    const Spacer(),
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
                ),
              )
          ],
        ),
      ),
    );
  }

  void _showNoteDialog(int idDetalle, String currentNote, String itemName) {
    final txtController = TextEditingController(text: currentNote);
    
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text("Nota para: $itemName"),
        content: TextField(
          controller: txtController,
          decoration: const InputDecoration(
            hintText: "Ej: Sin cebolla, Salsa aparte...",
            border: OutlineInputBorder()
          ),
          maxLines: 2,
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Cancelar"),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              setState(() => _isLoading = true);
              
              final api = ApiService();
              final success = await api.updateItemNote(idDetalle, txtController.text.trim());
              
              if (mounted) {
                setState(() => _isLoading = false);
                if (success) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Nota actualizada"), duration: Duration(seconds: 1))
                  );
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Error al guardar nota"), backgroundColor: Colors.red)
                  );
                }
              }
            },
            child: const Text("Guardar"),
          )
        ],
      )
    );
  }

  Widget _buildBottomActions() {
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: const BoxDecoration(
        color: Colors.white,
      ),
      child: Row(
        children: [
          Expanded(
            child: ElevatedButton.icon(
              icon: _isLoading 
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) 
                : const Icon(Icons.delete_forever),
              label: const Text("ELIMINAR"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red, 
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12)
              ),
              onPressed: (_isLoading || !_hasSelection()) ? null : _submitDelete,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: ElevatedButton.icon(
              icon: const Icon(Icons.call_split),
              label: const Text("SEPARAR"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange, 
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12)
              ),
              onPressed: (_isLoading || !_hasSelection()) ? null : _submitSplit,
            ),
          ),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> _getRelatedOrders(Map<String, dynamic> allMesas, String currentKey) {
    String baseId = currentKey;
    if (baseId.contains('+')) {
      baseId = baseId.split('+')[0];
    }
    if (baseId.contains('-')) {
      baseId = baseId.split('-')[0];
    }
    
    List<Map<String, dynamic>> group = [];
    
    allMesas.forEach((key, data) {
      String keyBase = key;
      if (keyBase.contains('+')) keyBase = keyBase.split('+')[0];
      if (keyBase.contains('-')) keyBase = keyBase.split('-')[0];
      
      if (keyBase == baseId) {
        group.add({
          'key': key,
          'items': data['items'] ?? [],
          'fecha': data['fecha_apertura']
        });
      }
    });

    group.sort((a, b) {
      String keyA = a['key'];
      String keyB = b['key'];
      bool isSubA = keyA.contains('-');
      bool isSubB = keyB.contains('-');
      
      if (!isSubA && isSubB) return -1; 
      if (isSubA && !isSubB) return 1;
      return keyA.compareTo(keyB);
    });

    return group;
  }

  bool _hasSelection() {
    return _selectedQuantities.values.any((q) => q > 0);
  }

  Future<void> _submitSplit() async {
    setState(() => _isLoading = true);
    final api = ApiService();
    bool allSuccess = true;
    
    final socketService = Provider.of<SocketService>(context, listen: false);
    final allMesas = socketService.mesas;
    final relatedOrders = _getRelatedOrders(allMesas, widget.mesaKey);
    
    Map<String, List<Map<String, dynamic>>> batchSplit = {};

    _selectedQuantities.forEach((idDetalle, qty) {
      if (qty > 0) {
        String? foundKey;
        for (var order in relatedOrders) {
          final items = order['items'] as List;
          if (items.any((i) => i['id_detalle'] == idDetalle)) {
            foundKey = order['key'];
            break;
          }
        }
        
        if (foundKey != null) {
          if (!batchSplit.containsKey(foundKey)) batchSplit[foundKey] = [];
          batchSplit[foundKey]!.add({'id_detalle': idDetalle, 'cantidad': qty});
        }
      }
    });

    for (var entry in batchSplit.entries) {
      final success = await api.splitOrder(entry.key, entry.value);
      if (!success) allSuccess = false;
    }

    if (mounted) {
      setState(() => _isLoading = false);
      if (allSuccess) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Cuentas separadas exitosamente")));
        setState(() { _selectedQuantities.clear(); });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al separar algunos items")));
      }
    }
  }

  Future<void> _submitDelete() async {
    final confirm = await showDialog<bool>(
      context: context, 
      builder: (ctx) => AlertDialog(
        title: const Text("¿Eliminar productos?"),
        content: const Text("Se eliminarán los items seleccionados de TODAS las sub-cuentas marcadas."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Cancelar")),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("Eliminar", style: TextStyle(color: Colors.red))),
        ],
      )
    );

    if (confirm != true) return;

    setState(() => _isLoading = true);
    final api = ApiService();
    bool allSuccess = true;

    final socketService = Provider.of<SocketService>(context, listen: false);
    final relatedOrders = _getRelatedOrders(socketService.mesas, widget.mesaKey);
    Map<String, List<Map<String, dynamic>>> batchDelete = {};

    _selectedQuantities.forEach((idDetalle, qty) {
      if (qty > 0) {
        String? foundKey;
        for (var order in relatedOrders) {
          final items = order['items'] as List;
          if (items.any((i) => i['id_detalle'] == idDetalle)) {
            foundKey = order['key'];
            break;
          }
        }
        if (foundKey != null) {
          if (!batchDelete.containsKey(foundKey)) batchDelete[foundKey] = [];
          batchDelete[foundKey]!.add({'id_detalle': idDetalle, 'cantidad': qty});
        }
      }
    });

    for (var entry in batchDelete.entries) {
      final success = await api.removeItems(entry.key, entry.value);
      if (!success) allSuccess = false;
    }

    if (mounted) {
      setState(() => _isLoading = false);
      if (allSuccess) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Productos eliminados")));
        setState(() { _selectedQuantities.clear(); });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al eliminar algunos items")));
      }
    }
  }
  
  Future<void> _submitCancel(String key) async {
    setState(() => _isLoading = true);
    final api = ApiService();
    final success = await api.cancelOrder(key);
    
    if (mounted) {
      setState(() => _isLoading = false);
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Mesa liberada correctamente")));
        if (mounted) Navigator.pop(context); 
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error al liberar mesa")));
      }
    }
  }
}