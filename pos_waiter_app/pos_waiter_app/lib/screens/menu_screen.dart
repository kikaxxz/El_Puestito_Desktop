import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:async';
import '../models/menu_models.dart';
import '../providers/cart_provider.dart';
import '../services/socket_service.dart';
import '../services/api_service.dart'; 

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
  final ApiService _apiService = ApiService(); 

  final TextEditingController _searchController = TextEditingController();
  List<Platillo> _allPlatillos = []; 
  List<Platillo> _filteredPlatillos = []; 

  @override
  void initState() {
    super.initState();
    _loadMenuFromServer();

    final socketService = Provider.of<SocketService>(context, listen: false);
    _menuSubscription = socketService.menuActualizadoStream.listen((_) {
      print("MenuScreen: Actualizando menú por evento socket...");
      Future.delayed(const Duration(milliseconds: 250), _loadMenuFromServer);
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
    if (!mounted) return;
    setState(() { _isLoading = true; _errorMessage = ''; });

    final url = await _apiService.getServerUrl();
    if (url == null) {
      if (mounted) setState(() { _errorMessage = 'Escanee el QR primero.'; _isLoading = false; });
      return;
    }
    _serverBaseUrl = url;

    final menuJson = await _apiService.getMenu();

    if (!mounted) return;

    if (menuJson != null) {
      try {
        final menu = Menu.fromJson(menuJson); 
        
        _allPlatillos = menu.categorias.expand((c) => c.items).toList();
        setState(() {
          _menuData = menu;
          _isLoading = false;
        });
      } catch (e) {
        setState(() { _errorMessage = 'Error procesando menú.'; _isLoading = false; });
      }
    } else {
      setState(() { _errorMessage = 'No se pudo cargar el menú (Error de Red/Auth).'; _isLoading = false; });
    }
  }

  void _filterMenu() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredPlatillos = query.isEmpty 
          ? [] 
          : _allPlatillos.where((p) => p.nombre.toLowerCase().contains(query)).toList();
    });
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
                Provider.of<SocketService>(context, listen: false).initService();
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
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_errorMessage.isNotEmpty) {
      return Center(child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(_errorMessage),
          ElevatedButton(onPressed: _loadMenuFromServer, child: const Text('Reintentar'))
        ],
      ));
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              labelText: 'Buscar...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchController.text.isNotEmpty 
                  ? IconButton(icon: const Icon(Icons.clear), onPressed: _searchController.clear) 
                  : null,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
        Expanded(
          child: _searchController.text.isEmpty ? _buildMenuListView() : _buildSearchResultsView(),
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
              padding: const EdgeInsets.all(10),
              child: Text(categoria.nombre, style: Theme.of(context).textTheme.titleLarge),
            ),
            ...categoria.items.map((p) => _buildPlatilloTile(p)),
            const Divider(),
          ],
        );
      },
    );
  }

  Widget _buildSearchResultsView() {
    if (_filteredPlatillos.isEmpty) return const Center(child: Text('Sin resultados'));
    return ListView.builder(
      itemCount: _filteredPlatillos.length,
      itemBuilder: (ctx, i) => _buildPlatilloTile(_filteredPlatillos[i]),
    );
  }

  Widget _buildPlatilloTile(Platillo platillo) {
    final cart = Provider.of<CartProvider>(context, listen: false);
    final imageUrl = '$_serverBaseUrl/images/${platillo.imagen}';

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 15, vertical: 4),
      child: ListTile(
        leading: Image.network(imageUrl, width: 60, height: 60, fit: BoxFit.cover,
          errorBuilder: (_,__,___) => const Icon(Icons.broken_image),
        ),
        title: Text(platillo.nombre),
        subtitle: Text('C\$${platillo.precio.toStringAsFixed(2)}'),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(icon: const Icon(Icons.remove_circle), onPressed: () => cart.removeSingleItem(platillo.id)),
            Consumer<CartProvider>(builder: (_, c, __) => Text('${c.items[platillo.id]?.cantidad ?? 0}')),
            IconButton(icon: const Icon(Icons.add_circle), onPressed: () => cart.addItem(platillo)),
          ],
        ),
      ),
    );
  }
}