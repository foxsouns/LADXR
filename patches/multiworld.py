from assembler import ASM
from roomEditor import RoomEditor
import entityData


def addMultiworldShop(rom):
    # Make a copy of the shop into GrandpaUlrira house
    shop_room = RoomEditor(rom, 0x2A1)
    re = RoomEditor(rom, 0x2A9)
    re.objects = [obj for obj in shop_room.objects if obj.x is not None and obj.type_id != 0xCE] + re.getWarps()
    re.entities = [(1, 6, 0x77), (2, 6, 0x77)]
    re.animation_id = shop_room.animation_id
    re.floor_object = shop_room.floor_object
    re.store(rom)
    # Fix the tileset
    rom.banks[0x20][0x2EB3 + 0x2A9 - 0x100] = rom.banks[0x20][0x2EB3 + 0x2A1 - 0x100]

    # Load the shopkeeper sprites instead of Grandpa sprites
    entityData.SPRITE_DATA[0x77] = entityData.SPRITE_DATA[0x4D]

    labels = {}
    rom.patch(0x06, 0x2860, "00" * 0x215, ASM("""
shopItemsHandler:
; Render the shop items
    ld   h, $00
loop:
    ; First load links position to render the item at
    ldh  a, [$98] ; LinkX
    ldh  [$EE], a ; X
    ldh  a, [$99] ; LinkY
    sub  $0E
    ldh  [$EC], a ; Y
    ; Check if this is the item we have picked up
    ld   a, [$C509] ; picked up item in shop
    dec  a
    cp   h
    jr   z, .renderCarry

    ld   a, h
    swap a
    add  a, $20
    ldh  [$EE], a ; X
    ld   a, $30
    ldh  [$EC], a ; Y
.renderCarry:
    ld   a, h
    push hl
    ldh  [$F1], a ; variant
    cp   $03
    jr   nc, .singleSprite
    ld   de, ItemsDualSpriteData
    call $3BC0 ; render sprite pair
    jr   .renderDone
.singleSprite:
    ld   de, ItemsSingleSpriteData
    call $3C77 ; render sprite
.renderDone:

    pop  hl
.skipItem:
    inc  h
    ld   a, $07
    cp   h
    jr   nz, loop

;   check if we want to pickup or drop an item
    ldh  a, [$CC]
    and  $30 ; A or B button
    call nz, checkForPickup

;   check if we have an item
    ld   a, [$C509] ; carry item
    and  a
    ret  z

    ; Set that link has picked something up
    ld   a, $01
    ld   [$C15C], a
    call $0CAF ; reset spin attack...

    ; Check if we are trying to exit the shop and so drop our item.
    ldh  a, [$99]
    cp   $78
    ret  c
    xor  a
    ld   [$C509], a

    ret

checkForPickup:
    ldh  a, [$9E] ; direction
    cp   $02
    ret  nz
    ldh  a, [$99] ; LinkY
    cp   $48
    ret  nc

    ld   a, $13
    ldh  [$F2], a ; play SFX

    ld   a, [$C509] ; picked up shop item
    and  a
    jr   nz, .drop

    ldh  a, [$98] ; LinkX
    sub  $08
    swap a
    and  $07
    ld   [$C509], a ; picked up shop item
    ret
.drop:
    xor  a
    ld   [$C509], a
    ret

ItemsDualSpriteData:
    db   $60, $08, $60, $28 ; zol
    db   $68, $09 ; chicken (left)
ItemsSingleSpriteData: ; (first 3 entries are still dual sprites)
    db   $6A, $09 ; chicken (right)
    db   $14, $02, $14, $22 ; piece of power
;Real single sprite data starts here
    db   $00, $0F ; bomb
    db   $38, $0A ; rupees
    db   $20, $0C ; medicine
    db   $28, $0C ; heart

;------------------------------------trying to buy something starts here
talkHandler:
    ld   a, [$C509] ; carry item
    add  a, a
    ret  z ; check if we have something to buy
    sub  $02

    ld   hl, itemNames
    ld   e, a
    ld   d, b ; b=0
    add  hl, de
    ld   e, [hl]
    inc  hl
    ld   d, [hl]

    ld   hl, wCustomMessage
    call appendString
    dec  hl
    call padString
    ld   de, postMessage
    call appendString
    dec  hl
    ld   a, $fe
    ld   [hl], a
    ld   de, $FFEF
    add  hl, de
    ldh  a, [$EE]
    swap a
    and  $0F
    add  a, $30
    ld   [hl], a
    ld   a, $C9
    call $2385 ; open dialog
    call $3B12 ; increase entity state
    ret

appendString:
    ld   a, [de]
    inc  de
    and  a
    ret  z
    ldi  [hl], a
    jr   appendString

padString:
    ld   a, l
    and  $0F
    ret  z
    ld   a, $20
    ldi  [hl], a
    jr   padString

itemNames:
    dw itemZol
    dw itemChicken
    dw itemPieceOfPower
    dw itemBombs
    dw itemRupees
    dw itemMedicine
    dw itemHealth

postMessage:
    db  "For player X?       Yes  No  ", $00

itemZol:
    db  m"Slime storm|100 {RUPEES}", $00
itemChicken:
    db  m"Coccu party|50 {RUPEES}", $00
itemPieceOfPower:
    db  m"Piece of Power|50 {RUPEES}", $00
itemBombs:
    db  m"20 Bombs|50 {RUPEES}", $00
itemRupees:
    db  m"100 {RUPEES}|200 {RUPEES}", $00
itemMedicine:
    db  m"Medicine|100 {RUPEES}", $00
itemHealth:
    db  m"Health refill|10 {RUPEES}", $00

TalkResultHandler:
    ld  hl, ItemPriceTableBCD
    ld  a, [$C509]
    dec a
    add a, a
    ld  c, a ; b=0
    add hl, bc
    ldi a, [hl]
    ld  d, [hl]
    ld  e, a
    ld  a, [$DB5D]
    cp  d
    ret c
    jr  nz, .highEnough
    ld  a, [$DB5E]
    cp  e
    ret c
.highEnough:
    ; Got enough money, take it.
    ld  hl, ItemPriceTableDEC
    ld  a, [$C509]
    dec a
    ld  c, a ; b=0
    add hl, bc
    ld  a, [hl]
    ld  [$DB92], a

    ; No longer picked up item
    xor a
    ld  [$C509], a
    ret

ItemPriceTableBCD:
    dw $0100, $0050, $0050, $0050, $0200, $0100, $0010
ItemPriceTableDEC:
    db $64, $32, $32, $32, $C8, $64, $0A

""", 0x6860, labels), fill_nop=True)

    # Patch GrandpaUlrira to work as a multiworld shop
    rom.patch(0x06, 0x1C0E, 0x1C89, ASM("""
    ld   a, $01
    ld   [$C50A], a ; this stops link from using items

;Draw shopkeeper
    ld   de, OwnerSpriteData
    call $3BC0 ; render sprite pair
    ldh  a, [$E7] ; frame counter
    swap a
    and  $01
    call $3B0C ; set sprite variant

    ldh  a, [$F0]
    and  a
    jr   nz, checkTalkingResult

    call $641A ; prevent link from moving into the sprite
    call $645D ; check if talking to NPC
    call c, ${TALKHANDLER:04x} ; talk handling

    ldh  a, [$EE] ; X
    cp   $18
    ret  nz

    ; Jump to other code which is placed on the old owl code. As we do not have enough space here.
    jp   ${SHOPITEMSHANDLER:04x}

checkTalkingResult:
    ld   a, [$C19F]
    and  a
    ret  nz ; still taking
    call $3B12 ; increase entity state
    ld   [hl], $00
    ld   a, [$C177] ; dialog selection
    and  a
    ret  nz
    jp ${TALKRESULTHANDLER:04x}

OwnerSpriteData:
    ;db   $60, $03, $62, $03, $62, $23, $60, $23 ; down
    db   $64, $03, $66, $03, $66, $23, $64, $23 ; up
    ;db   $68, $03, $6A, $03, $6C, $03, $6E, $03 ; left
    ;db   $6A, $23, $68, $23, $6E, $23, $6C, $23 ; right
    """.format(**labels), 0x5C0E), fill_nop=True)

