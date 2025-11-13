// lib/providers/cart_provider.dart

import 'package:flutter/material.dart';
import '../models/menu_models.dart';

// Clase para representar un ítem dentro del carrito.
// Necesitamos guardar el platillo, la cantidad y la imagen.
class CartItem {
  final String id;
  final String nombre;
  final int cantidad;
  final double precio;
  final String imagen;

  CartItem({
    required this.id,
    required this.nombre,
    required this.cantidad,
    required this.precio,
    required this.imagen,
  });
}

class CartProvider with ChangeNotifier {
  // Usamos un Map para guardar los ítems del carrito.
  // La clave (String) será el ID del platillo para un acceso rápido.
  Map<String, CartItem> _items = {};

  // Getter para acceder a los ítems de forma segura.
  Map<String, CartItem> get items {
    return {..._items};
  }

  // Getter para saber la cantidad total de productos en el carrito.
  int get itemCount {
    return _items.values.fold(0, (sum, item) => sum + item.cantidad);
  }

  // Getter que calcula el total de la orden.
  double get totalAmount {
    var total = 0.0;
    _items.forEach((key, cartItem) {
      total += cartItem.precio * cartItem.cantidad;
    });
    return total;
  }

  // Método para AÑADIR un platillo al carrito.
  void addItem(Platillo platillo) {
    if (_items.containsKey(platillo.id)) {
      // Si el platillo ya está, solo aumentamos la cantidad.
      _items.update(
        platillo.id,
        (existingCartItem) => CartItem(
          id: existingCartItem.id,
          nombre: existingCartItem.nombre,
          cantidad: existingCartItem.cantidad + 1,
          precio: existingCartItem.precio,
          imagen: existingCartItem.imagen,
        ),
      );
    } else {
      // Si es un platillo nuevo, lo añadimos.
      _items.putIfAbsent(
        platillo.id,
        () => CartItem(
          id: platillo.id,
          nombre: platillo.nombre,
          cantidad: 1,
          precio: platillo.precio,
          imagen: platillo.imagen,
        ),
      );
    }
    // ¡Avisamos a los widgets que estén escuchando que hubo un cambio!
    notifyListeners();
  }
  
  // Método para RESTAR una unidad de un platillo.
  void removeSingleItem(String platilloId) {
    if (!_items.containsKey(platilloId)) {
      return;
    }
    if (_items[platilloId]!.cantidad > 1) {
      // Si hay más de uno, restamos la cantidad.
       _items.update(
        platilloId,
        (existingCartItem) => CartItem(
          id: existingCartItem.id,
          nombre: existingCartItem.nombre,
          cantidad: existingCartItem.cantidad - 1,
          precio: existingCartItem.precio,
          imagen: existingCartItem.imagen,
        ),
      );
    } else {
      // Si solo queda uno, lo eliminamos del todo.
      _items.remove(platilloId);
    }
    notifyListeners();
  }

  // Método para ELIMINAR un platillo del carrito por completo.
  void removeItem(String platilloId) {
    _items.remove(platilloId);
    notifyListeners();
  }

  // Método para VACIAR el carrito por completo.
  void clearCart() {
    _items = {};
    notifyListeners();
  }
}