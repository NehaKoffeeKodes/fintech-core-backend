from admin_hub.models import*
from control_panel.models import *

def master_data(db_name):
    for old_cat in SaBillerGroup.objects.filter(is_deleted=False):
        BillerGroup.objects.using(db_name).get_or_create(
            name=old_cat.ss_name,
            defaults={'is_active': False}
        )

    for old_op in SaGlobalOperator.objects.filter(is_deleted=False):
        OperatorList.objects.using(db_name).get_or_create(
            operator_name=old_op.ss_name,
            op_code=old_op.operator_code,
            defaults={
                'operator_type': old_op.operator_type,
                'is_active': False
            }
        )

    levels = [
        {"title": "SUPER DISTRIBUTOR", "code": "SD", "parent": None, "active": True},
        {"title": "MASTER DISTRIBUTOR", "code": "MD", "parent": 1, "active": True},
        {"title": "DISTRIBUTOR", "code": "DT", "parent": 2, "active": False},
    ]

    for item in levels:
        HierarchyLevel.objects.using(db_name).update_or_create(
            title=item["title"],
            defaults={
                "description": item["title"],
                "prefix": item["code"],
                "parent_id": item["parent"],
                "is_active": item["active"]
            }
        )

    default_charges = ['instant_transfer_fee', 'bank_transfer_fee']

    for charge_name in default_charges:
        SaOperatorCharge.objects.get_or_create(
            name=charge_name,
            defaults={'is_active': True}
        )

    print(f"Seed data successfully added in database: {db_name}")