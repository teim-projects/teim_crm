from crmapp.models import Branch
from new_inventory.models import Site

def get_destination_queryset(dest_type: str):
    if dest_type == "HO":
        return Branch.objects.filter(is_head_office=True)
    elif dest_type == "BRANCH":
        return Branch.objects.filter(is_head_office=False)
    elif dest_type == "SITE":
        return Site.objects.all()
    return Branch.objects.none()
