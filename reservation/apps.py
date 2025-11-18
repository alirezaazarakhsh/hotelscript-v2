from django.apps import AppConfig


class ReservationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservation'

    def ready(self):
        # Import signal handlers to ensure post_save logic (wallet deduction, discounts, points) gets registered.
        # Wrapped in try/except to avoid breaking migrations if import side-effects fail temporarily.
        try:
            import reservation.signals  # noqa: F401
        except Exception:
            # Silently ignore to prevent startup crash; logs inside signals will indicate issues if any.
            pass