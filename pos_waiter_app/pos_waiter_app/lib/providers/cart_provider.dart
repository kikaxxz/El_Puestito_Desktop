import 'package:flutter/material.dart';
import '../models/menu_models.dart';

class CartItem {
  final String id;
  final String nombre;
  final int cantidad;
  final double precio;
  final String imagen;
  final String notas;

  CartItem({
    required this.id,
    required this.nombre,
    required this.cantidad,
    required this.precio,
    required this.imagen,
    this.notas = '',
  });
  
  CartItem copyWith({
    String? id,
    String? nombre,
    int? cantidad,
    double? precio,
    String? imagen,
    String? notas,
  }) {
    return CartItem(
      id: id ?? this.id,
      nombre: nombre ?? this.nombre,
      cantidad: cantidad ?? this.cantidad,
      precio: precio ?? this.precio,
      imagen: imagen ?? this.imagen,
      notas: notas ?? this.notas,
    );
  }
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

  void updateNote(String cartKey, String note) {
    if (_items.containsKey(cartKey)) {
      final existingItem = _items[cartKey]!;
      if (existingItem.cantidad > 1) {
        _items.update(
          cartKey,
          (item) => item.copyWith(cantidad: item.cantidad - 1),
        );
        final newKey = DateTime.now().microsecondsSinceEpoch.toString();
        _items[newKey] = existingItem.copyWith(cantidad: 1, notas: note);
      } else {
        _items.update(
          cartKey,
          (item) => item.copyWith(notas: note),
        );
      }
      notifyListeners();
    }
  }

  void addItem(Platillo platillo) {
    String? targetKey;
    _items.forEach((key, item) {
      if (item.id == platillo.id && item.notas.isEmpty) {
        targetKey = key;
      }
    });

    if (targetKey != null) {
      _items.update(
        targetKey!,
        (existing) => existing.copyWith(cantidad: existing.cantidad + 1),
      );
    } else {
      final newKey = DateTime.now().microsecondsSinceEpoch.toString();
      _items.putIfAbsent(
        newKey,
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

  void removeSingleItem(String cartKey) {
    if (!_items.containsKey(cartKey)) return;
    
    if (_items[cartKey]!.cantidad > 1) {
      _items.update(
        cartKey,
        (existing) => existing.copyWith(cantidad: existing.cantidad - 1),
      );
    } else {
      _items.remove(cartKey);
    }
    notifyListeners();
  }

  void removePlatilloId(String platilloId) {
    String? targetKey;
    
    _items.forEach((key, item) {
      if (item.id == platilloId && item.notas.isEmpty) {
        targetKey = key;
      }
    });

    if (targetKey == null) {
      _items.forEach((key, item) {
        if (item.id == platilloId) targetKey = key;
      });
    }

    if (targetKey != null) {
      removeSingleItem(targetKey!);
    }
  }

  void removeItem(String cartKey) {
    _items.remove(cartKey);
    notifyListeners();
  }

  void clearCart() {
    _items = {};
    notifyListeners();
  }
}