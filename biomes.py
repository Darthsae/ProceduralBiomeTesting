from opensimplex import OpenSimplex
from SockLib.Input import intput
from pygame import Color, Vector2, Rect
from pygame.time import Clock
from pygame_gui import UIManager
from pygame_gui.elements import UIButton, UILabel
from enum import Enum
import pygame, sys, math, pygame_gui

#region Constants
WIDTH: int = 640
HEIGHT: int = 480
CLEAR_COLOR: Color = (63, 63, 178)
TILE_SIZE: int = 8

TEMP = False
RAIN = False
HUMID = False
#endregion

#region Helpers
def defaultSafeArgument(index: int, defaultValue: str) -> str:
    return defaultValue if len(sys.argv) <= index else sys.argv[index]
#endregion

class BiomeModifier:
    def __init__(self, name: str, minHeight: float, maxHeight: float, minTemperature: float, maxTemperature: float, minHumidity: float, maxHumidity: float, minRainfall: float, maxRainfall: float, tags: list[tuple[str, float]]):
        self.name: str = name
        self.minHeight: float = minHeight
        self.maxHeight: float = maxHeight
        self.minTemperature: float = minTemperature
        self.maxTemperature: float = maxTemperature
        self.minHumidity: float = minHumidity
        self.maxHumidity: float = maxHumidity
        self.minRainfall: float = minRainfall
        self.maxRainfall: float = maxRainfall
        self.tags: list[tuple[str, float]] = tags

    def isValid(self, height: float, temperature: float, humidity: float, rainfall: float):
        return self.minHeight <= height <= self.maxHeight and self.minTemperature <= temperature <= self.maxTemperature and self.minHumidity <= humidity <= self.maxHumidity and self.minRainfall <= rainfall <= self.maxRainfall

class Tile:
    def __init__(self, name: str, symbol: str, color: Color, tags: list[str] = []):
        self.name: str = name
        self.symbol: str = symbol
        self.color: Color = color
        self.tags: list[str] = tags
        
    def isValid(self, tags: list[str]):
        if len(tags) != len(self.tags):
            return False
        
        for i in range(len(tags)):
            if tags[i] not in self.tags:
                return False
            
        return True
    
class Feature:
    def __init__(self):
        pass

class Chunk:
    CHUNK_SIZE: int = 64
    NOISE_SCALE: float = 0.01
    
    def __init__(self, x: int, y: int, tiles: list[list[Tile]]):
        self.x: int = x
        self.y: int = y
        self.tiles: list[list[Tile]] = tiles
    
    def display(self):
        for i in range(len(self.tiles)):
            for j in range(len(self.tiles[i])):
                print(self.tiles[i][j].symbol, end="")
            print("")
    
class World:
    def __init__(self, seed: int):
        self.heightMap: OpenSimplex = OpenSimplex(seed)
        self.temperatureMap: OpenSimplex = OpenSimplex(seed * 2)
        self.humidityMap: OpenSimplex = OpenSimplex(seed * 3)
        self.rainfallMap: OpenSimplex = OpenSimplex(seed * 4)
        
        self.biomeModifiers: list[BiomeModifier] = []
        self.narrowExclusiveCachedTileSearchCache: dict[str, Tile] = {}
        self.tiles: list[Tile] = []
        self.chunks: dict[tuple[int, int], Chunk] = {}
    
    def addBiomeModifier(self, modifier: BiomeModifier) -> None:
        self.biomeModifiers.append(modifier)
    
    def narrowExclusiveCachedTileSearch(self, tags: list[str], biomeModifiers: list[str]) -> Tile:
        tags.sort()
        biomeModifiers.sort()
        key: str = "".join(tags) + "".join(biomeModifiers)
        if self.narrowExclusiveCachedTileSearchCache.get(key) == None:
            for i in range(len(self.tiles)):
                if self.tiles[i].isValid(tags):
                    self.narrowExclusiveCachedTileSearchCache[key] = self.tiles[i]
                    break
                    
        return self.narrowExclusiveCachedTileSearchCache[key]
    
    def generate(self, x: int, y: int) -> Tile:
        height: float = self.heightMap.noise2(x * Chunk.NOISE_SCALE, y * Chunk.NOISE_SCALE)
        temperature: float = self.temperatureMap.noise2(x * Chunk.NOISE_SCALE, y * Chunk.NOISE_SCALE)
        humidity: float = self.humidityMap.noise2(x * Chunk.NOISE_SCALE, y * Chunk.NOISE_SCALE)
        rainfall: float = self.rainfallMap.noise2(x * Chunk.NOISE_SCALE, y * Chunk.NOISE_SCALE)
        
        valid: list[BiomeModifier] = []
        names: list[str] = []
        for i in range(len(self.biomeModifiers)):
            if self.biomeModifiers[i].isValid(height, temperature, humidity, rainfall):
                valid.append(self.biomeModifiers[i])
                names. append(self.biomeModifiers[i].name)
        tags: dict[str, float] = {}
        
        for i in range(len(valid)):
            for j in range(len(valid[i].tags)):
                if tags.get(valid[i].tags[j][0]) == None:
                    tags[valid[i].tags[j][0]] = valid[i].tags[j][1]
                else:
                    tags[valid[i].tags[j][0]] += valid[i].tags[j][1]
        
        finalTags: list[str] = []
        
        tagKeys: list[str] = list(tags.keys())
        
        for i in range(len(tagKeys)):
            if tags[tagKeys[i]] > 0:
                finalTags.append(tagKeys[i])
        
        return self.narrowExclusiveCachedTileSearch(finalTags, names)
    
    def newChunk(self, x: int, y: int) -> None:
        if self.chunks.get((x, y)) != None:
            return
        
        print(f"Loading New Chunk ({x}, {y})")
        
        tiles: list[list[Tile]] = []
        
        for i in range(x * Chunk.CHUNK_SIZE, x * Chunk.CHUNK_SIZE + Chunk.CHUNK_SIZE):
            tileRow: list[Tile] = []
            for j in range(y * Chunk.CHUNK_SIZE, y * Chunk.CHUNK_SIZE + Chunk.CHUNK_SIZE):
                tileRow.append(self.generate(i, j))
            tiles.append(tileRow)
                
        
        self.chunks[(x, y)] = Chunk(x, y, tiles)
          
#region UI Shenanigans
class ScreenType(Enum):
    TEST = 0

def switchScreen(newScreen: ScreenType):
    global currentScreen, backButton, manager, positionLabel
    currentScreen = newScreen
    manager.clear_and_reset()
    match newScreen:
        case ScreenType.TEST:
            global humidityButton, rainfallButton, temperatureButton
            backButton = UIButton(Rect(0, 0, 64, 32), "Back", manager)
            humidityButton = UIButton(Rect(0, 32, 96, 32), "Humidity", manager)
            rainfallButton = UIButton(Rect(0, 64, 96, 32), "Rainfall", manager)
            temperatureButton = UIButton(Rect(0, 96, 96, 32), "Temperature", manager)
            positionLabel = UILabel(Rect(WIDTH - 128, 0, 128, 32), f"{pos.x}, {pos.y}", manager)
#endregion      

world: World = World(intput("Seed: "))
world.addBiomeModifier(BiomeModifier("Base", -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, [("Base", 1.0)]))
world.addBiomeModifier(BiomeModifier("Simple", 0.0, 1.0, 0.5, 1.0, 0.2, 0.5, 0.05, 0.1, [("Simple", 5.0)]))
world.addBiomeModifier(BiomeModifier("Shrimple", -0.5, 1.0, 0.5, 1.0, 0.2, 0.5, -0.25, 0.1, [("Simple", 1.5)]))
world.addBiomeModifier(BiomeModifier("Anti Base", 0.2, 0.5, 0.5, 0.8, 0.3, 0.4, 0.05, 0.1, [("Base", -1.0)]))
world.tiles = [
    Tile("Simple Tile", "S", Color(25, 25, 25), ["Simple"]),
    Tile("Base Tile", "B", Color(0, 150, 25), ["Base"]),
    Tile("Simple Base Tile", "$", Color(50, 100, 50), ["Simple", "Base"]),
]


pygame.init()

if defaultSafeArgument(1, 0):
    while True:
        x: int = intput("Chunk X: ")
        y: int = intput("Chunk Y: ")
            
        world.newChunk(x, y)

        world.chunks[(x, y)].display()
        
        if input("Quit: ") == "yes":
            break
else:
    screen: pygame.Surface = pygame.display.set_mode((WIDTH, HEIGHT))
    ala = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.display.set_caption("Biome Test One")
    
    manager: UIManager = UIManager((WIDTH, HEIGHT))
    
    clock: Clock = Clock()
    
    running: bool = True
    pos: Vector2 = Vector2(0, 0)
    
    currentScreen: ScreenType = ScreenType.TEST
    switchScreen(ScreenType.TEST)
    
    while running:
        time_delta: float = clock.tick(60)/1000.0
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    running = False
                case pygame.KEYDOWN:
                    match event.key:
                        case pygame.K_LEFT:
                            pos.x -= TILE_SIZE
                        case pygame.K_RIGHT:
                            pos.x += TILE_SIZE
                        case pygame.K_DOWN:
                            pos.y += TILE_SIZE
                        case pygame.K_UP:
                            pos.y -= TILE_SIZE
                case pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == backButton:
                        print("back")
                    elif event.ui_element == humidityButton:
                        HUMID = not HUMID
                    elif event.ui_element == rainfallButton:
                        RAIN = not RAIN
                    elif event.ui_element == temperatureButton:
                        TEMP = not TEMP
            
            manager.process_events(event)
        
        match currentScreen:
            case ScreenType.TEST:
                positionLabel.set_text(f"{pos.x}, {pos.y}")
        
        manager.update(time_delta)
        
        #region Drawing
        screen.fill(CLEAR_COLOR)
        bottom: Vector2 = pos + (WIDTH, HEIGHT)
        chunks: Rect = Rect((int)(math.floor(pos.x / (Chunk.CHUNK_SIZE * TILE_SIZE))), (int)(math.floor(pos.y / (Chunk.CHUNK_SIZE * TILE_SIZE))), (int)(math.ceil(bottom.x / (Chunk.CHUNK_SIZE * TILE_SIZE))), (int)(math.ceil(bottom.y / (Chunk.CHUNK_SIZE * TILE_SIZE))))
        for i in range(chunks.x, chunks.width):
            for j in range(chunks.y, chunks.height):
                world.newChunk(i, j)
                chunk: Chunk = world.chunks[i, j]
                for y in range(Chunk.CHUNK_SIZE):
                    for x in range(Chunk.CHUNK_SIZE):
                        X = (x + Chunk.CHUNK_SIZE * i)
                        Y = (y + Chunk.CHUNK_SIZE * j)
                        DX = X * TILE_SIZE - pos.x
                        DY = Y * TILE_SIZE - pos.y
                        pygame.draw.rect(screen, chunk.tiles[y][x].color, (DX, DY, TILE_SIZE, TILE_SIZE))
                        
                        #DEBUG
                        if HUMID or RAIN or TEMP:
                            r = (world.temperatureMap.noise2(X * Chunk.NOISE_SCALE, Y * Chunk.NOISE_SCALE) + 1) * 128 if TEMP else 0
                            g = (world.rainfallMap.noise2(X * Chunk.NOISE_SCALE, Y * Chunk.NOISE_SCALE) + 1) * 128 if RAIN else 0
                            b = (world.humidityMap.noise2(X * Chunk.NOISE_SCALE, Y * Chunk.NOISE_SCALE) + 1) * 128 if HUMID else 0
                            pygame.draw.rect(ala, (r, g, b, 255), (DX, DY, TILE_SIZE, TILE_SIZE))
        
        if HUMID or RAIN or TEMP:
            screen.blit(ala)
        
        manager.draw_ui(screen)
        
        pygame.display.flip()
        #endregion
    
pygame.quit()
