import json
from django.conf import settings

def super_admin_action_label(action: str,txn_ref: str = None,entry_type: str = None,amount: float = 0.0,wallet: str = None,note: str = None,extra: str = None) -> str:
    try:
        with open(settings.ADMIN_LABEL_TEMPLATE_PATH, 'r', encoding='utf-8') as file:
            templates = json.load(file)
    except:
        templates = {"super_admin_action": "[{action}] {trn_detail}{effective_type} ₹{amount} | {effective_wallet}{description}{effectvie_label}"}

    template = templates.get("super_admin_action", "[ACTION] {trn_detail}{effective_type} ₹{amount}")
    
    trn_part = f" | Txn: {txn_ref}" if txn_ref else ""
    type_part = f" ({entry_type})" if entry_type else ""
    wallet_part = f" → {wallet.upper()}" if wallet else ""
    note_part = f" | Note: {note}" if note else ""
    extra_part = f" {extra}" if extra else ""

    final_label = template.format(
        action=action,
        trn_detail=trn_part,
        effective_type=type_part,
        amount=f"{amount:,.2f}",
        effective_wallet=wallet_part,
        description=note_part,
        effectvie_label=extra_part
    )

    return final_label.strip()