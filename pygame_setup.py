import pygame
from config import logging

pygame.init()
display_info = pygame.display.Info()
native_width = display_info.current_w
native_height = display_info.current_h
screen = pygame.display.set_mode((native_width, native_height), pygame.RESIZABLE)
fullscreen = False
clock = pygame.time.Clock()
pygame.display.set_caption("Multiplayer Börsenspiel")
pygame.font.init()

# Background image
try:
    background_image = pygame.image.load("background.jpg")
except pygame.error:
    logging.error("Hintergrundbild konnte nicht geladen werden.")
    print("Hintergrundbild konnte nicht geladen werden.")
    background_image = None