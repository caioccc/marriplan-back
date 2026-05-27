from app.models import (
    ChecklistTask,
    Gift,
    Guest,
    UserWeddingProfile,
    WeddingIdentity,
    WeddingSupplier,
)


FIRST_STEPS_KEYS = (
    'identity',
    'wedding_details',
    'checklist',
    'guests',
    'suppliers',
    'gifts',
)


def _has_completed_identity(profile: UserWeddingProfile) -> bool:
    identity = WeddingIdentity.objects.filter(wedding_profile=profile).first()
    if not identity:
        return False

    return bool(
        identity.selected_style
        and identity.wedding_size
        and identity.dress_code
        and identity.palette
    )


def _has_completed_wedding_details(profile: UserWeddingProfile) -> bool:
    return bool(profile.local and profile.data_casamento)


def build_first_steps_menu_state(user):
    profile, _ = UserWeddingProfile.objects.get_or_create(user=user)

    if getattr(user, 'first_steps', False):
        return {
            'first_steps': True,
            'items': {
                'identity': True,
                'wedding_details': True,
                'checklist': True,
                'guests': True,
                'suppliers': True,
                'gifts': True,
            },
            'done_count': len(FIRST_STEPS_KEYS),
            'total_count': len(FIRST_STEPS_KEYS),
            'pending_count': 0,
        }

    identity_done = _has_completed_identity(profile)
    wedding_details_done = _has_completed_wedding_details(profile)
    checklist_done = ChecklistTask.objects.filter(user=user, status='done').exists()
    guests_done = Guest.objects.filter(user=user).exists()
    suppliers_done = WeddingSupplier.objects.filter(wedding=profile).exists()
    gifts_done = Gift.objects.filter(wedding_profile=profile).exists()

    items = {
        'identity': identity_done,
        'wedding_details': wedding_details_done,
        'checklist': checklist_done,
        'guests': guests_done,
        'suppliers': suppliers_done,
        'gifts': gifts_done,
    }
    done_count = sum(1 for key in FIRST_STEPS_KEYS if items[key])
    total_count = len(FIRST_STEPS_KEYS)
    first_steps_completed = done_count == total_count

    if first_steps_completed and not getattr(user, 'first_steps', False):
        user.first_steps = True
        user.save(update_fields=['first_steps'])

    return {
        'first_steps': first_steps_completed,
        'items': items,
        'done_count': done_count,
        'total_count': total_count,
        'pending_count': total_count - done_count,
    }
