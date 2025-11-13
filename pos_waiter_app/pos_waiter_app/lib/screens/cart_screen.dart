import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../providers/cart_provider.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  int? _tableNumber;
  List<int> _childTables = []; 
  bool _isSending = false;
  bool _didExtractData = false;

  @override
  void didChangeDependencies() {
    if (!_didExtractData) {
      // Lee los argumentos como un Mapa
      final arguments = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;

      if (arguments != null) {
        _tableNumber = arguments['mesa_padre'] as int?;
        _childTables = List<int>.from(arguments['mesas_hijas'] ?? []);
      }
      _didExtractData = true;
    }
    super.didChangeDependencies();
  }

  Future<void> _sendOrder() async {
    final cart = Provider.of<CartProvider>(context, listen: false);

    if (cart.items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('El carrito está vacío.')),
      );
      return;
    }
    
    if (_tableNumber == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Error: No se ha seleccionado una mesa.')),
      );
      return;
    }

    setState(() {
      _isSending = true;
    });

    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);

    try {
      final prefs = await SharedPreferences.getInstance();
      final serverUrl = prefs.getString('server_url');

      if (serverUrl == null || serverUrl.isEmpty) {
        messenger.showSnackBar(
          const SnackBar(content: Text('URL del servidor no configurada.')),
        );
        if (mounted)
          setState(() {
            _isSending = false;
          });
        return;
      }

      final url = Uri.parse('$serverUrl/nueva-orden');
      final String orderId = const Uuid().v4();

      final orderData = {
        'order_id': orderId,
        'numero_mesa': _tableNumber, // Mesa Padre
        'mesas_enlazadas': _childTables, 
        'mesero_id': '101', 
        'timestamp': DateTime.now().toIso8601String(), 
        'items': cart.items.values
            .map((item) => {
                  'item_id': item.id,
                  'nombre': item.nombre,
                  'cantidad': item.cantidad,
                  'precio_unitario': item.precio,
                  'imagen': item.imagen,
                  'notas': '',
                })
            .toList(),
      };

      final response = await http
          .post(
            url,
            headers: {'Content-Type': 'application/json; charset=UTF-8'},
            body: json.encode(orderData),
          )
          .timeout(const Duration(seconds: 8));

      if (!mounted) return;

      if (response.statusCode == 200) {
        messenger.showSnackBar(
          const SnackBar(content: Text('¡Orden enviada a cocina!')),
        );
        cart.clearCart();
        navigator.popUntil(ModalRoute.withName('/'));
      } else if (response.statusCode == 400) {
        final errorData = json.decode(response.body);
        final String errorMessage =
            errorData['mensaje'] ?? 'El servidor rechazó la orden.';

        messenger.showSnackBar(
          SnackBar(
            content: Text('Error: $errorMessage'),
            backgroundColor: Colors.red.shade700,
            duration: const Duration(seconds: 4),
          ),
        );
      } else {
        messenger.showSnackBar(
          SnackBar(
              content: Text('Error del servidor: Código ${response.statusCode}')),
        );
      }
    } on TimeoutException {
      if (!mounted) return;
      messenger.showSnackBar(
        const SnackBar(
            content: Text('El servidor tardó demasiado... ¿Está encendido?')),
      );
    } on SocketException {
      if (!mounted) return;
      messenger.showSnackBar(
        const SnackBar(
            content: Text(
                'No se pudo conectar al servidor. Revisa la IP y el Wi-Fi.')),
      );
    } catch (error) {
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text('Ocurrió un error: ${error.toString()}')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = Provider.of<CartProvider>(context);

    String titleText = 'Orden Actual';
    String sendingText = 'Error: No se seleccionó mesa.';
    Color sendingColor = Colors.red;

    if (_tableNumber != null) {
      if (_childTables.isNotEmpty) {
        final allTables = [_tableNumber, ..._childTables].join('/');
        titleText = 'Orden - Grupo $allTables';
        sendingText = 'Enviando orden para el Grupo $allTables';
        sendingColor = Theme.of(context).primaryColor;
      } else {
        titleText = 'Orden - Mesa $_tableNumber';
        sendingText = 'Enviando orden para la Mesa $_tableNumber';
        sendingColor = Theme.of(context).primaryColor;
      }
    }
    // --- FIN DE LÓGICA DE TEXTO ---

    return Scaffold(
      appBar: AppBar(
        title: Text(titleText),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: cart.items.length,
              itemBuilder: (ctx, i) {
                final cartItem = cart.items.values.toList()[i];
                return ListTile(
                  title: Text(cartItem.nombre),
                  subtitle: Text('Cantidad: ${cartItem.cantidad}'),
                  trailing: Text(
                    'C\$${(cartItem.precio * cartItem.cantidad).toStringAsFixed(2)}',
                  ),
                );
              },
            ),
          ),
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                Text(
                  sendingText,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: sendingColor,
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Total:',
                        style: Theme.of(context).textTheme.titleLarge),
                    Text('C\$${cart.totalAmount.toStringAsFixed(2)}',
                        style: Theme.of(context).textTheme.titleLarge),
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
                          ),
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