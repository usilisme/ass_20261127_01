# Auto Driving Car Simulation

A command-line simulation of one or more autonomous cars moving on a rectangular field.
Each car gets a command string (`L` = turn left, `R` = turn right, `F` = move forward one cell).
All cars run **step by step** together: at each step every car runs one command, in the order the
cars were added. Cars that collide stop moving.

## Requirements

* Python **3.10+**
* No runtime dependencies (standard library only). The dev tools are `pytest`, `ruff` and `mypy`.

## Quick start

```bash
# 1. Create a virtual environment and install the package plus dev tools
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 2. Run the simulation (either command works)
auto-driving
python -m auto_driving

# 3. Run the tests (with coverage)
pytest
```

With `make`: `make install`, `make run`, `make test`, and `make check` (lint, type check and tests, as in CI).

### Color Options

| Option | Effect |
|---|---|
| `--color {auto,always,never}` | Colour each car in the field drawing. `auto` (default) uses colour only when writing to a terminal, and follows the [`NO_COLOR`](https://no-color.org) convention and `TERM=dumb`. |
| `--no-grid` | Don't draw the field. The output then matches the specification exactly. |

You can also run it without installing, straight from the source tree:

```bash
PYTHONPATH=src python3 -m auto_driving
```

## Example session

```text
Welcome to Auto Driving Car Simulation!

Please enter the width and height of the simulation field in x y format:
10 10
You have created a field of 10 x 10.

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
1
Please enter the name of the car:
A
Please enter initial position of car A in x y Direction format:
1 2 N
Please enter the commands for car A:
FFRFFFFRRL
Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
2
Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

After simulation, the result is:
- A, (5,4) S

Please choose from the following options:
[1] Start over
[2] Exit
2
Thank you for running the simulation. Goodbye!
```

## Field visualization

After the results, the program draws the field, giving each car its own colour:

```text
After simulation, the result is:
- A, collides with B at (5,4) at step 7
- B, collides with A at (5,4) at step 7
- C, (4,7) W

  ┌──────────────────────────────┐
9 │ +  ·  ·  ·  ·                │
8 │             ·  ·  ·  +       │
7 │             ●  ·             │
6 │                ·             │
5 │                ·             │
4 │    ·  ·  ·  ·  X             │
3 │    ·                         │
2 │    +                         │
1 │                              │
0 │                              │
  └──────────────────────────────┘
    0  1  2  3  4  5  6  7  8  9

Legend: + start   · path   ● final position   X crash
Cars:   ● A   ● B   ● C
```

| Symbol | Meaning |
|---|---|
| `+` | Where the car started |
| `·` | A cell the car drove through |
| `●` | Where the car ended |
| `X` | A crash, drawn white on red. Red is kept for crashes, so no car is red. |

Drawing rules:
* When marks share a cell, the more important one is drawn: **crash > final > start > path**. If two cars have the same kind of mark in a cell, the car added later is drawn.
* Fields up to **40 x 40** are drawn in full. On larger fields the drawing is cropped to the area the cars used (plus a one-cell margin) and a note says which part is shown. If even that area is larger than 40 x 40, a message is shown instead of the drawing.
* If the terminal's encoding can't show `●`, `·` or the box characters (for example `cp1252` on older Windows consoles), ASCII is used instead: `O` final, `.` path, and `+ - |` for the border.

## Project layout

```text
src/auto_driving/
├── domain.py       # Immutable value objects: Direction, Command, Position, Field, Car
├── simulator.py    # Simulator: the step-by-step engine (no I/O); CarResult, Collision
├── parsing.py      # Turns user text into domain objects, or raises ValidationError
├── formatting.py   # How cars and results are printed
├── visualization.py # Draws the field: starts, paths, final positions and crashes, in colour
├── cli.py          # AutoDrivingCLI: the interactive prompt flow; main() entry point
└── __main__.py     # Allows `python -m auto_driving`
tests/
├── test_domain.py      # Rotation, movement, field bounds
├── test_simulator.py   # Spec scenarios, boundaries, command lengths, collisions, purity
├── test_parsing.py     # Valid and invalid input for every prompt
├── test_visualization.py  # Which mark each cell shows, cropping, colours, ASCII fallback
└── test_cli.py         # Full transcripts, re-prompting, start over, EOF, `python -m` entry point
```

### Design

The code is split into layers, and each layer only depends on the ones below it:

```text
cli  ──►  parsing, formatting, visualization  ──►  simulator  ──►  domain
```

* **`domain`** has no logic beyond geometry. Its objects are frozen, so a car's *initial* configuration can never change.
* **`simulator`** is a pure function of `(field, cars) → results`. It keeps the state that changes during a run in its own internal objects, so the same cars can be run any number of times. Because it has no I/O, it can be reused by another front end (a REST API, a GUI, a batch runner).
* **`parsing`** holds all the input checks. Each check raises `ValidationError` with a message the user can read.
* **`visualization`** works out which mark each cell shows (`build_marks`) separately from drawing it (`render_field`), so the rules can be tested without comparing drawings. The simulator records each car's `path` for it.
* **`cli`** only handles the conversation. `input_fn`/`output_fn` are passed in, so the tests drive whole sessions and compare the exact transcript with the spec.

### Quality checks

| Check | Tool | Command |
|---|---|---|
| Unit and end-to-end tests | pytest (+ branch coverage, fails below 95%) | `pytest` |
| Lint and import order | ruff | `ruff check .` |
| Formatting | ruff format | `ruff format --check .` |
| Static types | mypy `--strict` | `mypy` |

GitHub Actions (`.github/workflows/ci.yml`) runs all of these on Python 3.10, 3.12 and 3.14.

## Assumptions

1. **Coordinates**: a `W x H` field has valid cells `x ∈ [0, W-1]` and `y ∈ [0, H-1]` (as in the spec's 10 x 10 → (9,9) example). North is `+y` and East is `+x`.
2. **Field size** must be two positive whole numbers. There is no upper limit.
3. **Order within a step**: cars run in the **order they were added**. A collision is checked straight after each car's move, so a car only collides when it drives into a taken cell. This means:
   * Two cars facing each other in neighbouring cells collide in the cell of the car that moves second, because the first car drives into it.
   * A car can move into a cell that a car earlier in the order left during the same step.
4. **Ignored moves still use a step**: when a car tries to leave the field, its `F` is ignored and it waits for its next command at the next step.
5. **Cars with no commands left** (or with no commands at all) stay where they are, and other cars can still hit them. A car that is hit counts as collided, even if it was not moving.
6. **Collided cars** stop where they collided and run no more commands. Their wreck stays on the field, and later cars that drive into it also collide.
7. **Pile-ups**: when a car drives into a cell holding several cars, it reports all of them (`collides with A, B at ...`). Cars that had already crashed keep their **first** collision.
8. **Result output**: cars are listed in the order they were added. Collided cars show their collision and the others show their final position and direction, so one result can mix both.
9. **Car names** are case-sensitive, must be unique and non-empty, and cannot contain a comma (it would make the `- name, ...` output ambiguous).
10. **Starting positions** must be inside the field and different from every other car's starting position.
11. **Directions and commands** are case-insensitive (`n` = `N`, `ffr` = `FFR`). Spaces inside a command string are rejected. An **empty** command string is allowed: the car just stays where it is.
12. **Running with no cars** is refused with a message, and the menu is shown again.
13. **Invalid input** shows an `Invalid input: ...` message and asks the same question again.
14. **The field drawing** is extra output that the spec doesn't ask for. It comes after the spec's result lines and before the menu, so the spec's own lines are unchanged. `--no-grid` turns it off for an exact match.
15. **End of input (Ctrl-D) or Ctrl-C** while waiting for input is treated as *Exit*: the goodbye message is printed and the program exits with code 0.

## Gaps in the specification

* There is no expected behaviour for invalid / blank / duplicate car names, handled as per above.
* There is no expected behaviour for cars starting in the same cell, or cars starting outside the field, handled as per above.
* The collisions check was not 100% clear, it is assumed to be after **each car's move**.
* The output format for collisions with more than one car (pile-ups) is not defined, it is assumed that the crashed cars left a wreck and can be collided with any active moving car(s).
* The UI options can be better of course e.g. "Start over" goes back to field setup, there can instead options to reset only the paths and keep the cars setup.

## Possible improvements

* **Performance**: collision checks scan all cars, so each step costs O(cars²). For very large fleets, keep a `dict[Position, list[car]]` of occupied cells so each check is O(1).
* **Configurable rules**: let the user choose the collision mode (sequential or simultaneous) and whether wrecks block cells, as a strategy passed to `Simulator`.
* **Batch / non-interactive mode**: read a scenario file (JSON/YAML) or command-line arguments, e.g. `auto-driving run scenario.json`, so scenarios can be scripted and replayed.
* **Better UX**: an option to remove or edit a car before running, and step-by-step playback of the drawing (redrawing the field after each step).
* **Visualization**: with more than 10 cars the colours repeat, and with colour off all cars look alike. Car initials, or a symbol per car, would help. A drawing for very large fields (for example, scaled down) or an image export (PNG/SVG) would also help.
* **Observability**: structured logging of each step behind a `--verbose` flag.
* **Property-based tests** (Hypothesis): for example, "no car ever ends up outside the field" and "simulation is repeatable" for random inputs.
* **Distribution**: publish a wheel or container image, and add pre-commit hooks that run ruff and mypy locally.
