import pygame
import random
import math
from enum import Enum
import numpy as np

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 1600, 700  
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tunnel Evacuation Simulation - Extended")

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

class LightSource:
    def __init__(self, x, y, radius, intensity, color):
        self.x = x
        self.y = y
        self.radius = radius
        self.base_intensity = intensity
        self.intensity = intensity
        self.base_color = color
        self.flicker_timer = 0
        self.flicker_amount = 0.1
        
    def update(self):
        self.flicker_timer += 1
        if self.flicker_timer % 2 == 0:
            self.intensity = max(0.8, self.base_intensity + random.uniform(-self.flicker_amount, self.flicker_amount))
        
    def draw(self, screen):
        # Create a surface for the light
        light_surface = pygame.Surface((int(self.radius*2), int(self.radius*2)), pygame.SRCALPHA)
        
        # Draw the light with gradient
        for r in range(int(self.radius), 0, -1):
            alpha = int(255 * (r/self.radius) * self.intensity)
            alpha = max(0, min(255, alpha))  # Clamp alpha between 0 and 255
            color = (
                self.base_color[0],
                self.base_color[1],
                self.base_color[2],
                alpha
            )
            pygame.draw.circle(light_surface, color, 
                             (int(self.radius), int(self.radius)), 
                             int(r))
        
        # Blit the light surface
        screen.blit(light_surface, (int(self.x - self.radius), int(self.y - self.radius)))

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
        self.rotation = random.uniform(0, 2 * math.pi)
        self.rotation_speed = random.uniform(-0.1, 0.1)
        
    def update(self):
        self.x += math.cos(self.direction) * self.speed
        self.y -= self.speed * 0.5  # Smoke rises
        self.lifetime -= 1
        self.alpha = int(255 * (self.lifetime / 150))
        self.size = max(0, self.size - 0.05)
        self.rotation += self.rotation_speed
        
    def draw(self, screen):
        if self.size > 0:
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            # Draw smoke with rotation
            points = []
            for i in range(8):
                angle = i * (2 * math.pi / 8) + self.rotation
                radius = self.size * (0.8 + 0.2 * math.sin(self.lifetime * 0.1 + i))
                points.append((
                    self.size + math.cos(angle) * radius,
                    self.size + math.sin(angle) * radius
                ))
            pygame.draw.polygon(s, (*self.color, self.alpha), points)
            screen.blit(s, (int(self.x - self.size), int(self.y - self.size)))

class Agent:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 4
        self.speed = random.uniform(0.4, 0.8)
        self.state = AgentState.NORMAL
        self.target_x = WIDTH - 50
        self.target_y = HEIGHT // 2
        self.color = GREEN
        self.panic_timer = 0
        self.disorientation_angle = 0
        self.animation_frame = 0
        self.footstep_timer = 0
        self.last_positions = []
        self.stuck_timer = 0
        self.exit_approach_timer = 0
        self.preferred_exit = None
        self.update_state_color()
    
    def is_in_exit_range(self, exit):
        # Simple distance check to exit
        return math.sqrt((self.x - exit.x)**2 + (self.y - exit.y)**2) < 30  # Increased range to 30
    
    def find_alternative_path(self, exits, fire_zones, vehicles):
        if self.is_stuck():
            self.stuck_timer += 1
            if self.stuck_timer > 20:  # Reduced from 30 to react faster
                # Try to move perpendicular to current direction
                dx, dy = self.target_x - self.x, self.target_y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    # Rotate 90 degrees
                    dx, dy = -dy/dist, dx/dist
                    # Add more randomness when near exit
                    if self.exit_approach_timer > 0:
                        dx += random.uniform(-0.5, 0.5)
                        dy += random.uniform(-0.5, 0.5)
                    else:
                        dx += random.uniform(-0.3, 0.3)
                        dy += random.uniform(-0.3, 0.3)
                    # Normalize
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        dx, dy = dx/dist, dy/dist
                        return dx, dy
        return None
    
    def find_nearest_exit(self, exits):
        min_dist = float('inf')
        nearest_exit = None
        for exit in exits:
            if exit.status != ExitStatus.BLOCKED:
                # Calculate distance considering tunnel bounds
                dist = math.sqrt((exit.x - self.x)**2 + (exit.y - self.y)**2)
                # Add preference for exits based on agent's position
                if exit.y < 50:  # Top exit
                    if self.y < HEIGHT/3:  # Agent is in upper third
                        dist *= 0.7  # Prefer top exit
                elif exit.y > HEIGHT - 50:  # Bottom exit
                    if self.y > 2*HEIGHT/3:  # Agent is in lower third
                        dist *= 0.7  # Prefer bottom exit
                if dist < min_dist:
                    min_dist = dist
                    nearest_exit = exit
        return nearest_exit
    
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
        nearest_exit = self.find_nearest_exit(exits)
        if nearest_exit:
            self.target_x, self.target_y = nearest_exit.x, nearest_exit.y
            self.preferred_exit = nearest_exit
        
        # Calculate direction to target
        dx, dy = self.target_x - self.x, self.target_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0:
            dx, dy = dx/dist, dy/dist
            
            # Check for alternative path if stuck
            if self.stuck_timer > 20:  # If stuck for too long
                # Try to move perpendicular to current direction
                dx, dy = -dy, dx  # Rotate 90 degrees
                # Add some randomness
                dx += random.uniform(-0.3, 0.3)
                dy += random.uniform(-0.3, 0.3)
                # Normalize
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
            
            # Check for vehicles and other agents (obstacles)
            for vehicle in vehicles:
                if vehicle.contains(self.x + dx * 10, self.y + dy * 10):
                    # Try to move around the vehicle
                    if random.random() < 0.5:
                        dy += 0.3
                    else:
                        dy -= 0.3
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        dx, dy = dx/dist, dy/dist
                    break
            
            # Update position
            new_x = self.x + dx * self.speed * speed_mod
            new_y = self.y + dy * self.speed * speed_mod
            
            # Keep within tunnel bounds with smoother transition
            if new_y < 60:
                new_y = 60 + (60 - new_y) * 0.5  # Bounce back from top wall
            elif new_y > HEIGHT - 60:
                new_y = HEIGHT - 60 - (new_y - (HEIGHT - 60)) * 0.5  # Bounce back from bottom wall
            
            # Update position and track history
            self.x, self.y = new_x, new_y
            self.last_positions.append((self.x, self.y))
            if len(self.last_positions) > 10:
                self.last_positions.pop(0)
            
            # Update stuck timer
            if len(self.last_positions) >= 5 and all(abs(self.x - pos[0]) < 2 and abs(self.y - pos[1]) < 2 for pos in self.last_positions[-5:]):
                self.stuck_timer += 1
            else:
                self.stuck_timer = 0
            
            # Update exit approach timer
            if nearest_exit and dist < 50:
                self.exit_approach_timer += 1
                if self.exit_approach_timer > 30:
                    # Try to find alternative path
                    if random.random() < 0.3:
                        dx, dy = -dy, dx  # Rotate 90 degrees
                        self.exit_approach_timer = 0
            else:
                self.exit_approach_timer = 0
            
            # State transitions
            if not in_fire and self.state != AgentState.NORMAL and random.random() < 0.005:
                if self.state.value > AgentState.NORMAL.value:
                    self.state = AgentState(self.state.value - 1)
            
            self.update_state_color()
            
            # Update footstep timer
            self.footstep_timer = (self.footstep_timer + 1) % 10
    
    def draw(self, screen):
        self.animation_frame = (self.animation_frame + 0.1) % 10
        
        # Draw shadow
        shadow_surface = pygame.Surface((self.radius*2, self.radius), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 50), (0, 0, self.radius*2, self.radius))
        screen.blit(shadow_surface, (int(self.x - self.radius), int(self.y + self.radius)))
        
        # Body
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        
        # Head (slightly smaller circle on top)
        head_radius = self.radius * 0.7
        head_color = (min(255, self.color[0] + 40), min(255, self.color[1] + 40), min(255, self.color[2] + 40))
        pygame.draw.circle(screen, head_color, 
                        (int(self.x), int(self.y - self.radius * 0.7)), 
                        int(head_radius))
        
        # Draw footsteps
        if self.footstep_timer < 5:
            foot_pos = (int(self.x - self.radius * 0.7), int(self.y + self.radius * 0.7))
            pygame.draw.circle(screen, (200, 200, 200, 100), foot_pos, 3)
        
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

    def check_exit_reached(self, exit):
        # Check if agent has reached the exit
        if exit.status == ExitStatus.BLOCKED:
            return False
            
        # Different detection radius for different types of exits
        if exit.y < 50:  # Top exit
            return (abs(self.x - exit.x) < 15 and 
                   abs(self.y - exit.y) < 15)
        elif exit.y > HEIGHT - 50:  # Bottom exit
            return (abs(self.x - exit.x) < 15 and 
                   abs(self.y - exit.y) < 15)
        else:  # Side exits
            return (abs(self.x - exit.x) < 20 and 
                   abs(self.y - exit.y) < 20)

class FireZone:
    def __init__(self, x, y, radius, level):
        self.x = x
        self.y = y
        self.radius = radius
        self.level = level
        self.particles = []
        self.timer = 0
        self.light = LightSource(x, y, radius*2, 1.0, (255, 100, 0))
        
    def contains(self, x, y):
        return math.sqrt((x - self.x)**2 + (y - self.y)**2) < self.radius
    
    def update(self):
        self.timer += 1
        self.light.update()
        
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
        # Draw light effect
        self.light.draw(screen)
        
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
        self.light = LightSource(x, y, width, 0.5, (255, 255, 200))
    
    def contains(self, x, y):
        return (self.x - self.width/2 <= x <= self.x + self.width/2 and 
                self.y - self.height/2 <= y <= self.y + self.height/2)
    
    def draw(self, screen):
        # Draw shadow
        shadow_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 50), (0, 0, self.width, self.height/2))
        screen.blit(shadow_surface, (int(self.x - self.width/2), int(self.y + self.height/2)))
        
        # Draw light effect
        self.light.draw(screen)
        
        # Car body
        pygame.draw.rect(screen, self.color, 
                        (self.x - self.width/2, self.y - self.height/2, 
                         self.width, self.height))
        pygame.draw.rect(screen, (100, 100, 100), 
                        (self.x - self.width/2, self.y - self.height/2, 
                         self.width, self.height), 2)
        
        # Windows
        window_surface = pygame.Surface((int(self.width/1.5), int(self.height/3)), pygame.SRCALPHA)
        pygame.draw.rect(window_surface, (150, 200, 255, 100), (0, 0, window_surface.get_width(), window_surface.get_height()))
        screen.blit(window_surface, (int(self.x - self.width/3), int(self.y - self.height/3)))
        
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
    def __init__(self, x, y, status, width, height):
        self.x = x
        self.y = y
        self.status = status
        self.width = width
        self.height = height
        self.blink_timer = 0
        self.light = LightSource(x, y, 40, 0.8, (0, 200, 0) if status == ExitStatus.ACCESSIBLE else (200, 200, 0))
        # Determine if this is a vertical exit (near top/bottom)
        self.is_vertical = y <= 80 or y >= HEIGHT - 80  # Adjusted for new positions
    
    def draw(self, screen):
        self.blink_timer = (self.blink_timer + 1) % 30
        self.light.update()
        
        # Draw light effect
        self.light.draw(screen)
        
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
        
        # Exit door - swap width and height for vertical exits
        if self.is_vertical:
            # Draw vertical exit
            pygame.draw.rect(screen, color, 
                           (self.x - self.height/2, self.y - self.width/2, 
                            self.height, self.width))
            
            # Door frame
            pygame.draw.rect(screen, WHITE, 
                           (self.x - self.height/2, self.y - self.width/2, 
                            self.height, self.width), 3)
            
            # Exit sign - adjusted position for vertical exits
            sign_color = (200, 0, 0) if self.status == ExitStatus.BLOCKED else (0, 0, 200)
            pygame.draw.rect(screen, sign_color, 
                           (self.x - 25, self.y - 15, 20, 30))
            
            # Draw arrow pointing to exit
            arrow_points = []
            if self.y <= 80:  # Top exit
                arrow_points = [
                    (self.x, self.y - 10),
                    (self.x - 10, self.y + 5),
                    (self.x + 10, self.y + 5)
                ]
            else:  # Bottom exit
                arrow_points = [
                    (self.x, self.y + 10),
                    (self.x - 10, self.y - 5),
                    (self.x + 10, self.y - 5)
                ]
            pygame.draw.polygon(screen, WHITE, arrow_points)
            
            # Rotate text for vertical exits
            font = pygame.font.SysFont('Arial', 14, bold=True)
            text = font.render("EXIT", True, WHITE)
            # Create a rotated surface for the text
            text = pygame.transform.rotate(text, 90)
            screen.blit(text, (self.x - 22, self.y - text.get_height()/2))
        else:
            # Draw horizontal exit (original code)
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
    wall_height = 60  # Increased from 40
    pygame.draw.rect(screen, (40, 40, 40), (0, 0, WIDTH, wall_height))
    pygame.draw.rect(screen, (40, 40, 40), (0, HEIGHT - wall_height, WIDTH, wall_height))
    
    # Wall texture (bricks)
    brick_width, brick_height = 50, 25  # Increased from 30,15
    for y in [0, HEIGHT - wall_height]:
        for x in range(0, WIDTH, brick_width):
            offset = brick_width/2 if (y/brick_height) % 2 == 0 else 0
            for bx in range(0, WIDTH, brick_width):
                pygame.draw.rect(screen, (50, 50, 50), 
                                (bx + offset - brick_width/2, y, brick_width, brick_height), 1)
    
    # Emergency lights with glow effect
    for i in range(200, WIDTH, 300):  # Increased spacing between lights
        for y in [wall_height/2, HEIGHT - wall_height/2]:
            # Glow effect
            for r in range(15, 5, -3):  # Increased light size
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 255, 0, 30), (r, r), r)
                screen.blit(s, (i - r, y - r))
            
            # Light bulb
            pygame.draw.circle(screen, YELLOW, (i, int(y)), 8)
            pygame.draw.circle(screen, WHITE, (i, int(y)), 4)
    
    # Road markings
    for i in range(100, WIDTH, 150):  # Increased spacing between markings
        pygame.draw.rect(screen, YELLOW, (i, HEIGHT/2 - 1, 50, 2))  # Increased length

def draw_hud(screen, agents):
    font = pygame.font.SysFont('Arial', 24, bold=True)
    small_font = pygame.font.SysFont('Arial', 18)
    
    # Status box with gradient background
    hud_surface = pygame.Surface((250, 220), pygame.SRCALPHA)
    pygame.draw.rect(hud_surface, (0, 0, 0, 150), (0, 0, 250, 220))
    pygame.draw.rect(hud_surface, (255, 255, 255, 50), (0, 0, 250, 220), 2)
    screen.blit(hud_surface, (10, 10))
    
    # Title with glow effect
    title = font.render("EVACUATION STATUS", True, WHITE)
    title_shadow = font.render("EVACUATION STATUS", True, (255, 255, 255, 100))
    screen.blit(title_shadow, (12, 12))
    screen.blit(title, (10, 10))
    
    # Agent count with icon
    agents_text = font.render(f"Agents: {len(agents)}", True, WHITE)
    pygame.draw.circle(screen, (100, 200, 100), (30, 70), 8)
    screen.blit(agents_text, (45, 60))
    
    # Legend with improved layout
    legend = [
        ("Normal", (100, 200, 100)),
        ("Concerned", (200, 200, 100)),
        ("Disoriented", (200, 150, 50)),
        ("Panicked", (200, 50, 50)),
        ("Injured", (100, 100, 200)),
        ("Helpless", (200, 200, 200))
    ]
    
    for i, (text, color) in enumerate(legend):
        # Draw state indicator with glow
        indicator_surface = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(indicator_surface, (*color, 200), (10, 10), 8)
        pygame.draw.circle(indicator_surface, (255, 255, 255, 100), (10, 10), 10, 2)
        screen.blit(indicator_surface, (15, 100 + i * 25))
        
        # Draw text with shadow
        text_surface = small_font.render(text, True, WHITE)
        text_shadow = small_font.render(text, True, (0, 0, 0, 100))
        screen.blit(text_shadow, (42, 102 + i * 25))
        screen.blit(text_surface, (40, 100 + i * 25))

def main():
    clock = pygame.time.Clock()
    running = True
    
    # Create more agents for the longer tunnel
    agents = [Agent(random.randint(50, WIDTH-100), 
              random.randint(50, HEIGHT - 50)) for _ in range(150)]
    
    # Create fire zones with adjusted sizes
    fire_zones = [
        FireZone(WIDTH//6, HEIGHT//2, 80, FireLevel.MEDIUM),
        FireZone(WIDTH//3, HEIGHT//3, 70, FireLevel.LOW),
        FireZone(WIDTH//2, 2*HEIGHT//3, 75, FireLevel.HIGH),
        FireZone(2*WIDTH//3, HEIGHT//4, 72, FireLevel.MEDIUM),
        FireZone(5*WIDTH//6, HEIGHT//2, 78, FireLevel.HIGH),
        FireZone(WIDTH//4, 3*HEIGHT//4, 65, FireLevel.LOW),
        FireZone(3*WIDTH//4, HEIGHT//3, 73, FireLevel.MEDIUM)
    ]
    
    # Create vehicles with smaller sizes
    vehicles = [
        # Large trucks (reduced sizes by ~50%)
        Vehicle(WIDTH//8, HEIGHT//2, 100, 30),
        Vehicle(WIDTH//3, HEIGHT//3, 90, 28),
        Vehicle(WIDTH//2, 2*HEIGHT//3, 110, 33),
        Vehicle(2*WIDTH//3, HEIGHT//2, 95, 30),
        Vehicle(7*WIDTH//8, HEIGHT//3, 105, 32),
        
        # Regular cars (reduced sizes by ~50%)
        Vehicle(WIDTH//6, HEIGHT//2 - 60, 60, 20),
        Vehicle(WIDTH//4, HEIGHT//2 + 60, 50, 18),
        Vehicle(5*WIDTH//12, 2*HEIGHT//3, 55, 19),
        Vehicle(7*WIDTH//12, HEIGHT//3, 58, 18),
        Vehicle(3*WIDTH//4, HEIGHT//2 - 48, 53, 18),
        Vehicle(5*WIDTH//6, HEIGHT//2 + 54, 55, 18),
        Vehicle(11*WIDTH//12, 2*HEIGHT//3, 57, 19),
        
        # Crashed/diagonal vehicles (reduced sizes by ~50%)
        Vehicle(3*WIDTH//8, 2*HEIGHT//3, 75, 23),
        Vehicle(5*WIDTH//8, HEIGHT//2, 65, 21),
        Vehicle(7*WIDTH//8, HEIGHT//3, 70, 22),
        Vehicle(WIDTH//4, HEIGHT//2, 73, 22),
        
        # Emergency vehicles (reduced sizes by ~50%)
        Vehicle(WIDTH//6, HEIGHT//2 + 30, 80, 25),
        Vehicle(WIDTH//2, HEIGHT//2 - 30, 85, 26),
        Vehicle(5*WIDTH//6, HEIGHT//2, 83, 26)
    ]
    
    # Create exits with fewer emergency exits
    exits = [
        # Main exits at both ends
        Exit(WIDTH - 30, HEIGHT//3, ExitStatus.ACCESSIBLE, 15, 48),
        Exit(WIDTH - 30, 2*HEIGHT//3, ExitStatus.ACCESSIBLE, 15, 48),
        Exit(30, HEIGHT//3, ExitStatus.RESTRICTED, 15, 48),
        Exit(30, 2*HEIGHT//3, ExitStatus.RESTRICTED, 15, 48),
        
        # Reduced number of emergency exits - moved closer to walkable area
        Exit(WIDTH//3, 80, ExitStatus.ACCESSIBLE, 15, 48),  # Moved down from top
        Exit(WIDTH//3, HEIGHT-80, ExitStatus.ACCESSIBLE, 15, 48),  # Moved up from bottom
        Exit(2*WIDTH//3, 80, ExitStatus.ACCESSIBLE, 15, 48),  # Moved down from top
        Exit(2*WIDTH//3, HEIGHT-80, ExitStatus.ACCESSIBLE, 15, 48)  # Moved up from bottom
    ]

    # Create camera offset for scrolling
    camera_x = 0
    scroll_speed = 12
    
    # Main game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    camera_x = min(0, camera_x + scroll_speed * 10)
                elif event.key == pygame.K_RIGHT:
                    camera_x = max(-(WIDTH - screen.get_width()), camera_x - scroll_speed * 10)
        
        # Update fire zones
        for zone in fire_zones:
            zone.update()
        
        # Update agents
        for agent in agents[:]:
            agent.move(exits, fire_zones, vehicles)
            
            # Check if agent is in range of any exit
            for exit in exits:
                if exit.status != ExitStatus.BLOCKED and agent.is_in_exit_range(exit):
                    agents.remove(agent)
                    break
        
        # Draw everything
        screen.fill((20, 20, 20))  # Dark gray background
        
        # Create a surface for the entire tunnel
        tunnel_surface = pygame.Surface((WIDTH, HEIGHT))
        tunnel_surface.fill((20, 20, 20))
        
        # Draw tunnel elements on the tunnel surface
        draw_tunnel(tunnel_surface)
        
        # Draw vehicles
        for vehicle in vehicles:
            vehicle.draw(tunnel_surface)
        
        # Draw fire zones
        for zone in fire_zones:
            zone.draw(tunnel_surface)
        
        # Draw exits
        for exit in exits:
            exit.draw(tunnel_surface)
        
        # Draw agents
        for agent in agents:
            agent.draw(tunnel_surface)
        
        # Draw the visible portion of the tunnel
        screen.blit(tunnel_surface, (camera_x, 0))
        
        # Draw HUD (always on top, not affected by scrolling)
        draw_hud(screen, agents)
        
        # Draw scroll indicators
        if camera_x < 0:
            pygame.draw.polygon(screen, (255, 255, 255, 128), 
                              [(10, HEIGHT//2), (30, HEIGHT//2-20), (30, HEIGHT//2+20)])
        if camera_x > -(WIDTH - screen.get_width()):
            pygame.draw.polygon(screen, (255, 255, 255, 128), 
                              [(screen.get_width()-10, HEIGHT//2), 
                               (screen.get_width()-30, HEIGHT//2-20), 
                               (screen.get_width()-30, HEIGHT//2+20)])
        
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    main()