import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import './providers/cart_provider.dart';
import './services/socket_service.dart'; // <-- NUEVO
import './screens/table_map_screen.dart';
import './screens/menu_screen.dart';
import './screens/cart_screen.dart';
import './screens/scanner_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (ctx) => CartProvider()),
        ChangeNotifierProvider(create: (ctx) => SocketService()), // <-- NUEVO
      ],
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'POS Mesero - El Puestito',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.orange),
          useMaterial3: true,
        ),
        initialRoute: '/',
        routes: {
          '/': (ctx) => const TableMapScreen(),
          '/menu': (ctx) => const MenuScreen(),
          '/cart': (ctx) => const CartScreen(),
          '/scanner': (ctx) => const ScannerScreen(),
        },
      ),
    );
  }
}