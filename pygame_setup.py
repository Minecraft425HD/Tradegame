import pygame
import os
from config import logging, get_path

pygame.init()
display_info = pygame.display.Info()
native_width = display_info.current_w
native_height = display_info.current_h
screen = pygame.display.set_mode((native_width, native_height), pygame.RESIZABLE)
fullscreen = False
clock = pygame.time.Clock()
pygame.display.set_caption("Multiplayer Börsenspiel")
pygame.font.init()

# Background image (cross-platform path)
try:
    background_path = get_path("background.jpg")
    if os.path.exists(background_path):
        background_image = pygame.image.load(background_path)
        logging.info(f"Hintergrundbild geladen: {background_path}")
    else:
        logging.warning(f"Hintergrundbild nicht gefunden: {background_path}")
        background_image = None
except pygame.error as e:
    logging.error(f"Hintergrundbild konnte nicht geladen werden: {e}")
    print(f"Hintergrundbild konnte nicht geladen werden: {e}")
    background_image = None
