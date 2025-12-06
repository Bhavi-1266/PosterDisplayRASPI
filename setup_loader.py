#!/usr/bin/env python3
"""
setup_loader.py
Shows fullscreen loader and installs:
    - python3-pygame
    - python3-pil
"""

import os, sys, time, subprocess
from pathlib import Path

try:
    import pygame
except Exception:
    pygame = None

REQUIRED_APT_PKGS = ["python3-pygame", "python3-pil"]
BG=(10,10,10); WHITE=(240,240,240); RED=(220,80,80); YELLOW=(240,200,60)

BASE = Path("/home/eposter")

def run_cmd(cmd):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout
    except Exception as e:
        return 1, str(e)

def apt_install():
    if os.geteuid() != 0:
        cmds = [["sudo","apt","update","-y"], ["sudo","apt","install","-y"]+REQUIRED_APT_PKGS]
    else:
        cmds = [["apt","update","-y"], ["apt","install","-y"]+REQUIRED_APT_PKGS]
    for c in cmds:
        rc,out = run_cmd(c)
        if rc!=0:
            return False, out[-200:]
    return True, "installed"

def show(screen, lines, font, color):
    screen.fill(BG)
    w,h = screen.get_size()
    y=(h - sum(font.size(x)[1]+10 for x in lines))//2
    for line in lines:
        surf = font.render(line, True, color)
        screen.blit(surf, ((w-surf.get_width())//2, y))
        y+=surf.get_height()+10
    pygame.display.flip()

def do_ui_setup():
    if pygame is None:
        return apt_install()

    pygame.init()
    scr = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    font = pygame.font.SysFont("Arial",48)

    show(scr, ["Preparing setup…","Installing system packages…"], font, YELLOW)
    pygame.event.pump()
    time.sleep(0.5)

    ok,msg = apt_install()
    if not ok:
        show(scr, ["ERROR LOADING","",msg], font, RED)
        while True:
            for e in pygame.event.get():
                if e.type==pygame.KEYDOWN: pygame.quit(); return False,msg
            time.sleep(0.1)

    show(scr, ["Setup complete.","You may run launcher now."], font, WHITE)
    time.sleep(1)
    pygame.quit()
    return True, "installed"

def main():
    ok,msg = do_ui_setup()
    if not ok:
        print("Setup failed:", msg)
        return 1
    print("Setup OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())

