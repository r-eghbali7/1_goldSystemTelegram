from django.db.models.signals import post_save
from django.dispatch import receiver
from decouple import config
from .models import User

@receiver(post_save, sender=User)
def notify_admin_on_new_user(sender, instance, created, **kwargs):
    if created:
        admin_chat_id = config('ADMIN_TELEGRAM_CHAT_ID')
        text = f"🚨 کاربر جدید ثبت نام کرد:\nشماره: {instance.phone_number}\nشناسه: {instance.id}"
        # TODO: Trigger celery task to send telegram message