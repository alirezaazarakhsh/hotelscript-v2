from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from authentication.models import NaturalProfile
from finance.models import Wallet

class Command(BaseCommand):
    help = 'چک و اعمال انقضای سطوح کاربری موقتی و تمدید خودکار'

    def handle(self, *args, **options):
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        
        # تمدید خودکار برای کاربرانی که نزدیک انقضا هستند و فعال کرده‌اند
        auto_renew_profiles = NaturalProfile.objects.filter(
            expiration_date__lte=tomorrow,
            expiration_date__gt=now,
            auto_renewal_enabled=True,
            previous_level__isnull=False
        )
        renewed_count = 0
        for profile in auto_renew_profiles:
            # فرض کنیم هزینه ماهانه 100,000 تومان (باید از پکیج گرفته شود، اما برای سادگی)
            cost = 100000  # TODO: از مدل SubscriptionPackage بگیر
            try:
                wallet = profile.base_user.bot_wallet
                if wallet.balance >= cost:
                    wallet.balance -= cost
                    wallet.save()
                    # تمدید expiration_date برای 30 روز
                    profile.expiration_date += timedelta(days=30)
                    profile.save(update_fields=['expiration_date'])
                    renewed_count += 1
                    self.stdout.write(f'اشتراک {profile} تمدید شد.')
                else:
                    self.stdout.write(f'کیف پول {profile} کافی نیست.')
            except Wallet.DoesNotExist:
                self.stdout.write(f'کیف پول برای {profile} وجود ندارد.')
        
        # چک انقضای سطوح
        expired_profiles = NaturalProfile.objects.filter(
            expiration_date__lt=now,
            previous_level__isnull=False
        )
        expired_count = 0
        for profile in expired_profiles:
            profile.level = profile.previous_level
            profile.previous_level = None
            profile.expiration_date = None
            profile.save(update_fields=['level', 'previous_level', 'expiration_date'])
            expired_count += 1
            self.stdout.write(f'سطح {profile} به {profile.level} برگردانده شد.')
        
        self.stdout.write(f'تمدید خودکار: {renewed_count}، انقضا: {expired_count}')