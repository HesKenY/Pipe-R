"""
Pokemon Crystal tick — capture mGBA window + OCR game state.
"""
import json, sys, tempfile, ctypes
from ctypes import wintypes
from pathlib import Path
from datetime import datetime, timezone
try:
    import pyautogui
except:
    sys.exit(2)
from PIL import Image, ImageChops

pyautogui.FAILSAFE = False
PREV = Path(tempfile.gettempdir()) / "_pokemon_prev.png"

def find_mgba():
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, None)
    while hwnd:
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "mGBA" in title or "mgba" in title or "Pokemon" in title or "Crystal" in title:
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    if rect.right - rect.left > 100:
                        return (rect.left, rect.top, rect.right, rect.bottom)
        hwnd = user32.GetWindow(hwnd, 2)
    return None

def motion(cur):
    if not PREV.exists():
        cur.save(str(PREV)); return 0.0
    try:
        prev = Image.open(str(PREV)).resize((64,64)).convert("L")
        diff = ImageChops.difference(cur.resize((64,64)).convert("L"), prev)
        m = sum(diff.getdata()) / (64*64*255.0)
        cur.save(str(PREV)); return round(m, 4)
    except:
        cur.save(str(PREV)); return 0.0

def ocr_region(img, box):
    try:
        import pytesseract
        return pytesseract.image_to_string(img.crop(box), config="--psm 7").strip()[:120]
    except:
        return ""

def classify(m, bright, texts):
    t = " ".join(texts).lower()
    if any(w in t for w in ["fainted", "black out", "whited out"]):
        return "death"
    if any(w in t for w in ["wild", "trainer", "used", "effective", "foe"]):
        return "battle"
    if any(w in t for w in ["new game", "continue", "options"]):
        return "menu"
    if m > 0.03: return "exploring"
    if m < 0.005: return "idle"
    return "dialogue"

def main():
    rect = find_mgba()
    if rect:
        l,t,r,b = rect
        shot = pyautogui.screenshot(region=(l,t,r-l,b-t))
        found = True
    else:
        shot = pyautogui.screenshot()
        found = False
    w, h = shot.size
    m = motion(shot)
    bright = round(sum(shot.resize((32,32)).convert("L").getdata())/(32*32*255.0), 3)
    # GBC screen regions (mGBA renders the 160x144 game screen scaled)
    top = ocr_region(shot, (0, 0, w, int(h*0.15)))
    mid = ocr_region(shot, (0, int(h*0.3), w, int(h*0.7)))
    bot = ocr_region(shot, (0, int(h*0.75), w, h))
    activity = classify(m, bright, [top, mid, bot])
    print(json.dumps({
        "at": datetime.now(timezone.utc).isoformat(),
        "w": w, "h": h,
        "top": top, "mid": mid, "bot": bot,
        "motion": m, "bright": bright,
        "activity": activity, "foundWindow": found
    }))

if __name__ == "__main__": main()
