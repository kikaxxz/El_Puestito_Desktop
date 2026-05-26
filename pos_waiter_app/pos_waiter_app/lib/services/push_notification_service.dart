import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:shared_preferences/shared_preferences.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

class PushNotificationService {
  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  String? deviceToken;

  Future<void> initialize() async {
    await _firebaseMessaging.requestPermission();
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    deviceToken = await _firebaseMessaging.getToken();
    
    final prefs = await SharedPreferences.getInstance();
    bool recibeAlertas = prefs.getBool('recibe_alertas') ?? true;

    if (recibeAlertas) {
      await subscribeToAlerts();
    } else {
      await unsubscribeFromAlerts();
    }

    FirebaseMessaging.onMessage.listen((RemoteMessage message) {});
  }

  Future<void> subscribeToAlerts() async {
    await _firebaseMessaging.subscribeToTopic('alertas_puestito');
  }

  Future<void> unsubscribeFromAlerts() async {
    await _firebaseMessaging.unsubscribeFromTopic('alertas_puestito');
  }
}