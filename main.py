import pygame
import random
import math
from enum import Enum
import numpy as np

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tunnel Evacuation Simulation")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
BLUE = (0, 0, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
BROWN = (139, 69, 19)
LIGHT_BLUE = (173, 216, 230)
SMOKE_COLORS = [(50, 50, 50), (70, 70, 70), (90, 90, 90), (110, 110, 110)]

# Agent states
class AgentState(Enum):
    NORMAL = 0
    CONCERNED = 1
    DISORIENTED = 2
    PANICKED = 3
    INJURED = 4
    HELPLESS = 5

# Fire levels
class FireLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

# Exit status
class ExitStatus(Enum):
    ACCESSIBLE = 0
    RESTRICTED = 1
    BLOCKED = 2

class SmokeParticle:
    def __init__(self, x, y, fire_level):
        self.x = x
        self.y = y
        self.size = random.randint(5, 15 if fire_level == FireLevel.HIGH else 10)
        self.speed = random.uniform(0.2, 1.0)
        self.color = random.choice(SMOKE_COLORS)
        self.lifetime = random.randint(50, 150)
        self.alpha = 255
        self.direction = random.uniform(0, 2 * math.pi)
        
    def update(self):
        self.x += math.cos(self.direction) * self.speed
        self.y -= self.speed * 0.5  # Smoke rises
        self.lifetime -= 1
        self.alpha = int(255 * (self.lifetime / 150))
        self.size = max(0, self.size - 0.05)
        
    def draw(self, screen):
        if self.size > 0:
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, self.alpha), (self.size, self.size), self.size)
            screen.blit(s, (int(self.x - self.size), int(self.y - self.size)))

class Agent:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.speed = random.uniform(1.0, 2.0)
        self.state = AgentState.NORMAL
        self.target_x = WIDTH - 50
        self.target_y = HEIGHT // 2
        self.color = GREEN
        self.panic_timer = 0
        self.disorientation_angle = 0
        self.animation_frame = 0
        self.update_state_color()
        
    def update_state_color(self):
        colors = {
            AgentState.NORMAL: (100, 200, 100),
            AgentState.CONCERNED: (200, 200, 100),
            AgentState.DISORIENTED: (200, 150, 50),
            AgentState.PANICKED: (200, 50, 50),
            AgentState.INJURED: (100, 100, 200),
            AgentState.HELPLESS: (200, 200, 200)
        }
        self.color = colors[self.state]
    
    def move(self, exits, fire_zones, vehicles):
        if self.state == AgentState.HELPLESS:
            return  # Can't move
            
        # Find nearest accessible exit
        min_dist = float('inf')
        for exit in exits:
            if exit.status != ExitStatus.BLOCKED:
                dist = math.sqrt((exit.x - self.x)**2 + (exit.y - self.y)**2)
                if dist < min_dist:
                    min_dist = dist
                    self.target_x, self.target_y = exit.x, exit.y
        
        # Calculate direction to target
        dx, dy = self.target_x - self.x, self.target_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0:
            dx, dy = dx/dist, dy/dist
            
            # Modify movement based on state
            speed_mod = {
                AgentState.NORMAL: 1.0,
                AgentState.CONCERNED: 1.2,
                AgentState.DISORIENTED: 0.7,
                AgentState.PANICKED: 2.0,
                AgentState.INJURED: 0.3,
                AgentState.HELPLESS: 0.0
            }[self.state]
            
            if self.state == AgentState.DISORIENTED:
                self.disorientation_angle += random.uniform(-0.5, 0.5)
                dx = math.cos(math.atan2(dy, dx) + self.disorientation_angle)
                dy = math.sin(math.atan2(dy, dx) + self.disorientation_angle)
            elif self.state == AgentState.PANICKED and random.random() < 0.1:
                dx += random.uniform(-0.5, 0.5)
                dy += random.uniform(-0.5, 0.5)
            
            # Check for fire zones
            in_fire = False
            for zone in fire_zones:
                if zone.contains(self.x, self.y):
                    in_fire = True
                    if zone.level == FireLevel.LOW:
                        speed_mod *= 0.9
                        if random.random() < 0.01 and self.state.value < AgentState.CONCERNED.value:
                            self.state = AgentState.CONCERNED
                    elif zone.level == FireLevel.MEDIUM:
                        speed_mod *= 0.7
                        if random.random() < 0.05 and self.state.value < AgentState.DISORIENTED.value:
                            self.state = AgentState.DISORIENTED
                    elif zone.level == FireLevel.HIGH:
                        speed_mod *= 0.3
                        if random.random() < 0.1:
                            self.state = AgentState.PANICKED
                        if random.random() < 0.02:
                            self.state = AgentState.INJURED
                    break
            
            # Check for vehicles (obstacles)
            for vehicle in vehicles:
                if vehicle.contains(self.x + dx * 10, self.y + dy * 10):
                    if random.random() < 0.5:
                        dy += 0.3
                    else:
                        dy -= 0.3
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        dx, dy = dx/dist, dy/dist
                    break
            
            # Update position
            self.x += dx * self.speed * speed_mod
            self.y += dy * self.speed * speed_mod
            
            # Keep within tunnel bounds
            self.y = max(60, min(HEIGHT - 60, self.y))
            
            # State transitions
            if not in_fire and self.state != AgentState.NORMAL and random.random() < 0.005:
                if self.state.value > AgentState.NORMAL.value:
                    self.state = AgentState(self.state.value - 1)
            
            self.update_state_color()
    
    def draw(self, screen):
        self.animation_frame = (self.animation_frame + 0.1) % 10
        
        # Body
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        
        # Head (slightly smaller circle on top)
        head_radius = self.radius * 0.7
        head_color = (min(255, self.color[0] + 40), min(255, self.color[1] + 40), min(255, self.color[2] + 40))
        pygame.draw.circle(screen, head_color, 
                        (int(self.x), int(self.y - self.radius * 0.7)), 
                        int(head_radius))
        
        # State indicators
        if self.state == AgentState.DISORIENTED:
            # Swirling lines around head
            angle = self.animation_frame * 0.6
            for i in range(3):
                start = (self.x + math.cos(angle + i*2.1) * self.radius * 1.3,
                        self.y + math.sin(angle + i*2.1) * self.radius * 1.3)
                end = (self.x + math.cos(angle + i*2.1) * self.radius * 1.6,
                    self.y + math.sin(angle + i*2.1) * self.radius * 1.6)
                pygame.draw.line(screen, WHITE, start, end, 2)
                
        elif self.state == AgentState.PANICKED:
            # Jagged lines around body
            for i in range(6):
                angle = i * math.pi / 3 + self.animation_frame * 0.5
                length = self.radius * (1.3 + math.sin(self.animation_frame * 2 + i) * 0.3)
                end = (self.x + math.cos(angle) * length,
                    self.y + math.sin(angle) * length)
                pygame.draw.line(screen, RED, (self.x, self.y), end, 2)
                
        elif self.state == AgentState.INJURED:
            # Bandage cross
            pygame.draw.line(screen, WHITE, 
                            (self.x - self.radius*0.7, self.y - self.radius*0.7),
                            (self.x + self.radius*0.7, self.y + self.radius*0.7), 2)
            pygame.draw.line(screen, WHITE, 
                            (self.x + self.radius*0.7, self.y - self.radius*0.7),
                            (self.x - self.radius*0.7, self.y + self.radius*0.7), 2)
            
        elif self.state == AgentState.HELPLESS:
            # Collapsed pose
            pygame.draw.line(screen, WHITE, 
                        (self.x, self.y + self.radius*0.5),
                        (self.x, self.y + self.radius*1.5), 3)
            pygame.draw.line(screen, WHITE,
                        (self.x - self.radius*0.7, self.y + self.radius*1.2),
                        (self.x + self.radius*0.7, self.y + self.radius*1.2), 3)

class FireZone:
    def __init__(self, x, y, radius, level):
        self.x = x
        self.y = y
        self.radius = radius
        self.level = level
        self.particles = []
        self.timer = 0
        
    def contains(self, x, y):
        return math.sqrt((x - self.x)**2 + (y - self.y)**2) < self.radius
    
    def update(self):
        self.timer += 1
        
        # Generate new smoke particles
        if self.timer % 2 == 0:
            for _ in range(2 if self.level == FireLevel.HIGH else 1):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(0, self.radius * 0.8)
                px = self.x + math.cos(angle) * dist
                py = self.y + math.sin(angle) * dist
                self.particles.append(SmokeParticle(px, py, self.level))
        
        # Update existing particles
        for particle in self.particles[:]:
            particle.update()
            if particle.lifetime <= 0:
                self.particles.remove(particle)
    
    def draw(self, screen):
        # Draw fire base
        if self.level != FireLevel.NONE:
            fire_colors = {
                FireLevel.LOW: [(255, 100, 0), (255, 165, 0)],
                FireLevel.MEDIUM: [(255, 50, 0), (255, 165, 0)],
                FireLevel.HIGH: [(255, 0, 0), (255, 100, 0)]
            }
            
            for i in range(10):
                r = self.radius * (0.8 - i * 0.07)
                color = fire_colors[self.level][0] if i < 5 else fire_colors[self.level][1]
                alpha = 200 - i * 15
                s = pygame.Surface((int(r*2), int(r*2)), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, alpha), (int(r), int(r)), int(r))
                screen.blit(s, (int(self.x - r), int(self.y - r)))
        
        # Draw smoke particles
        for particle in self.particles:
            particle.draw(screen)

class Vehicle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = (70, 50, 30)
        self.wheel_color = (40, 40, 40)
    
    def contains(self, x, y):
        return (self.x - self.width/2 <= x <= self.x + self.width/2 and 
                self.y - self.height/2 <= y <= self.y + self.height/2)
    
    def draw(self, screen):
        # Car body
        pygame.draw.rect(screen, self.color, 
                        (self.x - self.width/2, self.y - self.height/2, 
                         self.width, self.height))
        pygame.draw.rect(screen, (100, 100, 100), 
                        (self.x - self.width/2, self.y - self.height/2, 
                         self.width, self.height), 2)
        
        # Windows
        pygame.draw.rect(screen, (150, 200, 255, 100), 
                        (self.x - self.width/3, self.y - self.height/3, 
                         self.width/1.5, self.height/3))
        
        # Wheels
        wheel_positions = [
            (self.x - self.width/2.5, self.y + self.height/2.5),
            (self.x + self.width/2.5, self.y + self.height/2.5),
            (self.x - self.width/2.5, self.y - self.height/2.5),
            (self.x + self.width/2.5, self.y - self.height/2.5)
        ]
        
        for wx, wy in wheel_positions:
            pygame.draw.circle(screen, self.wheel_color, (int(wx), int(wy)), int(self.height/4))

class Exit:
    def __init__(self, x, y, status):
        self.x = x
        self.y = y
        self.status = status
        self.width = 25
        self.height = 80
        self.blink_timer = 0
    
    def draw(self, screen):
        self.blink_timer = (self.blink_timer + 1) % 30
        
        colors = {
            ExitStatus.ACCESSIBLE: (0, 200, 0),
            ExitStatus.RESTRICTED: (200, 200, 0),
            ExitStatus.BLOCKED: (200, 0, 0)
        }
        
        # Only blink if restricted
        if self.status == ExitStatus.RESTRICTED and self.blink_timer < 15:
            color = (100, 100, 0)
        else:
            color = colors[self.status]
        
        # Exit door
        pygame.draw.rect(screen, color, 
                        (self.x - self.width/2, self.y - self.height/2, 
                         self.width, self.height))
        
        # Door frame
        pygame.draw.rect(screen, WHITE, 
                        (self.x - self.width/2, self.y - self.height/2, 
                         self.width, self.height), 3)
        
        # Exit sign
        sign_color = (200, 0, 0) if self.status == ExitStatus.BLOCKED else (0, 0, 200)
        pygame.draw.rect(screen, sign_color, 
                        (self.x - 15, self.y - self.height/2 - 25, 30, 20))
        
        font = pygame.font.SysFont('Arial', 14, bold=True)
        text = font.render("EXIT", True, WHITE)
        screen.blit(text, (self.x - text.get_width()/2, self.y - self.height/2 - 25 + 3))

def draw_tunnel(screen):
    # Tunnel walls with texture
    wall_height = 60
    pygame.draw.rect(screen, (40, 40, 40), (0, 0, WIDTH, wall_height))
    pygame.draw.rect(screen, (40, 40, 40), (0, HEIGHT - wall_height, WIDTH, wall_height))
    
    # Wall texture (bricks)
    brick_width, brick_height = 40, 20
    for y in [0, HEIGHT - wall_height]:
        for x in range(0, WIDTH, brick_width):
            offset = brick_width/2 if (y/brick_height) % 2 == 0 else 0
            for bx in range(0, WIDTH, brick_width):
                pygame.draw.rect(screen, (50, 50, 50), 
                                (bx + offset - brick_width/2, y, brick_width, brick_height), 1)
    
    # Emergency lights with glow effect
    for i in range(100, WIDTH, 200):
        for y in [wall_height/2, HEIGHT - wall_height/2]:
            # Glow effect
            for r in range(15, 5, -5):
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 255, 0, 30), (r, r), r)
                screen.blit(s, (i - r, y - r))
            
            # Light bulb
            pygame.draw.circle(screen, YELLOW, (i, int(y)), 8)
            pygame.draw.circle(screen, WHITE, (i, int(y)), 4)
    
    # Road markings
    for i in range(50, WIDTH, 100):
        pygame.draw.rect(screen, YELLOW, (i, HEIGHT/2 - 1, 50, 2))

def draw_hud(screen, agents):
    font = pygame.font.SysFont('Arial', 24, bold=True)
    small_font = pygame.font.SysFont('Arial', 18)
    
    # Status box
    pygame.draw.rect(screen, (0, 0, 0, 150), (10, 10, 250, 220))
    pygame.draw.rect(screen, WHITE, (10, 10, 250, 220), 2)
    
    # Title
    title = font.render("EVACUATION STATUS", True, WHITE)
    screen.blit(title, (20, 20))
    
    # Agent count
    agents_text = font.render(f"Agents: {len(agents)}", True, WHITE)
    screen.blit(agents_text, (20, 60))
    
    # Legend
    legend = [
        ("Normal", (100, 200, 100)),
        ("Concerned", (200, 200, 100)),
        ("Disoriented", (200, 150, 50)),
        ("Panicked", (200, 50, 50)),
        ("Injured", (100, 100, 200)),
        ("Helpless", (200, 200, 200))
    ]
    
    for i, (text, color) in enumerate(legend):
        pygame.draw.rect(screen, color, (20, 100 + i * 25, 15, 15))
        text_surface = small_font.render(text, True, WHITE)
        screen.blit(text_surface, (40, 100 + i * 25))

def main():
    clock = pygame.time.Clock()
    running = True
    
    # Create agents
    agents = [Agent(random.randint(50, WIDTH//2), 
              random.randint(70, HEIGHT - 70)) for _ in range(60)]
    
    # Create fire zones
    fire_zones = [
        FireZone(WIDTH//3, HEIGHT//2, 100, FireLevel.MEDIUM),
        FireZone(WIDTH//2, HEIGHT//4, 80, FireLevel.LOW),
        FireZone(WIDTH//3, 3*HEIGHT//4, 70, FireLevel.HIGH)
    ]
    
    # Create vehicles (obstacles)
    vehicles = [
        Vehicle(WIDTH//4, HEIGHT//2, 120, 40),
        Vehicle(WIDTH//2 + 50, HEIGHT//3, 100, 35),
        Vehicle(WIDTH//2 - 50, 2*HEIGHT//3, 150, 45)
    ]
    
    # Create exits
    exits = [
        Exit(WIDTH - 50, HEIGHT//3, ExitStatus.ACCESSIBLE),
        Exit(WIDTH - 50, 2*HEIGHT//3, ExitStatus.RESTRICTED),
        Exit(50, HEIGHT//2, ExitStatus.BLOCKED)
    ]
    
    # Main game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Update fire zones
        for zone in fire_zones:
            zone.update()
        
        # Update agents
        for agent in agents[:]:
            agent.move(exits, fire_zones, vehicles)
            
            # Check if agent reached an exit
            for exit in exits:
                if exit.status != ExitStatus.BLOCKED and math.sqrt((agent.x - exit.x)**2 + (agent.y - exit.y)**2) < 25:
                    agents.remove(agent)
                    break
        
        # Randomly change some states (for demonstration)
        if random.random() < 0.01 and agents:
            random_agent = random.choice(agents)
            if random_agent.state.value < AgentState.HELPLESS.value:
                random_agent.state = AgentState(random_agent.state.value + 1)
        
        # Draw everything
        screen.fill((20, 20, 20))  # Dark gray background
        
        # Draw tunnel
        draw_tunnel(screen)
        
        # Draw vehicles
        for vehicle in vehicles:
            vehicle.draw(screen)
        
        # Draw fire zones
        for zone in fire_zones:
            zone.draw(screen)
        
        # Draw exits
        for exit in exits:
            exit.draw(screen)
        
        # Draw agents
        for agent in agents:
            agent.draw(screen)
        
        # Draw HUD
        draw_hud(screen, agents)
        
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    main()