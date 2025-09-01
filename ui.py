import pygame
from config import colors
from pygame_setup import screen

def draw_text(text, font, color, x, y):
    lines = text.split('\n')
    for i, line in enumerate(lines):
        render = font.render(line, True, color)
        screen.blit(render, (x, y + i * font.get_height()))

class Button:
    def __init__(self, text, x, y, color, width=200, height=50, hover=False, pressed=False):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.width = width
        self.height = height
        self.hover = hover
        self.pressed = pressed
        self.font = pygame.font.Font(None, 36)
    
    def draw(self):
        button_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        button_color = colors["LIGHT_GRAY"] if self.hover else (colors["GRAY"] if self.pressed else self.color)
        pygame.draw.rect(screen, button_color, button_rect, border_radius=15)
        text_surface = self.font.render(self.text, True, colors["WHITE"])
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)
        return button_rect

def draw_input_box(x, y, text, active):
    font = pygame.font.Font(None, 36)
    input_box_rect = pygame.Rect(x, y, 200, 50)
    color = colors["SELECTED_COLOR"] if active else colors["BLACK"]
    pygame.draw.rect(screen, color, input_box_rect, 2, border_radius=5)
    draw_text(text, font, colors["BLACK"], x + 10, y + 10)
    return input_box_rect

def draw_stock_label(text, x, y, selected):
    font = pygame.font.Font(None, 36)
    color = colors["SELECTED_COLOR"] if selected else colors["BLACK"]
    text_surface = font.render(text, True, color)
    label_rect = text_surface.get_rect(topleft=(x, y))
    screen.blit(text_surface, label_rect)
    return label_rect