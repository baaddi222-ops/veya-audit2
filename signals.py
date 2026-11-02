"""
Profile auto-creation on user signup — the Django equivalent of the
Postgres SECURITY DEFINER trigger from ADR-0009.

Properties:
  - Runs in the SAME transaction as the User creation, so a User cannot
    exist without a Profile + PrivacySettings row.
  - Placeholder username is `user_<8 hex>` derived from the user's UUID,
    never from the email. On the (astronomically unlikely) collision it is
    re-rolled from a fresh random hex string — still `user_<8 hex>`, so
    Profile.has_placeholder_username keeps recognising it.
  - Each attempt runs in its OWN savepoint. (The first version wrapped the
    whole retry loop in one atomic block: after an IntegrityError that block
    is marked broken, so every retry would have raised
    TransactionManagementError instead of retrying.)
"""
import uuid

from django.db import IntegrityError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User

MAX_USERNAME_ATTEMPTS = 5


def _placeholder_username(hex_seed: str) -> str:
    return f'user_{hex_seed[:8]}'


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance: User, created: bool, **kwargs):
    if not created:
        return

    from profiles.models import PrivacySettings, Profile  # local import: app-loading order

    profile = None
    for attempt in range(MAX_USERNAME_ATTEMPTS):
        seed = instance.id.hex if attempt == 0 else uuid.uuid4().hex
        try:
            with transaction.atomic():  # savepoint per attempt
                profile = Profile.objects.create(user=instance, username=_placeholder_username(seed))
            break
        except IntegrityError:
            if attempt == MAX_USERNAME_ATTEMPTS - 1:
                raise
    PrivacySettings.objects.create(profile=profile)
