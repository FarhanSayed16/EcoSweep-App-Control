# EcoSweep Diagrams — PlantUML Source

Professional diagrams for the EcoSweep research paper. All use a consistent color palette and clean layout.

---

## Diagram Index (Paper Figure Mapping)

| File | Paper Fig | Description | Type |
|------|-----------|-------------|------|
| `ecosweep-fig1-system-architecture.puml` | **Fig. 1** | System architecture: App ↔ Pi ↔ Arduino | Component |
| `ecosweep-fig2-hardware-block.puml` | **Fig. 2** | Hardware block: Compute, Sensors, Actuators | Block |
| `ecosweep-fig4-state-machine.puml` | **Fig. 4** | Autonomy state machine (SEARCH → PICKUP → RECOVER) | State |
| `ecosweep-pickup-sequence.puml` | **Fig. 5** (optional) | Pickup sequence: creep → arm down → grip → arm up | Sequence |
| `ecosweep-data-flow.puml` | **Fig. 6** | Data flow: Camera → YOLO → Detection → Autonomy → Arduino | Sequence |
| `ecosweep-fig7-manhole-concept.puml` | **Fig. 10** | Extended application: Manhole inspection concept | Component |

---

## Figures That Are NOT UML (You Provide)

| Paper Fig | Description | What to Add |
|-----------|-------------|-------------|
| **Fig. 3** | YOLO detection output | Screenshot from FPV stream with bounding boxes |
| **Fig. 7** | Test environment | Photo of indoor setup, robot, objects |
| **Fig. 8** | Mobile app | Screenshots (FPV, joystick, telemetry) |
| **Fig. 9** | Results chart | Bar/line chart (detection %, pickup %) |

---

## Color Palette (Professional)

| Role | Hex | Use |
|------|-----|-----|
| App / Mobile | `#E3F2FD` | Light blue |
| Pi / AI / Compute | `#E8F5E9` | Light green |
| Arduino / Control | `#FFF3E0` | Light orange |
| Sensors | `#E3F2FD` / `#FCE4EC` | Blue / pink |
| Actuators | `#F3E5F5` / `#FFF8E1` | Purple / amber |
| Text / Arrows | `#37474F` | Dark gray |
| Background | `#FAFAFA` | Off-white |

---

## Generate PNG Images

### Option A: Command Line (requires PlantUML + Java)

```powershell
cd d:\Robot_newcontrol\docs\diagrams
.\generate-png.ps1
```

Or with PlantUML directly:

```bash
plantuml -tpng -o output *.puml
```

PNG files will be in `docs/diagrams/output/`.

### Option B: Online (no install)

1. Go to [PlantUML Online Server](https://www.plantuml.com/plantuml/uml/)
2. Open each `.puml` file
3. Copy full content, paste into the editor
4. Click Submit to render
5. Right-click image → Save as PNG

### Option C: VS Code

1. Install extension: **PlantUML** by jebbs
2. Open a `.puml` file
3. Press `Alt+D` to preview
4. Right-click preview → Export

---

## File Order for Paper (Insert Sequence)

1. **Fig. 1** — `ecosweep-fig1-system-architecture.puml`  
2. **Fig. 2** — `ecosweep-fig2-hardware-block.puml`  
3. **Fig. 3** — (screenshot)  
4. **Fig. 4** — `ecosweep-fig4-state-machine.puml`  
5. **Fig. 5** — `ecosweep-pickup-sequence.puml` OR hardware close-up photo  
6. **Fig. 6** — `ecosweep-data-flow.puml`  
7. **Fig. 7** — (test environment photo)  
8. **Fig. 8** — (app screenshots)  
9. **Fig. 9** — (results chart)  
10. **Fig. 10** — `ecosweep-fig7-manhole-concept.puml`  

---

## Quick Reference

- **All .puml files** → Generate PNG → Paste into Word at the placeholder
- **Figs 3, 7, 8, 9** → Use your own screenshots/photos/charts
- **Output folder** → `docs/diagrams/output/` (after running generate script)
