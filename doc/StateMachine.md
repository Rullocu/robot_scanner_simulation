# State Machine

## INIT
- **Action:** none
- **Transition:** → `PREPARE_ITEM`

---

## PREPARE_ITEM
- **Action:** call `/item/spawn` (`SpawnItem.srv`)
- **Transition:**
  - `success == true` → `PICK_ITEM`
  - `success == false` → `ERROR_RECOVERY`

---

## PICK_ITEM
- **Action:** call `/robot/pick_and_place` (`MoveRobot.srv`, source=`RED_TOTE`, dest=`SCAN_TABLE`)
- **Transition:**
  - `success == true` → `VERIFY_ITEM_ON_TABLE`
  - `success == false` → `ERROR_RECOVERY`

---

## VERIFY_ITEM_ON_TABLE
- **Action:** read `/scan_table/occupancy` topic (`TableOccupancy.msg`)
- **Transition:**
  - `occupied == true` → `SCAN_ITEM`
  - `occupied == false` → `ERROR_RECOVERY`

---

## SCAN_ITEM
- **Action:** call `/scanner/trigger` (`TriggerScan.srv`)
- **Transition:**
  - `success == true` → `ITEM_MANAGEMENT`
  - `success == false` → `ERROR_RECOVERY`

---

## ITEM_MANAGEMENT
- **Action:**
  - Deduplicate barcodes by `barcode_id`
  - Update `item_library` map `<string, uint32>` (`barcode_id` → count)
  - Log barcodes
- **Transition:**
  - All `barcode_id`s differ or `barcodes.size() == 0` → `CLEAN_SCAN_TABLE`
  - `barcode_id`s are identical → `PUSH_ITEM_TO_POCKET`

---

## PUSH_ITEM_TO_POCKET
- **Action:** call `/pusher/push` (`Push.srv`, direction=`POCKET`)
- **Transition:**
  - `success == true` → `CHECK_TABLE_OCCUPIED`
  - `success == false` → `ERROR_RECOVERY`

---

## CHECK_TABLE_OCCUPIED
- **Action:** read `/scan_table/occupancy` topic (`TableOccupancy.msg`)
- **Transition:**
  - `occupied == true` → `CLEAN_SCAN_TABLE`
  - `occupied == false` → `RECOVER_ROBOT`

---

## CLEAN_SCAN_TABLE
- **Action:** call `/pusher/push` (`Push.srv`, direction=`REJECT`)
- **Transition:**
  - `success == true` → `RECOVER_ROBOT`
  - `success == false` → `ERROR_RECOVERY`

---

## RECOVER_ROBOT
- **Action:** call `/robot/pick_and_place` (`MoveRobot.srv`, source=`SCAN_TABLE`, dest=`RED_TOTE`)
- **Transition:**
  - `success == true` → `PREPARE_ITEM`
  - `success == false` → `ERROR_RECOVERY`

---

## ERROR_RECOVERY
- **Action:**
  - `log_error("manual intervention required")`
  - `sleep(2 seconds)`
- **Transition:** → `PREPARE_ITEM`
