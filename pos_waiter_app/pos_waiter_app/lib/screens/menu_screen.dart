import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:async';
import '../models/menu_models.dart';
import '../providers/cart_provider.dart';
import '../services/socket_service.dart';

class MenuScreen extends StatefulWidget {
  const MenuScreen({super.key});

  @override
  State<MenuScreen> createState() => _MenuScreenState();
}

class _MenuScreenState extends State<MenuScreen> {
  Menu? _menuData;
  bool _isLoading = true;
  String _errorMessage = '';
  String _serverBaseUrl = '';
  int? _tableNumber;
  StreamSubscription? _menuSubscription;


  final TextEditingController _searchController = TextEditingController();
  List<Platillo> _allPlatillos = []; 
  List<Platillo> _filteredPlatillos = []; 

  @override
  void initState() {
    super.initState();
    _loadMenuFromServer();

    final socketService = Provider.of<SocketService>(context, listen: false);
    _menuSubscription = socketService.menuActualizadoStream.listen((_) {
      print("MenuScreen: Recibido evento de menú actualizado por Stream. Recargando...");
      Future.delayed(const Duration(milliseconds: 250), () {
        _loadMenuFromServer();
      });
    });

    _searchController.addListener(_filterMenu);
  }

  @override
  void dispose() {
    _menuSubscription?.cancel();
    _searchController.removeListener(_filterMenu);
    _searchController.dispose();
    super.dispose();
  }

@override
void didChangeDependencies() {
  if (_tableNumber == null) {
    final arguments = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;

    if (arguments != null) {
      _tableNumber = arguments['mesa_padre'] as int;
    }
  }
  super.didChangeDependencies();
}

  Future<void> _loadMenuFromServer() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    final prefs = await SharedPreferences.getInstance();
    final serverUrl = prefs.getString('server_url');

    if (serverUrl == null || serverUrl.isEmpty) {
      setState(() {
        _errorMessage = 'Servidor no configurado.\nPor favor, escanee el código QR.';
        _isLoading = false;
      });
      return;
    }

    setState(() {
      _serverBaseUrl = serverUrl;
    });

    try {
      final response = await http.get(Uri.parse('$serverUrl/menu')).timeout(const Duration(seconds: 5));

      print('Respuesta del servidor: ${response.body}');

      if (!mounted) return;

      if (response.statusCode == 200) {
        final menu = menuFromJson(response.body);

        // Crea una lista plana de todos los platillos para la búsqueda
        _allPlatillos = menu.categorias
            .expand((categoria) => categoria.items)
            .toList();

        setState(() {
          _menuData = menu;
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'Error del servidor al cargar el menú (Código: ${response.statusCode}).';
          _isLoading = false;
        });
      }
    } on FormatException catch (e) {
      if (!mounted) return;
      print('ERROR DE FORMATO JSON: $e');
      setState(() {
        _errorMessage = 'El menú recibido del servidor tiene un formato incorrecto.';
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      print('ERROR DE CONEXIÓN O OTRO: $e');
      setState(() {
        _errorMessage = 'No se pudo conectar al servidor.\nVerifique la conexión.';
        _isLoading = false;
      });
    }
  }

  void _filterMenu() {
    final query = _searchController.text.toLowerCase();
    if (query.isEmpty) {
      setState(() {
        _filteredPlatillos = [];
      });
    } else {
      setState(() {
        _filteredPlatillos = _allPlatillos.where((platillo) {
          return platillo.nombre.toLowerCase().contains(query);
        }).toList();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_tableNumber != null ? 'Menú - Mesa $_tableNumber' : 'Menú El Puestito'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: () {
              Navigator.of(context).pushNamed('/scanner').then((_) {
                Provider.of<SocketService>(context, listen: false).initSocket();
                _loadMenuFromServer();
              });
            },
          ),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: Consumer<CartProvider>(
        builder: (ctx, cart, child) => Badge(
          isLabelVisible: cart.itemCount > 0,
          label: Text(cart.itemCount.toString()),
          child: FloatingActionButton(
            onPressed: () {
              final arguments = ModalRoute.of(context)?.settings.arguments;
              Navigator.of(context).pushNamed('/cart', arguments: arguments);
            },
            child: const Icon(Icons.shopping_cart),
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    
    if (_errorMessage.isNotEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_errorMessage, textAlign: TextAlign.center, style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _loadMenuFromServer,
              child: const Text('Reintentar Conexión'),
            )
          ],
        ),
      );
    }


    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16.0, 16.0, 16.0, 8.0),
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              labelText: 'Buscar platillo...',
              hintText: 'Ej: Alitas, Nachos...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12.0),
              ),
            ),
          ),
        ),
        Expanded(
          child: _searchController.text.isEmpty
              ? _buildMenuListView()
              : _buildSearchResultsView(), 
        ),
      ],
    );
  }


  Widget _buildMenuListView() {
    return ListView.builder(
      itemCount: _menuData!.categorias.length,
      itemBuilder: (ctx, i) {
        final categoria = _menuData!.categorias[i];
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Text(
                categoria.nombre,
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            ...categoria.items.map((platillo) => _buildPlatilloTile(platillo)),
            const Divider(),
          ],
        );
      },
    );
  }


  Widget _buildSearchResultsView() {
    if (_filteredPlatillos.isEmpty) {
      return const Center(
        child: Text(
          'No se encontraron platillos.',
          style: TextStyle(fontSize: 16, color: Colors.grey),
        ),
      );
    }

    return ListView.builder(
      itemCount: _filteredPlatillos.length,
      itemBuilder: (ctx, i) {
        final platillo = _filteredPlatillos[i];

        return _buildPlatilloTile(platillo);
      },
    );
  }

  Widget _buildPlatilloTile(Platillo platillo) {
    final cart = Provider.of<CartProvider>(context, listen: false);
    final imageUrl = '$_serverBaseUrl/images/${platillo.imagen}';

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 15, vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: ListTile(
          leading: Image.network(
            imageUrl,
            width: 80,
            fit: BoxFit.contain,
            loadingBuilder: (context, child, progress) {
              if (progress == null) return child;
              return const SizedBox(width: 80, height: 80, child: Center(child: CircularProgressIndicator()));
            },
            errorBuilder: (context, error, stackTrace) {
              return const Icon(Icons.broken_image, size: 50, color: Colors.grey);
            },
          ),
          title: Text(platillo.nombre),
          subtitle: Text('C\$${platillo.precio.toStringAsFixed(2)}'),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: const Icon(Icons.remove_circle_outline),
                onPressed: () => cart.removeSingleItem(platillo.id),
              ),
              Consumer<CartProvider>(
                builder: (ctx, cartData, _) {
                  final quantity = cartData.items[platillo.id]?.cantidad ?? 0;
                  return Text(quantity.toString(), style: const TextStyle(fontSize: 18));
                }
              ),
              IconButton(
                icon: const Icon(Icons.add_circle),
                onPressed: () => cart.addItem(platillo),
              ),
            ],
          ),
        ),
      ),
    );
  }
}