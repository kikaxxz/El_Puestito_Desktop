import 'dart:async';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  final MobileScannerController controller = MobileScannerController();
  bool _isProcessing = false;

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void _handleDetection(BarcodeCapture capture) async {
    if (_isProcessing) return;

    final barcode = capture.barcodes.firstOrNull;
    if (barcode?.rawValue == null) return;
    
    setState(() { _isProcessing = true; });

    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final String scannedUrl = barcode!.rawValue!;

    if (scannedUrl.startsWith('http')) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('server_url', scannedUrl);
      
      messenger.showSnackBar(
        const SnackBar(content: Text('URL del servidor guardada.')),
      );
      navigator.pop();
    } else {
      messenger.showSnackBar(
        const SnackBar(content: Text('Código QR no contiene una URL válida.')),
      );
      await Future.delayed(const Duration(seconds: 2));
      if (mounted) {
        setState(() { _isProcessing = false; });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Escanear QR del Servidor')),
      body: MobileScanner(
        controller: controller,
        onDetect: _handleDetection,
      ),
    );
  }
}