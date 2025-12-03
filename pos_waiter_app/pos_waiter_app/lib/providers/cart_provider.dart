import 'package:flutter/material.dart';
import '../models/menu_models.dart';

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

  Map<String, CartItem> _items = {};

  Map<String, CartItem> get items {
    return {..._items};
  }

  int get itemCount {
    return _items.values.fold(0, (sum, item) => sum + item.cantidad);
  }

  double get totalAmount {
    var total = 0.0;
    _items.forEach((key, cartItem) {
      total += cartItem.precio * cartItem.cantidad;
    });
    return total;
  }

  void addItem(Platillo platillo) {
    if (_items.containsKey(platillo.id)) {
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
    notifyListeners();
  }
  
  void removeSingleItem(String platilloId) {
    if (!_items.containsKey(platilloId)) {
      return;
    }
    if (_items[platilloId]!.cantidad > 1) {
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
      _items.remove(platilloId);
    }
    notifyListeners();
  }

  void removeItem(String platilloId) {
    _items.remove(platilloId);
    notifyListeners();
  }

  void clearCart() {
    _items = {};
    notifyListeners();
  }
}