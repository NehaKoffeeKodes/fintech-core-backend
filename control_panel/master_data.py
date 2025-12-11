from master_data.models import GlobalBillerGroup, GlobalOperator
from tenant_app.models import BillerGroup, OperatorList, HierarchyLevel, DefaultChargeHead

def seed_initial_master_data(target_db):
    for cat in GlobalBillerGroup.objects.filter(active=True):
        BillerGroup.objects.using(target_db).get_or_create(
            name=cat.group_name,
            defaults={'is_disabled': True}
        )

    for op in GlobalOperator.objects.filter(active=True):
        OperatorList.objects.using(target_db).get_or_create(
            operator_name=op.operator_name,
            op_code=op.op_code,
            defaults={'is_disabled': True, 'service_type': op.service_type}
        )

    levels = [
        {"title": "SUPER DISTRIBUTOR", "code": "SD", "parent": None, "active": True},
        {"title": "MASTER DISTRIBUTOR", "code": "MD", "parent": 1, "active": True},
        {"title": "DISTRIBUTOR", "code": "DT", "parent": 2, "active": False},
    ]
    for lvl in levels:
        HierarchyLevel.objects.using(target_db).update_or_create(
            title=lvl["title"],
            defaults={
                "description": lvl["title"],
                "prefix": lvl["code"],
                "parent_id": lvl["parent"],
                "is_active": lvl["active"]
            }
        )

    if not DefaultChargeHead.objects.exists():
        charges = ['instant_transfer_fee', 'wallet_to_bank_fee', 'dmt_charges']
        for name in charges:
            DefaultChargeHead.objects.get_or_create(name=name)