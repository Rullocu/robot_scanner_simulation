uint8 state                # current state enum value (0=INIT … 10=ERROR_RECOVERY)
string state_name          # human-readable, e.g. "SCAN_ITEM"
string last_transition     # e.g. "PICK_ITEM -> VERIFY_ITEM_ON_TABLE"
string transition_reason   # e.g. "MoveRobot success"
uint8 current_item_id
uint32 item_library_size   # total unique barcode IDs accumulated so far
