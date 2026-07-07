from src.database.repositories.orders import order_repo
from logger_setup import setup_logger

logger = setup_logger()

class OrderService:
    def create_new_order(self, orden_completa):
        return order_repo.create_new_order(orden_completa)
        
    def complete_order(self, mesa_key):
        return order_repo.complete_order(mesa_key)
        
    def get_active_orders_caja(self):
        return order_repo.get_active_orders_caja()
        
    def cancel_order(self, mesa_key):
        return order_repo.cancel_order_by_key(mesa_key)
        
    def split_order(self, original_mesa_key, items_to_split, target_account_key=None, new_account_name=None):
        return order_repo.split_order(original_mesa_key, items_to_split, target_account_key, new_account_name)
        
    def remove_items_from_order(self, mesa_key, items_to_remove):
        return order_repo.remove_items_from_order(mesa_key, items_to_remove)
        
    def get_kds_orders(self, destino):
        if destino == 'cocina':
            return order_repo.get_active_cocina_orders()
        else:
            return order_repo.get_active_barra_orders()
            
    def mark_order_ready(self, mesa_key, destino):
        if destino == 'cocina':
            return order_repo.mark_cocina_order_ready(mesa_key)
        else:
            return order_repo.mark_barra_order_ready(mesa_key)
            
    def mark_individual_item_ready(self, id_detalle):
        return order_repo.mark_individual_item_ready(id_detalle)
        
    def get_sales_report(self, date_str):
        return order_repo.get_sales_report(date_str)
        
    def get_sales_history_range(self, start_date=None, end_date=None, days=30):
        return order_repo.get_sales_history_range(start_date, end_date, days)

order_service = OrderService()
