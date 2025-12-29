
from maspy import Admin, Percept, Any
import pygame 
import sys 
import os

os.environ['SDL_VIDEO_CENTERED'] = '1'

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
SIDEBAR_WIDTH = 200
AGENT_COLOR = (0, 100, 255)
TARGET_COLOR = (255, 50, 50)
BG_COLOR = (240, 240, 240)
GRID_COLOR = (200, 200, 200)
BUTTON_COLOR = (80, 80, 200)
BUTTON_HOVER = (100, 100, 250)
TEXT_COLOR = (255, 255, 255)
SIDEBAR_WIDTH = 200

pygame.init()
FONT = pygame.font.SysFont(None, 24)

class Button:
    def __init__(self, rect, text, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.hover = False

    def draw(self, screen):
        color = BUTTON_HOVER if self.hover else BUTTON_COLOR
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        text_surf = FONT.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.hover:
            self.callback()

class TextInput:
    def __init__(self, rect, label, default=""):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.placeholder = default
        self.text = default
        self.active = False
        self.cleared = False   # important
        self.active = False

    def draw(self, screen):
        color = (180, 180, 180) if not self.cleared else (255, 255, 255)
        pygame.draw.rect(screen, (70, 70, 70), self.rect, border_radius=5)
        if self.active:
            pygame.draw.rect(screen, (150, 150, 250), self.rect, 2)
        else:
            pygame.draw.rect(screen, (120, 120, 120), self.rect, 2)
        txt_surface = FONT.render(self.text, True, color)
        #txt_surface = FONT.render(self.text, True, TEXT_COLOR)
        label_surface = FONT.render(self.label, True, TEXT_COLOR)
        screen.blit(label_surface, (self.rect.x - 120, self.rect.y + 5))
        screen.blit(txt_surface, (self.rect.x + 10, self.rect.y + 5))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
                if not self.cleared:
                    self.text = ""
                    self.cleared = True
            else:
                self.active = False
                if self.text == "":
                    self.text = self.placeholder
                    self.cleared = False
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            else:
                self.text += event.unicode
        # if event.type == pygame.MOUSEBUTTONDOWN:
        #     self.active = self.rect.collidepoint(event.pos)
        # if event.type == pygame.KEYDOWN and self.active:
        #     if event.key == pygame.K_RETURN:
        #         self.active = False
        #     elif event.key == pygame.K_BACKSPACE:
        #         self.text = self.text[:-1]
        #     elif event.unicode.isdigit():
        #         self.text += event.unicode

class MapVisualizer:
    def __init__(self, env) -> None:
        pygame.init()
        self.env = env
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

        self.map_area_width = WINDOW_WIDTH - SIDEBAR_WIDTH
        self.map_area_height = WINDOW_HEIGHT
        self.cell_size = min(
            self.map_area_width // env.map_size[0],
            self.map_area_height // env.map_size[1],
        )
        pygame.display.set_caption("Map Environment")
        self.clock = pygame.time.Clock()
        self.buttons: list[Button] = self._create_buttons()
    
    def _create_buttons(self):
        buttons = []
        x = self.env.map_size[0]*self.cell_size + 20
        y = 40
        spacing = 60
        actions = [self.action_1, self.action_2, self.action_3, self.action_4]
        names = ["Pause/Resume", "More Delay", "Less Delay", "Reset"]
        for i, func in enumerate(actions):
            btn = Button(
                rect=(x, y + i*spacing, SIDEBAR_WIDTH-40, 40),
                text= names[i],
                callback=func
            )
            buttons.append(btn)
        return buttons

    def action_1(self): Admin().pause_system()
    def action_2(self): Admin().slower_cycle()
    def action_3(self): Admin().faster_cycle()
    def action_4(self): Admin()._models[0].reset_percepts()
    def action_5(self): print("Action 5 triggered")
    def action_6(self): print("Action 6 triggered")
    
    def draw_sidebar(self):
        sidebar_rect = pygame.Rect(self.env.map_size[0]*self.cell_size, 0, SIDEBAR_WIDTH, self.env.map_size[1]*self.cell_size)
        pygame.draw.rect(self.screen, (30, 30, 60), sidebar_rect)
        for btn in self.buttons:
            btn.draw(self.screen)
    
    def draw_map(self):
        # grid
        for x in range(0, self.env.map_size[0]*self.cell_size, self.cell_size):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, self.env.map_size[1]*self.cell_size))
        for y in range(0, self.env.map_size[1]*self.cell_size, self.cell_size):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (self.env.map_size[0]*self.cell_size, y))

        # draw target
        target = self.env.get(Percept("target", (Any, Any)))
        if target:
            tx, ty = target.values
            cx, cy = tx * self.cell_size, ty * self.cell_size
            pygame.draw.line(self.screen, TARGET_COLOR,
                            (cx + 4, cy + 4),
                            (cx + self.cell_size - 4, cy + self.cell_size - 4), 3)
            pygame.draw.line(self.screen, TARGET_COLOR,
                            (cx + self.cell_size - 4, cy + 4),
                            (cx + 4, cy + self.cell_size - 4), 3)
            
        # draw walls
        walls = self.env.get(Percept("wall", (Any, Any)), all=True)
        if not walls: walls = []
        for wall in walls:
            rect = pygame.Rect(wall.values[0] * self.cell_size, wall.values[1] * self.cell_size, self.cell_size, self.cell_size)
            pygame.draw.rect(self.screen, (0, 0, 0), rect)

        # draw agents
        for percept in self.env.get(Percept("agt_position", (Any, Any)), all=True):
            x, y = percept.values
            cx = x * self.cell_size + self.cell_size // 2
            cy = y * self.cell_size + self.cell_size // 2
            body = self.cell_size // 4

            # body
            pygame.draw.rect(self.screen, AGENT_COLOR,
                             (cx - body//2, cy - body//2, body, body))
            # body id
            agent_id = percept.group.split("_")[-1]
            font = pygame.font.SysFont(None, body)
            text = font.render(agent_id, True, (255, 255, 255))  # black text
            text_rect = text.get_rect(center=(cx, cy))

            self.screen.blit(text, text_rect)

            # legs
            leg_len = self.cell_size // 3
            # body bottom corners/sides
            bottom_left  = (cx - body//2, cy + body//2)
            bottom_right = (cx + body//2, cy + body//2)

            # left leg (angled left-down)
            pygame.draw.line(self.screen, AGENT_COLOR,
                            bottom_left,
                            (bottom_left[0] - leg_len//2, bottom_left[1] + leg_len), 2)

            # left-mid leg (straight down)
            pygame.draw.line(self.screen, AGENT_COLOR,
                            (cx - body//4, cy + body//2),
                            (cx - body//4, cy + body//2 + leg_len), 2)

            # right-mid leg (straight down)
            pygame.draw.line(self.screen, AGENT_COLOR,
                            (cx + body//4, cy + body//2),
                            (cx + body//4, cy + body//2 + leg_len), 2)

            # right leg (angled right-down)
            pygame.draw.line(self.screen, AGENT_COLOR,
                            bottom_right,
                            (bottom_right[0] + leg_len//2, bottom_right[1] + leg_len), 2)

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.draw_map()
        self.draw_sidebar()
        pygame.display.flip()
        
    def loop(self):
        running = True
        while running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    for btn in self.buttons:
                        btn.handle_event(event)
            except Exception as e:
                print(e)
                sys.exit()
            
            self.draw()
            
            pygame.time.delay(10)
            self.clock.tick(30) 
            
        pygame.quit()
        
class MenuScreen:
    def __init__(self):
        self.screen = pygame.display.set_mode((500, 400))
        pygame.display.set_caption("Simulation Setup")
        self.clock = pygame.time.Clock()
        self.inputs = [
            TextInput((200, 60, 100, 25), "Map Width:", "10"),
            TextInput((200, 100, 100, 25), "Map Height:", "10"),
            TextInput((200, 140, 100, 25), "Walls %:", "20"),
            TextInput((200, 200, 100, 25), "Agents:", "6"),
            TextInput((200, 240, 100, 25), "Episodes:", "2000")
        ]
        self.start_button = Button((175, 300, 150, 50), "Start Simulation", self.start)
        self.done = False
        self.settings = None

    def start(self):
        try:
            width = int(self.inputs[0].text)
            height = int(self.inputs[1].text)
            walls_perc = float(self.inputs[2].text)/100
            agents = int(self.inputs[3].text)
            episodes = int(self.inputs[4].text)
            self.settings = ((width, height), walls_perc, agents, episodes)
            self.done = True
        except ValueError:
            print("Invalid input")

    def loop(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.start_button.handle_event(event)
                for inp in self.inputs:
                    inp.handle_event(event)

            self.screen.fill((20, 20, 50))
            for inp in self.inputs:
                inp.draw(self.screen)
            self.start_button.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(30)
        return self.settings
