# Conventions for PicoSDK constant definitions

## Module layout
- Import statements at the top, separated from the first definition by a single blank line.
- All constants and public structures live in `pypicosdk/constants.py`.
- The bottom of the file maintains a comprehensive `__all__` list enumerating every exported name.

## Enumerations and constant groups
- When constants map directly to integer values, use an `IntEnum` subclass.
  For example: `class CHANNEL(IntEnum):`.
- For simpler sets of constants that don’t require an enum type, use a plain class with uppercase attributes.
- Constant names are **UPPERCASE_WITH_UNDERSCORES**.
- Every enumeration or constant group includes a docstring with:
  - A Summary line explaining the function and summarising the info from the API documentation.
  - An `Attributes:` section listing each constant and stating if it is required or optional. If optional, the default value must be listed for reference.
  - Optionally an `Examples:` section demonstrating usage.
- One blank line separates each class definition.

## ctypes structures
- `ctypes.Structure` classes replicate PicoSDK structs.
- Set `_pack_ = 1` to mirror the 1-byte packing used in the SDK headers.
- Declare `_fields_` as a list of `(field_name, ctype)` tuples.
- Field names have a trailing underscore (`triggerTime_`) to match the C struct names exactly.
- Provide a docstring explaining the purpose of the structure and any special naming conventions.

## Miscellaneous
- Lists or helper constants (e.g., `CHANNEL_NAMES`) are defined at module scope with uppercase names.
- Indentation uses four spaces and no tabs.
- Keep line lengths reasonably short for readability (many existing lines are under 100 characters).

## Python wrapper style
- All public functions and methods include a triple-quoted docstring. Start with a
  short summary line followed by `Args:` and `Returns:` sections. Use `Raises:`
  when applicable.
- Type hints annotate function arguments and return values to clarify expected
  types.
- Private helper functions are prefixed with an underscore.
- Classes have an extensive docstring summarizing and explaining use including args, values, related consts and their purpose etc.
- Each module ends with an explicit `__all__` list enumerating all exported
  names. The package ``__init__`` re-exports these names for static analysers.

## Golden docstring style (for functions)

The following principles are illustrated by the `set_channel` docstring, which serves as the golden example:

### Signature included
The function signature is written at the top in Python style, showing parameter names, types, and defaults. This makes it instantly clear how the function is called.

### One-line summary
The docstring begins with a short description (e.g., *Configure a scope channel in one call.*).  
This is plain and action-oriented, describing what the function does in minimal words.

### Parameter breakdown
Each parameter is listed with:
- **name** (matches the function signature)  
- **type** (e.g., `CHANNEL`, `bool`, `float`, `str`)  
- **purpose** (brief explanation in everyday language)  
- **default values** are shown inline, not repeated unnecessarily.

Example:
- `enabled`: turn channel on/off  
- `offset`: analog offset in volts  

### Defaults in signature, not prose
Defaults are shown directly in the signature (`enabled: bool = True`, `offset: float = 0.0`)  
to avoid redundancy in the explanations.

### Extra context at the end
Special notes (like ps6000a combining `set_channel_on/off`) are included in a short paragraph at the end.  
These provide background without cluttering the parameter list.

### Concise formatting
- Bullet points for parameters → easy to scan.  
- Avoids full sentences unless needed.  
- Reads like code documentation, not a manual.  

---

## Docstring Template Skeleton

```python
function_name(
    param1: TYPE = default,
    param2: TYPE = default,
    ...
)
"""
One-line summary of what the function does.

- param1: short description of parameter purpose
- param2: short description of parameter purpose
- ...

Additional context, notes, or special behavior (if any).
"""
```
