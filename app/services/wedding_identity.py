from app.models import WeddingIdentity


def get_wedding_identity(profile):
    return WeddingIdentity.objects.filter(wedding_profile=profile).first()


def upsert_wedding_identity(profile, validated_data):
    identity, created = WeddingIdentity.objects.get_or_create(wedding_profile=profile)

    for field_name in ('selected_style', 'wedding_size', 'dress_code', 'palette'):
        if field_name in validated_data:
            setattr(identity, field_name, validated_data[field_name])

    identity.save()
    return identity, created


def delete_wedding_identity(profile):
    identity = get_wedding_identity(profile)
    if identity:
        identity.delete()
        return True
    return False
