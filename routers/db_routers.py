# class ItemRouter:
#     route_app_labels = {'core'}  # Add this attribute

#     def db_for_read(self, model, **hints):
    
#         if model._meta.app_label in self.route_app_labels:
#             return "item_db"
#         return None

#     def db_for_write(self, model, **hints):
    
#         if model._meta.app_label in self.route_app_labels:
#             return "item_db"
#         return None
    
#     def allow_relation(self, obj1, obj2, **hints):
#         # Allow relations between Item and other models
#         return True


#     def allow_migrate(self, db, app_label, model_name=None, **hints):
    
#         if app_label in self.route_app_labels:
#             return db == "item_db"
#         return None

# class ItemRouter:
#     route_app_labels = {'core'}

#     def db_for_read(self, model, **hints):
#         if model._meta.app_label in self.route_app_labels:
#             # Keep User-related models in default database
#             if model._meta.model_name in ['orderitem', 'order', 'userprofile']:
#                 return 'default'
#             return "item_db"
#         return None

#     def db_for_write(self, model, **hints):
#         if model._meta.app_label in self.route_app_labels:
#             # Keep User-related models in default database
#             if model._meta.model_name in ['orderitem', 'order', 'userprofile']:
#                 return 'default'
#             return "item_db"
#         return None

#     def allow_relation(self, obj1, obj2, **hints):
#         return True

#     def allow_migrate(self, db, app_label, model_name=None, **hints):
#         if app_label in self.route_app_labels:
#             if model_name in ['orderitem', 'order', 'userprofile']:
#                 return db == 'default'
#             return db == "item_db"
#         return None


class ItemRouter:
    # Apps that should always use the default (SQLite) database
    default_apps = {
        'auth', 'admin', 'sessions', 'contenttypes', 
        'account', 'sites', 'socialaccount', 'allauth',
        'django_countries', 'messages', 'address', 'userprofile'  
    }
    
    # Apps that should use different databases
    core_app = 'core'
    item_models = {'item'}
    order_models = {
        'order', 
        'orderitem', 
        'payment',
        'coupon',
        'refund',
        'orderitems'  # Changed from order_items to match model name
    }

    def db_for_read(self, model, **hints):
        app_label = model._meta.app_label
        model_name = model._meta.model_name

        # Always use default for User model
        if model._meta.model_name == 'user':
            return 'default'

        # Default database for auth and related apps
        if app_label in self.default_apps:
            return 'default'
        
        # Core app routing
        if app_label == self.core_app:
            if model_name in self.item_models:
                return 'item_db'
            if model_name in self.order_models:
                return 'other_db'
            return 'default'  
            
        return None

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations between objects in any database
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name == 'user' or app_label == 'auth':
            return db == 'default'
            
        if app_label in self.default_apps:
            return db == 'default'
            
        if app_label == self.core_app:
            if model_name in self.item_models:
                return db == 'item_db'
            if model_name in self.order_models:
                return db == 'other_db'
            return db == 'default'
            
        return None
