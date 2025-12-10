import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';

import '../providers/cart_provider.dart';
import '../services/api_service.dart';
import '../models/menu_models.dart'; 

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

  Future<void> _sendOrder() async {
    final cart = Provider.of<CartProvider>(context, listen: false);
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);

    if (cart.items.isEmpty) return;
    if (_tableNumber == null) {
      messenger.showSnackBar(const SnackBar(content: Text('Error: Sin mesa asignada.')));
      return;
    }

    setState(() => _isSending = true);

    final orderData = {
      'order_id': const Uuid().v4(),
      'numero_mesa': _tableNumber,
      'mesas_enlazadas': _childTables, 
      'mesero_id': '101', 
      'timestamp': DateTime.now().toIso8601String(), 
      'items': cart.items.values.map((item) => {
            'item_id': item.id,
            'nombre': item.nombre,
            'cantidad': item.cantidad,
            'precio_unitario': item.precio,
            'imagen': item.imagen,
            'notas': item.notas, 
          }).toList(),
    };

    final resultado = await _apiService.enviarOrden(orderData);

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

  void _showNoteDialog(BuildContext context, String itemId, String currentNote, String itemName) {
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
              Provider.of<CartProvider>(context, listen: false).updateNote(itemId, txtController.text.trim());
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
                final item = cart.items.values.toList()[i];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Column(
                      children: [
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(item.nombre, style: const TextStyle(fontWeight: FontWeight.bold)),
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
                              "📝 ${item.notas}",
                              style: TextStyle(fontStyle: FontStyle.italic, color: Colors.brown.shade800),
                            ),
                          ),
                        
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton.icon(
                              icon: Icon(item.notas.isEmpty ? Icons.note_add_outlined : Icons.edit_note),
                              label: Text(item.notas.isEmpty ? "Agregar Nota" : "Editar Nota"),
                              onPressed: () => _showNoteDialog(context, item.id, item.notas, item.nombre),
                            ),
                            const Spacer(),
                            IconButton(
                              icon: const Icon(Icons.remove_circle_outline, color: Colors.red),
                              onPressed: () => cart.removeSingleItem(item.id),
                            ),
                            Text("${item.cantidad}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                            IconButton(
                              icon: const Icon(Icons.add_circle_outline, color: Colors.green),
                              onPressed: () {
                                final p = _importPlatilloDummy(item); 
                                cart.addItem(p); 
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
                    : SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _tableNumber == null ? null : _sendOrder,
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 15),
                            backgroundColor: Colors.orange,
                            foregroundColor: Colors.white
                          ),
                          child: const Text('Enviar Orden a Cocina', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                        ),
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
      imagen: item.imagen
    );
  }
}