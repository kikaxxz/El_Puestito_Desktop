import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';

import './providers/cart_provider.dart';
import './services/socket_service.dart';
import './services/push_notification_service.dart';
import './screens/table_map_screen.dart';
import './screens/menu_screen.dart';
import './screens/cart_screen.dart';
import './screens/scanner_screen.dart';

final GlobalKey<ScaffoldMessengerState> globalMessengerKey = GlobalKey<ScaffoldMessengerState>();
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  final pushService = PushNotificationService();
  await pushService.initialize();

  runApp(MyApp(pushService: pushService));
}

class MyApp extends StatelessWidget {
  final PushNotificationService pushService;

  const MyApp({super.key, required this.pushService});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (ctx) => CartProvider()),
        ChangeNotifierProvider(create: (ctx) => SocketService()),
        Provider<PushNotificationService>.value(value: pushService),
      ],
      child: MaterialApp(
        navigatorKey: navigatorKey,
        scaffoldMessengerKey: globalMessengerKey,
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