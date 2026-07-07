import 'package:flutter_test/flutter_test.dart';
import 'package:pos_waiter_app/providers/cart_provider.dart';
import 'package:pos_waiter_app/models/menu_models.dart';
import 'package:pos_waiter_app/services/api_service.dart';

class MockApiService extends ApiService {
  @override
  Future<Map<String, dynamic>> enviarOrden(Map<String, dynamic> ordenData) async {
    return {'exito': true, 'msg': 'Mock Orden enviada', 'data': ordenData};
  }
}

void main() {
  group('CartProvider Tests', () {
    late CartProvider cart;

    setUp(() {
      cart = CartProvider();
    });

    test('addItem should add a platillo and increment count correctly', () {
      final platillo = Platillo(id: '1', nombre: 'Taco', descripcion: '', precio: 30.0, imagen: '');
      
      cart.addItem(platillo);
      expect(cart.itemCount, 1);
      expect(cart.totalAmount, 30.0);
      
      cart.addItem(platillo);
      expect(cart.itemCount, 2);
      expect(cart.totalAmount, 60.0);
    });

    test('updateNote should split items if they have different notes', () {
      final platillo = Platillo(id: '1', nombre: 'Taco', descripcion: '', precio: 30.0, imagen: '');
      
      cart.addItem(platillo);
      cart.addItem(platillo);
      expect(cart.items.length, 1); // 1 key, count 2

      final key = cart.items.keys.first;
      cart.updateNote(key, 'Sin cebolla');
      
      // Should now have 2 items with count 1 each (one with note, one without)
      expect(cart.items.length, 2);
      final withNote = cart.items.values.firstWhere((item) => item.notas == 'Sin cebolla');
      final withoutNote = cart.items.values.firstWhere((item) => item.notas == '');
      
      expect(withNote.cantidad, 1);
      expect(withoutNote.cantidad, 1);
    });

    test('removeSingleItem should decrement or remove completely', () {
      final platillo = Platillo(id: '1', nombre: 'Sope', descripcion: '', precio: 25.0, imagen: '');
      
      cart.addItem(platillo);
      cart.addItem(platillo);
      
      final key = cart.items.keys.first;
      cart.removeSingleItem(key);
      expect(cart.itemCount, 1);
      
      cart.removeSingleItem(key);
      expect(cart.itemCount, 0);
      expect(cart.items.isEmpty, true);
    });

    test('submitOrder should correctly map items and call api', () async {
      final platillo = Platillo(id: '1', nombre: 'Quesadilla', descripcion: '', precio: 45.0, imagen: '');
      cart.addItem(platillo);
      
      final mockApi = MockApiService();
      final response = await cart.submitOrder(
        mockApi, 
        '10', 
        ['11'], 
        '101'
      );
      
      expect(response['exito'], true);
      
      final orderData = response['data'] as Map<String, dynamic>;
      expect(orderData['numero_mesa'], '10');
      expect(orderData['mesas_enlazadas'], ['11']);
      expect(orderData['mesero_id'], '101');
      expect((orderData['items'] as List).length, 1);
      expect(orderData['items'][0]['nombre'], 'Quesadilla');
    });
  });
}
