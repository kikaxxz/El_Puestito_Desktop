import os
from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QRect,
    QSequentialAnimationGroup, QParallelAnimationGroup, QTimer
)

from widgets.role_card import RoleCard
from widgets.pin_dialog import PinDialog 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class RoleSelectionPage(QWidget):
    role_selected = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("role_selection_page")
        
        self.ROLE_PINS = self._load_pins_from_config()
        
        self.title = QLabel("Selección de Rol", parent=self)
        self.title.setObjectName("main_title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.cards_container = QWidget(parent=self)
        
        cashier_icon_path = os.path.join(BASE_DIR,"Assets", "icon_cashier.png")
        admin_icon_path = os.path.join(BASE_DIR, "Assets", "icon_admin.png")
        cook_icon_path = os.path.join(BASE_DIR,"Assets",  "icon_cook.png")
        bar_icon_path = os.path.join(BASE_DIR, "Assets", "icon_bar.png")

        self.card_cashier = RoleCard(cashier_icon_path, "Cajero", "Cajero", parent=self.cards_container)
        self.card_admin = RoleCard(admin_icon_path, "Administrador", "Administrador", parent=self.cards_container)
        self.card_cook = RoleCard(cook_icon_path, "Cocinero", "Cocinero", parent=self.cards_container)
        self.card_bar = RoleCard(bar_icon_path, "Barra", "Barra", parent=self.cards_container)

        self.all_cards = [self.card_cashier, self.card_admin, self.card_cook, self.card_bar]
        self.initial_geometries = {}
        self._initial_setup_done = False
        
        self.card_cashier.clicked.connect(lambda: self.handle_card_click(self.card_cashier, "Cajero"))
        self.card_admin.clicked.connect(lambda: self.handle_card_click(self.card_admin, "Administrador"))
        self.card_cook.clicked.connect(lambda: self.handle_card_click(self.card_cook, "Cocinero"))
        self.card_bar.clicked.connect(lambda: self.handle_card_click(self.card_bar, "Barra"))

        self.current_animation_group = None

    def _load_pins_from_config(self):
        try:
            path = os.path.join(BASE_DIR, "assets", "config.json")
            import json
            with open(path, 'r') as f:
                data = json.load(f)
                return data.get("seguridad", {}).get("pines", {})
        except Exception:
            return {"Cajero": "0000"}     

    def handle_card_click(self, card, role_name):
        """
        Intermediario: Pide el PIN y, si es correcto, inicia la animación.
        """
        correct_pin = self.ROLE_PINS.get(role_name)
        
        dialog = PinDialog(correct_pin, role_name, parent=self)
        if dialog.exec():
            self.start_animation(card)
        else:
            print("Acceso cancelado por el usuario")

    def showEvent(self, event):
        """Se llama cada vez que la página se muestra."""
        super().showEvent(event)
        if not self._initial_setup_done:
            self.setup_initial_positions()
            self._initial_setup_done = True
        self.reset_state()
    
    def resizeEvent(self, event):
        """Se llama cuando la ventana principal cambia de tamaño."""
        super().resizeEvent(event)
        if self._initial_setup_done:
            self.recenter_elements()

    def setup_initial_positions(self):
        """Calcula la posición inicial de las tarjetas."""
        
        for card in self.all_cards:
            card.adjustSize()

        card_width = self.card_cashier.width()
        card_height = self.card_cashier.height()
        
        spacing = 30
        positions = [0, card_width + spacing, 2 * (card_width + spacing), 3 * (card_width + spacing)]
        
        for card, pos_x in zip(self.all_cards, positions):
            card.move(pos_x, 0)
            self.initial_geometries[card] = card.geometry()
            
        total_width = 4 * card_width + 3 * spacing
        self.cards_container.setFixedSize(total_width, card_height)
    
    def recenter_elements(self):
        """Recalcula el centro de la página y reposiciona los elementos."""
        if not self.isVisible():
            return
            
        self.title.adjustSize() 
        title_x = (self.width() - self.title.width()) // 2
        title_y = int(self.height() * 0.25)
        self.title.move(title_x, title_y)
        
        cards_container_x = (self.width() - self.cards_container.width()) // 2
        cards_container_y = int(self.height() * 0.5) - (self.cards_container.height() // 2)
        self.cards_container.move(cards_container_x, cards_container_y)

    def reset_state(self):
        """Restaura la página a su estado inicial antes de la animación."""
        if not self._initial_setup_done:
            return
            
        self.recenter_elements()
        
        self.title.show()
        self.title.raise_() 
        self.cards_container.show()
        
        for card in self.all_cards:
            card.setGeometry(self.initial_geometries[card])
            if card.graphicsEffect():
                card.graphicsEffect().deleteLater()
                card.setGraphicsEffect(None)
            card.setEnabled(True)
            card.show()

    def start_animation(self, selected_card):
        """Inicia la secuencia de animación completa."""

        original_selected_card_pos_in_container = selected_card.pos()
        global_pos = selected_card.mapToGlobal(QPoint(0, 0))
        selected_card_page_pos = self.mapFromGlobal(global_pos)
        selected_card.setParent(self)
        selected_card.move(selected_card_page_pos)
        selected_card.raise_()
        selected_card.show() 
        
        other_cards = [card for card in self.all_cards if card is not selected_card]
        for card in self.all_cards:
            card.setEnabled(False)
        
        anim_group_disappear = QParallelAnimationGroup()
        for card in other_cards:
            opacity_effect = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(opacity_effect)
            anim_fade = QPropertyAnimation(opacity_effect, b"opacity")
            anim_fade.setDuration(300)
            anim_fade.setEndValue(0.0)
            anim_fade.setEasingCurve(QEasingCurve.Type.InQuad)
            
            anim_slide = QPropertyAnimation(card, b"pos")
            anim_slide.setDuration(300)
            anim_slide.setEndValue(QPoint(card.pos().x(), card.pos().y() - 80))
            anim_slide.setEasingCurve(QEasingCurve.Type.InQuad)
            anim_group_disappear.addAnimation(anim_fade)
            anim_group_disappear.addAnimation(anim_slide)
        
        center_x = (self.width() - selected_card.width()) // 2
        center_y = (self.height() - selected_card.height()) // 2
        
        anim_move_to_center = QPropertyAnimation(selected_card, b"pos")
        anim_move_to_center.setDuration(400)
        anim_move_to_center.setEndValue(QPoint(center_x, center_y))
        anim_move_to_center.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        current_size = selected_card.size() 
        new_width = int(current_size.width() * 1.2)
        new_height = int(current_size.height() * 1.2)
        end_x = center_x - (new_width - current_size.width()) // 2
        end_y = center_y - (new_height - current_size.height()) // 2
        end_rect = QRect(end_x, end_y, new_width, new_height)
        
        anim_scale_and_center = QPropertyAnimation(selected_card, b"geometry")
        anim_scale_and_center.setDuration(300)
        anim_scale_and_center.setEndValue(end_rect)
        anim_scale_and_center.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        anim_group_selected = QSequentialAnimationGroup()
        anim_group_selected.addAnimation(anim_move_to_center)
        anim_group_selected.addAnimation(anim_scale_and_center) 
        
        anim_title_slide = QPropertyAnimation(self.title, b"pos")
        anim_title_slide.setDuration(400)
        anim_title_slide.setEasingCurve(QEasingCurve.Type.InCubic)
        anim_title_slide.setEndValue(QPoint(-self.title.width(), self.title.y()))
        
        final_animation_group = QParallelAnimationGroup()
        final_animation_group.addAnimation(anim_group_disappear)
        final_animation_group.addAnimation(anim_group_selected)
        final_animation_group.addAnimation(anim_title_slide)
        final_animation_group.finished.connect(lambda: self.on_animation_finished(selected_card, original_selected_card_pos_in_container))
        
        self.current_animation_group = final_animation_group
        self.current_animation_group.start()

    def on_animation_finished(self, selected_card, original_pos_in_container):
        """Se llama al final. Devuelve la tarjeta a su contenedor y emite la señal."""
        
        selected_card.setParent(self.cards_container)
        selected_card.move(original_pos_in_container)
        selected_card.show()
        
        self.role_selected.emit(selected_card.role_name)