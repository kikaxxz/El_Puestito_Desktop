import 'dart:convert';

Menu menuFromJson(String str) => Menu.fromJson(json.decode(str));

class Menu {
    final List<Categoria> categorias;

    Menu({
        required this.categorias,
    });

    factory Menu.fromJson(Map<String, dynamic> json) => Menu(
        categorias: List<Categoria>.from(json["categorias"].map((x) => Categoria.fromJson(x))),
    );
}

class Categoria {
    final String nombre;
    final List<Platillo> items;

    Categoria({
        required this.nombre,
        required this.items,
    });

    factory Categoria.fromJson(Map<String, dynamic> json) => Categoria(
        nombre: json["nombre"],
        items: List<Platillo>.from(json["items"].map((x) => Platillo.fromJson(x))),
    );
}

class Platillo {
    final String id;
    final String nombre;
    final String descripcion;
    final double precio;
    final String imagen;

    Platillo({
        required this.id,
        required this.nombre,
        required this.descripcion,
        required this.precio,
        required this.imagen,
    });

    factory Platillo.fromJson(Map<String, dynamic> json) => Platillo(
        id: json["id"],
        nombre: json["nombre"],
        descripcion: json["descripcion"],
        precio: json["precio"]?.toDouble(),
        imagen: json["imagen"],
    );
}