import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';

import '../providers/cart_provider.dart';
import '../services/api_service.dart';
import '../models/menu_models.dart'; 
import '../services/socket_service.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  int? _tableNumber;
  List<int> _childTables = []; 
  bool _isSending = false;
  final ApiService _apiService = ApiService();

  @override
  void didChangeDependencies() {
    final arguments = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
    if (arguments != null && _tableNumber == null) {
      _tableNumber = arguments['mesa_padre'] as int?;
      _childTables = List<int>.from(arguments['mesas_hijas'] ?? []);
    }
    super.didChangeDependencies();
  }

  Future<Map<String, String>?> _selectTargetForNewItems(List<Map<String, dynamic>> existingOrders) async {
    String? selectedOption = existingOrders.isNotEmpty ? existingOrders.first['key'] : "new";
    final TextEditingController nameController = TextEditingController();
    final baseMesaId = _tableNumber.toString();

    return await showDialog<Map<String, String>>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text("¿Dónde agregar estos artículos?"),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ...existingOrders.map((order) {
                      final key = order['key'];
                      final isSub = key.contains('-');
                      final title = key == baseMesaId ? "Cuenta Principal" : (isSub ? "Sub-cuenta ${key.split('-').last}" : "Grupo Principal");
                      
                      return RadioListTile<String>(
                        title: Text(title),
                        value: key,
                        groupValue: selectedOption,
                        onChanged: (val) => setState(() => selectedOption = val),
                      );
                    }).toList(),
                    const Divider(),
                    RadioListTile<String>(
                      title: const Text("Nueva Sub-cuenta"),
                      value: "new",
                      groupValue: selectedOption,
                      onChanged: (val) => setState(() => selectedOption = val),
                    ),
                    if (selectedOption == "new")
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16.0),
                        child: TextField(
                          controller: nameController,
                          decoration: const InputDecoration(labelText: "Nombre de la sub-cuenta"),
                        ),
                      ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text("Cancelar"),
                ),
                ElevatedButton(
                  onPressed: selectedOption == null
                      ? null
                      : () {
                          if (selectedOption == "new" && nameController.text.trim().isEmpty) {
                            return;
                          }
                          Navigator.pop(ctx, {
                            'type': selectedOption == "new" ? "new" : "existing",
                            'value': selectedOption == "new" ? nameController.text.trim() : selectedOption!
                          });
                        },
                  child: const Text("Aceptar"),
                ),
              ],
            );
          }
        );
      }
    );
  }

  Future<void> _sendOrder() async {
    final cart = Provider.of<CartProvider>(context, listen: false);
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final socketService = Provider.of<SocketService>(context, listen: false);

    if (cart.items.isEmpty) return;
    if (_tableNumber == null) {
      messenger.showSnackBar(const SnackBar(content: Text('Error: Sin mesa asignada.')));
      return;
    }

    List<Map<String, dynamic>> existingOrders = [];
    final baseMesaId = _tableNumber.toString();
    
    socketService.mesas.forEach((key, data) {
      String keyBase = key;
      if (keyBase.contains('+')) keyBase = keyBase.split('+')[0];
      if (keyBase.contains('-')) keyBase = keyBase.split('-')[0];
      
      if (keyBase == baseMesaId) {
        existingOrders.add({'key': key});
      }
    });

    if (!existingOrders.any((order) => order['key'] == baseMesaId)) {
      existingOrders.insert(0, {'key': baseMesaId});
    }

    String? targetAccountKey;
    String? newAccountName;

    if (existingOrders.isNotEmpty) {
      final destination = await _selectTargetForNewItems(existingOrders);
      if (destination == null) return; 

      if (destination['type'] == 'existing') {
        targetAccountKey = destination['value'];
      } else {
        newAccountName = destination['value'];
      }
    }

    setState(() => _isSending = true);

    final resultado = await cart.submitOrder(
      _apiService,
      _tableNumber!.toString(),
      _childTables.map((e) => e.toString()).toList(),
      '101',
      targetAccountKey: targetAccountKey,
      newAccountName: newAccountName,
    );

    if (!mounted) return;
    setState(() => _isSending = false);

    if (resultado['exito']) {
      messenger.showSnackBar(const SnackBar(content: Text('¡Orden enviada exitosamente!')));
      cart.clearCart();
      navigator.popUntil(ModalRoute.withName('/'));
    } else {
      messenger.showSnackBar(SnackBar(
        content: Text('Error: ${resultado['msg']}'),
        backgroundColor: Colors.red,
      ));
    }
  }

  Future<void> _showSplitCartDialog() async {
    final cart = Provider.of<CartProvider>(context, listen: false);
    if (cart.items.isEmpty) return;

    Map<String, int> selectedQuantities = {};
    for (var key in cart.items.keys) {
      selectedQuantities[key] = 0;
    }

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setModalState) {
            return Container(
              padding: const EdgeInsets.all(16),
              height: MediaQuery.of(context).size.height * 0.7,
              child: Column(
                children: [
                  const Text("Dividir Orden - Seleccionar Artículos", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Divider(),
                  Expanded(
                    child: ListView.builder(
                      itemCount: cart.items.length,
                      itemBuilder: (c, i) {
                        final cartKey = cart.items.keys.elementAt(i);
                        final item = cart.items[cartKey]!;
                        final maxQty = item.cantidad;
                        final currentSel = selectedQuantities[cartKey]!;

                        return ListTile(
                          title: Text(item.nombre),
                          subtitle: Text("En carrito: $maxQty"),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.remove_circle_outline),
                                onPressed: currentSel > 0 
                                    ? () => setModalState(() => selectedQuantities[cartKey] = currentSel - 1)
                                    : null,
                              ),
                              Text("$currentSel", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                              IconButton(
                                icon: const Icon(Icons.add_circle_outline),
                                onPressed: currentSel < maxQty 
                                    ? () => setModalState(() => selectedQuantities[cartKey] = currentSel + 1)
                                    : null,
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 50),
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white
                    ),
                    child: const Text("Elegir Destino y Enviar"),
                    onPressed: () async {
                      if (!selectedQuantities.values.any((v) => v > 0)) return;
                      Navigator.pop(ctx);
                      await _processSplitCart(selectedQuantities);
                    },
                  )
                ],
              ),
            );
          }
        );
      }
    );
  }

  Future<void> _processSplitCart(Map<String, int> selectedQuantities) async {
    final socketService = Provider.of<SocketService>(context, listen: false);
    final cart = Provider.of<CartProvider>(context, listen: false);

    List<Map<String, dynamic>> existingOrders = [];
    final baseMesaId = _tableNumber.toString();
    
    socketService.mesas.forEach((key, data) {
      String keyBase = key;
      if (keyBase.contains('+')) keyBase = keyBase.split('+')[0];
      if (keyBase.contains('-')) keyBase = keyBase.split('-')[0];
      
      if (keyBase == baseMesaId) {
        existingOrders.add({'key': key});
      }
    });

    if (!existingOrders.any((order) => order['key'] == baseMesaId)) {
      existingOrders.insert(0, {'key': baseMesaId});
    }

    final destination = await _selectTargetForNewItems(existingOrders);
    if (destination == null) return;

    setState(() => _isSending = true);

    String? targetAccountKey;
    String? newAccountName;
    if (destination['type'] == 'existing') {
      targetAccountKey = destination['value'];
    } else {
      newAccountName = destination['value'];
    }

    List<Map<String, dynamic>> itemsToSend = [];
    selectedQuantities.forEach((cartKey, qty) {
      if (qty > 0) {
        final item = cart.items[cartKey]!;
        itemsToSend.add({
          'item_id': item.id,
          'nombre': item.nombre,
          'cantidad': qty,
          'precio_unitario': item.precio,
          'imagen': item.imagen,
          'notas': item.notas,
          'id_cerveza': item.idCerveza,
          'nombre_cerveza': item.nombreCerveza, 
        });
      }
    });

    final resultado = await cart.submitOrder(
      _apiService,
      _tableNumber!.toString(),
      _childTables.map((e) => e.toString()).toList(),
      '101',
      targetAccountKey: targetAccountKey,
      newAccountName: newAccountName,
      customItems: itemsToSend,
    );

    if (!mounted) return;
    setState(() => _isSending = false);

    if (resultado['exito']) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Orden parcial enviada exitosamente'))
      );
      selectedQuantities.forEach((cartKey, qty) {
        for (int i = 0; i < qty; i++) {
          cart.removeSingleItem(cartKey);
        }
      });
      if (cart.items.isEmpty) {
        Navigator.popUntil(context, ModalRoute.withName('/'));
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${resultado['msg']}'), backgroundColor: Colors.red)
      );
    }
  }

  void _showNoteDialog(BuildContext context, String cartKey, String currentNote, String itemName) {
    final txtController = TextEditingController(text: currentNote);
    
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text("Nota para $itemName"),
        content: TextField(
          controller: txtController,
          decoration: const InputDecoration(
            hintText: "Ej: Sin hielo, Término medio...",
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
            onPressed: () {
              Provider.of<CartProvider>(context, listen: false).updateNote(cartKey, txtController.text.trim());
              Navigator.pop(ctx);
            },
            child: const Text("Guardar"),
          )
        ],
      )
    );
  }

  @override
  Widget build(BuildContext context) {
    final cart = Provider.of<CartProvider>(context);
    String titleText = _tableNumber != null ? 'Mesa $_tableNumber' : 'Sin Mesa';
    if (_childTables.isNotEmpty) titleText += " (+${_childTables.length})";

    return Scaffold(
      appBar: AppBar(title: Text('Orden - $titleText')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: cart.items.length,
              itemBuilder: (ctx, i) {
                final cartKey = cart.items.keys.elementAt(i);
                final item = cart.items[cartKey]!;
                
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Column(
                      children: [
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(
                            item.nombreCerveza != null && item.nombreCerveza!.isNotEmpty
                                ? '${item.nombre} (${item.nombreCerveza})'
                                : item.nombre,
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          subtitle: Text('C\$${item.precio.toStringAsFixed(2)} x ${item.cantidad}'),
                          trailing: Text('C\$${(item.precio * item.cantidad).toStringAsFixed(2)}', 
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.green)
                          ),
                        ),
                        if (item.notas.isNotEmpty)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(8),
                            margin: const EdgeInsets.only(bottom: 8),
                            decoration: BoxDecoration(
                              color: Colors.yellow.shade100,
                              borderRadius: BorderRadius.circular(5),
                            ),
                            child: Text(
                              " ${item.notas}",
                              style: TextStyle(fontStyle: FontStyle.italic, color: Colors.brown.shade800),
                            ),
                          ),
                        
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton.icon(
                              icon: Icon(item.notas.isEmpty ? Icons.note_add_outlined : Icons.edit_note),
                              label: Text(item.notas.isEmpty ? "Agregar Nota" : "Editar Nota"),
                              onPressed: () => _showNoteDialog(context, cartKey, item.notas, item.nombre),
                            ),
                            const Spacer(),
                            IconButton(
                              icon: const Icon(Icons.remove_circle_outline, color: Colors.red),
                              onPressed: () => cart.removeSingleItem(cartKey),
                            ),
                            Text("${item.cantidad}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                            IconButton(
                              icon: const Icon(Icons.add_circle_outline, color: Colors.green),
                              onPressed: () {
                                final p = _importPlatilloDummy(item); 
                                cart.addItem(
                                  p,
                                  idCerveza: item.idCerveza,
                                  nombreCerveza: item.nombreCerveza,
                                  precioFinal: item.precio,
                                ); 
                              },
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
          const Divider(),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Total:', style: Theme.of(context).textTheme.titleLarge),
                    Text('C\$${cart.totalAmount.toStringAsFixed(2)}', style: Theme.of(context).textTheme.titleLarge),
                  ],
                ),
                const SizedBox(height: 20),
                _isSending
                    ? const CircularProgressIndicator()
                    : Column(
                        children: [
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _tableNumber == null ? null : _sendOrder,
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 15),
                                backgroundColor: Colors.orange,
                                foregroundColor: Colors.white
                              ),  
                              child: const Text('Enviar Toda la Orden', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                            ),
                          ),
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: _tableNumber == null ? null : _showSplitCartDialog,
                              icon: const Icon(Icons.call_split),
                              label: const Text('Dividir Orden (Enviar Parcial)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 15),
                                foregroundColor: Colors.orange.shade800,
                                side: BorderSide(color: Colors.orange.shade800, width: 2),
                              ),
                            ),
                          ),
                        ],
                      ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Platillo _importPlatilloDummy(CartItem item) {
    return Platillo(
      id: item.id, 
      nombre: item.nombre, 
      descripcion: '', 
      precio: item.precio, 
      imagen: item.imagen,
    );
  }
}