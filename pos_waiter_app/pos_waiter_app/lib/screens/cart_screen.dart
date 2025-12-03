import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';

import '../providers/cart_provider.dart';
import '../services/api_service.dart'; // <--- IMPORTANTE

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

    // Construimos los datos igual que antes
    final orderData = {
      'order_id': const Uuid().v4(),
      'numero_mesa': _tableNumber,
      'mesas_enlazadas': _childTables, 
      'mesero_id': '101', // Podrías sacarlo de una pantalla de login futura
      'timestamp': DateTime.now().toIso8601String(), 
      'items': cart.items.values.map((item) => {
            'item_id': item.id,
            'nombre': item.nombre,
            'cantidad': item.cantidad,
            'precio_unitario': item.precio,
            'imagen': item.imagen,
            'notas': '',
          }).toList(),
    };

    // --- AQUÍ ESTA EL CAMBIO: Usamos el servicio seguro ---
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
                return ListTile(
                  title: Text(item.nombre),
                  subtitle: Text('Cant: ${item.cantidad}'),
                  trailing: Text('C\$${(item.precio * item.cantidad).toStringAsFixed(2)}'),
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
                          style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 15)),
                          child: const Text('Enviar Orden a Cocina'),
                        ),
                      ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}